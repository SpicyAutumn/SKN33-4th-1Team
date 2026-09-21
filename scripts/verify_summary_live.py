"""Explicit opt-in smoke check; raw evidence is saved locally, never committed."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'app')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('--execute is required: calls configured Ollama and embedding services')
    import rag_client
    import retrieval
    from rag_service.ollama_generator import PROMPT_VERSION
    rag_client.load_env()
    missing = rag_client.missing_env()
    if missing:
        raise RuntimeError('Missing configuration: ' + ', '.join(missing))
    service = retrieval.get_service()
    generator = service.generator
    while hasattr(generator, 'delegate'):
        generator = generator.delegate
    captured = []
    original_transport = generator.transport

    def transport(url, payload, timeout):
        response = original_transport(url, payload, timeout)
        captured.append({'raw': deepcopy(response), 'payload': deepcopy(payload)})
        return response

    generator.transport = transport
    cases = [
        ('강강술래가 뭐냐', 'general'),
        ('강강술래가 뭐냐', 'advanced'),
        ('경복궁은 1395년에 완성된 것이 맞지?', 'general'),
        ('경복궁은 1400년에 완성된 것이 맞지?', 'general'),
        ('경복궁이 완성된 정확한 시각은 몇 시야?', 'general'),
        ('강강술래가 뭐냐', 'general'),
    ]
    path = ROOT / 'outputs' / 'pr15_summary_live.jsonl'
    path.parent.mkdir(exist_ok=True)
    with path.open('w', encoding='utf-8') as file:
        for question, level in cases:
            captured.clear()
            record = {'question': question, 'level': level, 'prompt_version': PROMPT_VERSION}
            try:
                result = retrieval.answer(question, audience_level=level)
                record.update(result=result, generations=deepcopy(captured))
                response = result['response']
                print(json.dumps({'question': question, 'level': level,
                    'type': response.get('response_type'), 'summary': response.get('summary'),
                    'message': response.get('message'), 'calls': len(captured)}, ensure_ascii=False), flush=True)
            except Exception as exc:
                # Exception messages can contain private service URLs.
                record.update(error_type=type(exc).__name__, generations=deepcopy(captured))
                print(json.dumps({'question': question, 'error_type': type(exc).__name__}), flush=True)
            file.write(json.dumps(record, ensure_ascii=False) + '\n')
            file.flush()


if __name__ == '__main__':
    main()
