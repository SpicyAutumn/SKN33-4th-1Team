import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import runner
from report import summarize
from transport import RecordedTransport, TransportStopped


class FakeHTTPResponse:
    status_code = 200
    def __init__(self, envelope):
        self.data = json.dumps(envelope).encode('utf-8')
        self.closed = False
    def iter_content(self, chunk_size):
        yield self.data
    def close(self): self.closed = True


class FakeHTTPSession:
    def __init__(self, envelopes):
        self.responses = [FakeHTTPResponse(e) for e in envelopes]
        self.calls = 0
        self.closed = False
    def post(self, url, **kwargs):
        response = self.responses[self.calls]
        self.calls += 1
        return response
    def close(self): self.closed = True


class Fake:
    is_mock=True
    def __init__(self,bad=False): self.calls=0; self.bad=bad; self.closed=False
    def __call__(self,stage,payload,timeout):
        self.calls+=1
        return dict(done_reason='stop',message=dict(content=json.dumps(dict(verdict='needs_review',
            evidence=[dict(source_ref='S1',quote='nonexistent')] if self.bad else [],explanation='mock'))))
    def stop(self): self.closed=True


class Tests(unittest.TestCase):
    def setUp(self): self.bundle=runner.load_inputs(runner.HERE/'example_inputs.json')
    def test_order(self):
        self.assertEqual([r['run_id'] for r in runner.plan(self.bundle)],
            ['W00-A','V02-A','V02-B','V01-B','V01-A','V03-A','V03-B'])
    def test_only_prompt_changes(self):
        rows=runner.plan(self.bundle)
        for rid in ('V01','V02','V03'):
            a,b=[r['request'] for r in rows if r['input_id']==rid]
            self.assertEqual(a['messages'][1],b['messages'][1])
            self.assertNotEqual(a['messages'][0],b['messages'][0])
            for k in ('model','options','format','stream'): self.assertEqual(a[k],b[k])
    def test_no_label_in_payload(self):
        for r in runner.plan(self.bundle):
            self.assertEqual(set(json.loads(r['request']['messages'][1]['content'])),
                             {'question','target_claim','response_context','sources'})
    def test_input_rejects_key(self):
        with tempfile.TemporaryDirectory() as d:
            b=copy.deepcopy(self.bundle); b['inputs'][0]['expected']='supported'
            p=Path(d)/'in.json'; runner.save(p,b)
            with self.assertRaises(ValueError): runner.load_inputs(p)
    def test_duplicate_id(self):
        with tempfile.TemporaryDirectory() as d:
            b=copy.deepcopy(self.bundle); b['inputs'][1]['input_id']='V01'
            p=Path(d)/'in.json'; runner.save(p,b)
            with self.assertRaises(ValueError): runner.load_inputs(p)
    def test_duplicate_json(self):
        with self.assertRaises(ValueError): json.loads('{"a":1,"a":2}',object_pairs_hook=runner.pairs)
    def test_invalid_quote(self):
        with self.assertRaises(runner.InvalidResult):
            runner.validate(json.dumps(dict(verdict='supported',evidence=[dict(source_ref='S1',quote='absent')],explanation='x')),
                            self.bundle['inputs'][0],'stop')
    def test_truncation(self):
        with self.assertRaises(runner.InvalidResult): runner.validate('{}',{},'length')
    def test_dry_no_transport(self):
        with patch.object(runner,'RecordedTransport') as transport:
            runner.main(['--inputs',str(runner.HERE/'example_inputs.json')]); transport.assert_not_called()
    def test_missing_approval(self):
        with patch.object(runner,'RecordedTransport') as t:
            with self.assertRaises(ValueError): runner.main(['--inputs',str(runner.HERE/'example_inputs.json'),'--execute'])
            t.assert_not_called()
    def test_full_mock_report(self):
        with tempfile.TemporaryDirectory() as d:
            t=Fake(); runner.collect(self.bundle,t,Path(d),lambda:100)
            r=summarize(Path(d),runner.HERE/'example_key.json')
            self.assertEqual(t.calls,7); self.assertTrue(t.closed); self.assertTrue(r['is_mock'])
            self.assertEqual(len(r['rows']),6)
            self.assertTrue(all(x['category']=='abstained' for x in r['rows']))
    def test_stop_preserve(self):
        with tempfile.TemporaryDirectory() as d:
            t=Fake(True)
            with self.assertRaises(runner.InvalidResult): runner.collect(self.bundle,t,Path(d),lambda:100)
            self.assertEqual(t.calls,1); self.assertTrue((Path(d)/'W00-A.json').exists())
            r=summarize(Path(d),runner.HERE/'example_key.json')
            self.assertTrue(all(x['category']=='not_run' for x in r['rows']))
    def test_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            t=Fake()
            with self.assertRaises(TimeoutError): runner.collect(self.bundle,t,Path(d),lambda:0)
            self.assertEqual(t.calls,0)
    def test_stale_environment(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'env.json'; runner.save(p,{'deployed_at':'old'})
            args=SimpleNamespace(approve_live=True,environment_record=p,deployed_at='2026-09-10T00:00:00+00:00',
                                 output_root=Path(d),base_url='http://127.0.0.1:11435')
            with self.assertRaises(ValueError): runner.preflight(args,datetime(2026,9,10,0,1,tzinfo=timezone.utc))

    def check_http_truncation(self, reason, content):
        warm = dict(done=True, done_reason='stop', message=dict(content=json.dumps(dict(
            verdict='needs_review', evidence=[], explanation='mock warmup'))))
        short = dict(done=True, message=dict(content=content))
        if reason is not None: short['done_reason'] = reason
        session = FakeHTTPSession([warm, short])
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)/'run'
            transport = RecordedTransport(base_url='http://127.0.0.1:11435',output_dir=folder,
                max_calls=7,max_seconds=120,timeout=30,session=session)
            with self.assertRaises(runner.InvalidResult) as caught:
                runner.collect(self.bundle,transport,folder,lambda:100)
            self.assertEqual(caught.exception.category,'truncated_or_incomplete')
            self.assertEqual(session.calls,2)
            self.assertTrue(session.closed)
            self.assertTrue(all(r.closed for r in session.responses))
            self.assertEqual((folder/'002-raw.bin').read_bytes(),session.responses[1].data)
            self.assertEqual(runner.read(folder/'V02-A.json')['envelope']['message']['content'],content)
            states=runner.read(folder/'completion.json')['states']
            self.assertEqual(states['V02-A'],'truncated_or_incomplete')
            self.assertEqual(states['V02-B'],'not_run')
            report=summarize(folder,runner.HERE/'example_key.json')
            first=report['rows'][0]
            self.assertEqual(first['raw'],content)
            self.assertEqual(first['finish_reason'],reason)
            self.assertEqual(first['category'],'truncated_or_incomplete')
            self.assertIsNone(first['predicted'])
            self.assertTrue(all(r['category']=='not_run' for r in report['rows'][1:]))

    def test_http_length_preserved_in_report(self):
        self.check_http_truncation('length','{"verdict":"supported", "explanation":"unfinished')

    def test_http_unknown_finish_not_accepted(self):
        self.check_http_truncation('unknown','{"verdict":"supported","evidence":[],"explanation":"mock"}')

    def test_http_missing_finish_not_accepted(self):
        self.check_http_truncation(None,'partial output')

    def test_incomplete_http_envelope_still_rejected(self):
        session=FakeHTTPSession([dict(done=False,message=dict(content='partial'))])
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'run'
            t=RecordedTransport(base_url='http://127.0.0.1:11435',output_dir=folder,
                max_calls=7,max_seconds=120,timeout=30,session=session)
            with self.assertRaises(TransportStopped):
                runner.collect(self.bundle,t,folder,lambda:100)
            self.assertEqual(session.calls,1)
            self.assertTrue((folder/'001-raw.bin').exists())
            self.assertEqual(runner.read(folder/'completion.json')['states']['W00-A'],'collection_failed')


if __name__=='__main__': unittest.main()
