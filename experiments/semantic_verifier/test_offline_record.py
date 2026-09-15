"""Synthetic fixtures only; no private experiment inputs or model calls."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from offline_record import attach_review, record, save_new, verify_file


class OfflineRecordTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden'))
        guard.start()
        self.addCleanup(guard.stop)
        self.item = {'sources': [{'source_ref': 'S1', 'text': 'The box is blue. Literal ... text.'}]}

    def make(self, label='supported', quote='The box is blue.', **kwargs):
        evidence = [] if quote is None else [{'source_ref': 'S1', 'quote': quote}]
        raw = json.dumps({'verdict': label, 'evidence': evidence, 'explanation': 'Synthetic explanation.'})
        return record('session', 'model', 'case', 1, self.item, raw, dispatched=True, **kwargs)

    def test_exact_does_not_imply_semantic_pass(self):
        r = self.make()
        self.assertEqual(r['quote_accuracy'], 'pass')
        self.assertEqual(r['human_review']['state'], 'pending')

    def test_empty_evidence(self):
        for label in ('unsupported', 'needs_review'):
            self.assertEqual(self.make(label, None)['quote_accuracy'], 'not_applicable')
        for label in ('supported', 'contradicted', 'meaning_weakened'):
            self.assertEqual(self.make(label, None)['automatic_outcome'], 'missing_evidence')

    def test_strict_quotes(self):
        self.assertEqual(self.make(quote='Literal ... text.')['quote_accuracy'], 'pass')
        for quote in ('The box\nis blue.', 'The ... blue.', 'blue. The box is'):
            self.assertEqual(self.make(quote=quote)['automatic_outcome'], 'citation_error')

    def test_failed_and_not_run_separate(self):
        failed = record('old', 'Q', 'C1', 1, self.item, dispatched=True)
        not_run = record('old', 'Q', 'C2', 1, self.item)
        self.assertEqual(failed['execution'], 'not_received')
        self.assertEqual(not_run['execution'], 'not_run')
        self.assertIsNone(failed['automatic_outcome'])

    def test_review_requires_reference_and_preserves_original(self):
        row = self.make(original_outcome='original-value')
        self.assertEqual(attach_review(row, {'evidence': 'insufficient'})['human_review']['state'], 'pending')
        reviewed = attach_review(row, {'evidence': 'insufficient'}, 'review-1')
        self.assertEqual(reviewed['human_review']['findings']['evidence'], 'insufficient')
        self.assertEqual(reviewed['original_outcome'], 'original-value')
        self.assertEqual(row['human_review']['state'], 'pending')

    def test_incomplete_and_format(self):
        self.assertEqual(self.make(reason='length')['automatic_outcome'], 'truncated_or_incomplete')
        row = record('s', 'a', 'c', 1, self.item, '{"x":1,"x":2}', dispatched=True)
        self.assertEqual(row['automatic_outcome'], 'format_error')

    def test_no_overwrite_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'records.json'
            save_new(path, [self.make()])
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): save_new(path, [self.make()])
            with self.assertRaises(ValueError): verify_file(path, 'invalid')
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError): save_new(Path(tmp)/'duplicate.json', [self.make(), self.make()])


if __name__ == '__main__':
    unittest.main()
