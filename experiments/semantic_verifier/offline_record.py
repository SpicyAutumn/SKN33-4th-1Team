"""Public, synthetic-testable record helper; no inference or file discovery.

This is not the private session-specific adapter or a semantic classifier.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

from runner import InvalidResult, pairs, validate
import json


def record(session_id, arm, input_id, attempt_id, item, raw=None,
           reason='stop', dispatched=False, original_outcome=None):
    if raw is not None and not dispatched:
        raise ValueError('Response requires a dispatched request')
    result = {
        'identity': [session_id, arm, input_id, attempt_id],
        'execution': 'received' if raw is not None else 'not_received' if dispatched else 'not_run',
        'original_outcome': original_outcome,
        'automatic_outcome': None,
        'quote_accuracy': 'uncheckable',
        'model_output': None,
        'human_review': {'state': 'pending', 'findings': None},
    }
    if raw is None:
        return result
    try:
        result['model_output'] = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, TypeError):
        pass
    try:
        output = validate(raw, item, reason)
        result['automatic_outcome'] = 'format_and_citation_pass_pending_review'
        result['quote_accuracy'] = 'pass' if output['evidence'] else 'not_applicable'
    except InvalidResult as error:
        result['automatic_outcome'] = error.category
        if error.category == 'citation_error':
            result['quote_accuracy'] = 'fail'
        elif error.category == 'missing_evidence':
            result['quote_accuracy'] = 'not_applicable'
    return result


def attach_review(row, findings, approval_reference=None):
    """Attach caller-supplied human findings, never infer them from a label."""
    result = deepcopy(row)
    if approval_reference:
        result['human_review'] = {'state': 'reviewed', 'findings': deepcopy(findings),
                                  'approval_reference': deepcopy(approval_reference)}
    return result


def verify_file(path, expected_sha256):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Source hash mismatch')
    return raw


def save_new(path, rows):
    identities = [tuple(row['identity']) for row in rows]
    if len(set(identities)) != len(identities):
        raise ValueError('Duplicate record identity')
    payload = json.dumps(rows, ensure_ascii=False, indent=2, allow_nan=False)
    with Path(path).open('x', encoding='utf-8') as f:
        f.write(payload + '\n')
