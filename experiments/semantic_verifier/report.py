"""Offline JSON report. Answer key is read here only, never by inference runner."""
import argparse
from pathlib import Path
from runner import read, digest, validate, InvalidResult, LABELS, ORDER
import json


def summarize(folder,key_path):
    plan=read(folder/'plan.json'); completion=read(folder/'completion.json'); key=read(key_path)
    if type(plan.get('is_mock')) is not bool or completion.get('is_mock')!=plan['is_mock']:
        raise ValueError('Missing/mixed provenance')
    if key.get('kind')!=plan.get('data_kind') or set(key['labels'])!={'V01','V02','V03'}:
        raise ValueError('Key/data kind mismatch')
    expected_ids=['W00-A']+[rid+'-'+arm for rid,arm in ORDER]
    if [r['run_id'] for r in plan['rows']]!=expected_ids or set(completion['states'])!=set(expected_ids):
        raise ValueError('Plan/completion IDs mismatch')
    reports=[]
    for row in plan['rows']:
        if row['input_id']=='W00': continue
        label=key['labels'][row['input_id']]
        if label['expected'] not in LABELS or not isinstance(label.get('origin'),str):
            raise ValueError('Invalid key label/origin')
        rid=row['run_id']; state=completion['states'][rid]
        result=dict(run_id=rid,origin=label['origin'],expected=label['expected'],category=state,
            human_review='pending',question=row['item']['question'],target_claim=row['item']['target_claim'],
            sources=row['item']['sources'],raw=None,predicted=None)
        path=folder/(rid+'.json')
        if path.exists():
            response=read(path)
            if response['run_id']!=rid or response['is_mock']!=plan['is_mock'] or response['request_sha256']!=digest(row['request']):
                raise ValueError('Result provenance/hash mismatch')
            envelope=response['envelope']; raw=envelope['message']['content']
            result.update(raw=raw,finish_reason=envelope.get('done_reason'),
                elapsed_seconds=response['elapsed_seconds'],metrics={
                k:envelope.get(k) for k in ('load_duration','prompt_eval_count','prompt_eval_cached_count',
                                           'prompt_eval_duration','eval_count','eval_duration','total_duration')})
            try:
                parsed=validate(raw,row['item'],envelope.get('done_reason'))
                pred=parsed['verdict']; gold=label['expected']
                category=('abstained' if pred=='needs_review' else 'label_match' if pred==gold else
                          'missed_error' if pred=='supported' else 'false_alarm' if gold=='supported' else 'wrong_error_type')
                result.update(predicted=pred,category=category,empty_evidence=not parsed['evidence'])
            except InvalidResult as e: result['category']=e.category
        elif state=='format_and_citation_pass': raise ValueError('Missing completed result')
        reports.append(result)
    return dict(is_mock=plan['is_mock'],data_kind=plan['data_kind'],rows=reports,
                warning='Label match is not semantic approval. Synthetic examples are not historical performance.',
                review_questions=['판정이 원문과 맞는가?','인용이 판정을 뒷받침하는가?',
                                  '설명이 원문에 없는 관계나 범위를 추가했는가?'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True); p.add_argument('--key',type=Path,required=True)
    args=p.parse_args()
    print(json.dumps(summarize(args.run,args.key),ensure_ascii=False,indent=2))
