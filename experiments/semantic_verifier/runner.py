"""Standalone development experiment; dry by default, no dataset auto-discovery."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import uuid
from transport import RecordedTransport, validate_base_url

HERE = Path(__file__).resolve().parent
MODEL = 'exaone3.5:7.8b-instruct-q8_0'
OPTIONS = dict(num_ctx=32768, temperature=0, seed=42, num_predict=1024)
ORDER = [('V02','A'),('V02','B'),('V01','B'),('V01','A'),('V03','A'),('V03','B')]
LABELS = {'supported','contradicted','unsupported','meaning_weakened','needs_review'}


def pairs(items):
    result = {}
    for k,v in items:
        if k in result: raise ValueError('Duplicate JSON key')
        result[k] = v
    return result


def read(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs)


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def save(path,obj):
    with path.open('x',encoding='utf-8') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)


def load_inputs(path):
    bundle = read(path)
    if set(bundle) != {'version','kind','inputs'} or bundle['version'] != 1 or bundle['kind'] not in ('synthetic','reviewed_external'):
        raise ValueError('Invalid bundle header')
    items = bundle['inputs']
    if not isinstance(items,list) or len(items)!=3:
        raise ValueError('Exactly three inputs required')
    seen = set()
    for item in items:
        if not isinstance(item,dict) or set(item)!={'input_id','question','target_claim','response_context','sources'}:
            raise ValueError('Unexpected input field; never include answer key')
        rid=item['input_id']
        if not isinstance(rid,str) or rid not in {'V01','V02','V03'} or rid in seen:
            raise ValueError('Input IDs must be unique V01..V03')
        seen.add(rid)
        if any(not isinstance(item[k],str) or not item[k].strip() for k in ('question','target_claim')):
            raise ValueError('Empty question/claim')
        if item['response_context'] is not None and not isinstance(item['response_context'],str):
            raise ValueError('Invalid response context')
        if not isinstance(item['sources'],list) or not item['sources']:
            raise ValueError('Sources required')
        refs=set()
        for s in item['sources']:
            if not isinstance(s,dict) or set(s)!={'source_ref','text'} or any(not isinstance(v,str) or not v.strip() for v in s.values()):
                raise ValueError('Invalid source')
            if s['source_ref'] in refs: raise ValueError('Duplicate source ID')
            refs.add(s['source_ref'])
    return bundle


def plan(bundle):
    candidate=read(HERE/'candidate.json')
    a=candidate['system_prompt']
    prompts={'A':a,'B':a+'\n\n'+(HERE/'meaning_addendum.txt').read_text(encoding='utf-8').strip()}
    warm=dict(input_id='W00',question='상자 색은?',target_claim='상자는 파란색이다.',response_context=None,
              sources=[dict(source_ref='S1',text='상자는 파란색이다.')])
    items={x['input_id']:x for x in bundle['inputs']}
    items['W00']=warm
    rows=[]
    for rid,arm in [('W00','A')]+ORDER:
        item=items[rid]
        blind={k:item[k] for k in ('question','target_claim','response_context','sources')}
        payload=dict(model=MODEL,stream=False,options=OPTIONS.copy(),format=candidate['output_schema'],messages=[
            dict(role='system',content=prompts[arm]),dict(role='user',content=json.dumps(blind,ensure_ascii=False))])
        rows.append(dict(run_id=rid+'-'+arm,input_id=rid,arm=arm,item=item,request=payload))
    return rows


class InvalidResult(ValueError):
    def __init__(self,category): super().__init__(category); self.category=category


def validate(raw,item,reason):
    if reason!='stop': raise InvalidResult('truncated_or_incomplete')
    try: obj=json.loads(raw,object_pairs_hook=pairs)
    except (ValueError,TypeError): raise InvalidResult('format_error')
    if not isinstance(obj,dict) or set(obj)!={'verdict','evidence','explanation'}:
        raise InvalidResult('format_error')
    if not isinstance(obj['verdict'],str) or obj['verdict'] not in LABELS or not isinstance(obj['explanation'],str) or not obj['explanation'].strip() or not isinstance(obj['evidence'],list):
        raise InvalidResult('format_error')
    sources={s['source_ref']:s['text'] for s in item['sources']}
    for q in obj['evidence']:
        if not isinstance(q,dict) or set(q)!={'source_ref','quote'} or any(not isinstance(v,str) for v in q.values()):
            raise InvalidResult('format_error')
        if q['source_ref'] not in sources or not q['quote'].strip() or q['quote'] not in sources[q['source_ref']]:
            raise InvalidResult('citation_error')
    return obj


def collect(bundle,transport,folder,remaining):
    rows=plan(bundle)
    states={r['run_id']:'not_run' for r in rows}
    try:
        save(folder/'plan.json',dict(version=1,is_mock=transport.is_mock,data_kind=bundle['kind'],
             bundle_sha256=digest(bundle),rows=rows,max_calls=7))
        for row in rows:
            wait=min(120,remaining())
            if wait<=0: raise TimeoutError('Dispatch deadline')
            rid=row['run_id']; states[rid]='attempted'
            try:
                tick=time.monotonic()
                envelope=transport('generation',row['request'],wait)
                save(folder/(rid+'.json'),dict(run_id=rid,is_mock=transport.is_mock,
                    request_sha256=digest(row['request']),envelope=envelope,elapsed_seconds=time.monotonic()-tick))
                validate(envelope['message']['content'],row['item'],envelope.get('done_reason'))
                states[rid]='format_and_citation_pass'
                print(rid,'completed')
            except InvalidResult as e: states[rid]=e.category; raise
            except (Exception,KeyboardInterrupt): states[rid]='collection_failed'; raise
    finally:
        transport.stop()
        save(folder/'completion.json',dict(is_mock=transport.is_mock,states=states,human_review='pending'))


def preflight(args,now):
    if not args.approve_live or not args.environment_record or not args.deployed_at or not args.output_root:
        raise ValueError('Approval, deployment time, environment record and output root required')
    url=validate_base_url(args.base_url)
    deployed=datetime.fromisoformat(args.deployed_at)
    if deployed.tzinfo is None: raise ValueError('Timezone required')
    age=(now-deployed).total_seconds()
    if not 0<=age<2700: raise ValueError('Deployment must be less than 45 minutes old')
    env=read(args.environment_record)
    if not isinstance(env,dict) or env.get('deployed_at')!=args.deployed_at:
        raise ValueError('Environment deployment mismatch')
    if any(not env.get(k) for k in ('model_digest','ollama_version','gpu','driver','model_defaults')):
        raise ValueError('Incomplete environment')
    if not isinstance(env['model_digest'],str) or not re.fullmatch('[0-9a-f]{64}',env['model_digest']):
        raise ValueError('Full digest required')
    return url,age,env


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--approve-live',action='store_true')
    p.add_argument('--base-url')
    p.add_argument('--deployed-at')
    p.add_argument('--environment-record',type=Path)
    p.add_argument('--output-root',type=Path)
    args=p.parse_args(argv)
    bundle=load_inputs(args.inputs)
    rows=plan(bundle)
    if not args.execute:
        print('Data kind:',bundle['kind'])
        for row in rows: print(row['run_id'])
        print('DRY RUN PASS. No calls or files. Maximum 7 calls planned.')
        return
    url,age,env=preflight(args,datetime.now(timezone.utc))
    folder=args.output_root/('live-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8])
    tick=time.monotonic()
    t=RecordedTransport(base_url=url,output_dir=folder,max_calls=7,max_seconds=2700-age,timeout=120,authorize_live=True)
    try:
        save(folder/'environment.json',env)
        print('Results:',folder)
        collect(bundle,t,folder,lambda:2700-age-(time.monotonic()-tick))
    finally: t.stop()


if __name__=='__main__': main()
