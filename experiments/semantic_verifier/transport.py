"""Explicit opt-in transport only. No CLI, environment loading, or automatic calls.

Not connected to run_mock.py: that runner must never label live requests mock.
"""
import copy
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlsplit


class TransportStopped(RuntimeError):
    pass


def validate_base_url(url):
    # Literal loopback only: no DNS resolution, credentials, proxies or redirects.
    if not isinstance(url, str) or not re.fullmatch(r'http://127\.0\.0\.1:[0-9]{1,5}/?', url):
        raise ValueError('Use explicit http://127.0.0.1:PORT')
    port = urlsplit(url).port
    if not port or not 1 <= port <= 65535:
        raise ValueError('Invalid port')
    return url.rstrip('/')


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


class RecordedTransport:
    def __init__(self, *, base_url, output_dir, max_calls, max_seconds, timeout,
                 authorize_live=False, session=None, clock=time.monotonic,
                 max_response_bytes=4 * 1024 * 1024):
        self.base_url = validate_base_url(base_url)
        if type(max_calls) is not int or not 1 <= max_calls <= 100:
            raise ValueError('Explicit max_calls must be 1..100')
        if not positive(max_seconds) or not positive(timeout):
            raise ValueError('Explicit finite positive time limits required')
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError('Invalid response size limit')
        if session is None and authorize_live is not True:
            raise ValueError('Live authorization required')
        if session is not None and authorize_live:
            raise ValueError('Do not label injected test transport live')
        self.is_mock = session is not None
        self.folder = Path(output_dir)
        self.folder.mkdir(parents=True, exist_ok=False)
        self.clock = clock
        self.started = clock()
        self.max_calls, self.max_seconds, self.timeout = max_calls, max_seconds, timeout
        self.max_response_bytes = max_response_bytes
        self.calls = 0
        self.stopped = False
        self.session = session
        # Lazy construction: no requests import or connection during validation.
        self._write('transport-config.json', {
            'is_mock': self.is_mock, 'max_calls': max_calls, 'max_seconds': max_seconds,
            'timeout': timeout, 'max_response_bytes': max_response_bytes,
            'automatic_retry': False, 'hard_deadline': False,
            'warning': 'Client timeout does not cancel server inference or stop Pod billing'})

    def _write(self, name, obj):
        with (self.folder / name).open('x', encoding='utf-8') as stream:
            json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)

    def _remaining(self):
        return self.max_seconds - (self.clock() - self.started)

    def _session(self):
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.trust_env = False
            self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=0))
        return self.session

    def __call__(self, stage, payload, request_timeout):
        if self.stopped:
            raise TransportStopped('Transport already stopped')
        response = None
        prefix = f'{self.calls + 1:03}'
        try:
            if stage not in ('selection', 'generation'):
                raise ValueError('Invalid stage')
            if not positive(request_timeout):
                raise ValueError('Invalid requested timeout')
            if self.calls >= self.max_calls or self._remaining() <= 0:
                raise TimeoutError('Budget exhausted')
            if not isinstance(payload, dict) or payload.get('stream') is not False:
                raise ValueError('Nonstreaming payload required')
            # Write before dispatch; a disk failure must prevent network usage.
            self._write(prefix+'-input.json', {'stage': stage, 'payload': copy.deepcopy(payload),
                                              'is_mock': self.is_mock})
            wait = min(self.timeout, request_timeout, self._remaining())
            if wait <= 0:
                raise TimeoutError('Deadline reached before dispatch')
            self.calls += 1  # attempts, including failures; no retries
            tick = self.clock()
            response = self._session().post(self.base_url+'/api/chat', json=copy.deepcopy(payload),
                timeout=(min(5.0, wait), wait), allow_redirects=False, stream=True)
            self._write(prefix+'-http.json', {'status_code': response.status_code,
                                            'is_mock': self.is_mock})
            if response.status_code != 200:
                raise ValueError('Non-200 HTTP response')
            data = bytearray()
            with (self.folder / (prefix+'-raw.bin')).open('xb') as stream:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        if len(data) + len(chunk) > self.max_response_bytes:
                            raise ValueError('Response byte limit exceeded')
                        stream.write(chunk)
                        data.extend(chunk)
                    if self._remaining() <= 0 or self.clock()-tick > wait:
                        raise TimeoutError('Response deadline exceeded')
            if self._remaining() <= 0 or self.clock()-tick > wait:
                raise TimeoutError('Response deadline exceeded')
            envelope = json.loads(data.decode('utf-8'))
            if not isinstance(envelope, dict) or envelope.get('done') is not True:
                raise ValueError('Incomplete envelope')
            if envelope.get('done_reason') != 'stop':
                raise ValueError('Truncated or unknown finish reason')
            if not isinstance(envelope.get('message'), dict) or not isinstance(envelope['message'].get('content'), str):
                raise ValueError('Missing model content')
            self._write(prefix+'-result.json', {'stage': stage, 'envelope': envelope,
                'elapsed_seconds': self.clock()-tick, 'is_mock': self.is_mock,
                'quality_score': None, 'human_review_status': 'pending'})
            return envelope
        except (Exception, KeyboardInterrupt) as error:
            self.stopped = True
            try:
                self._write(prefix+'-failure.json', {'stage': stage, 'error_type': type(error).__name__,
                    'attempted_calls': self.calls, 'is_mock': self.is_mock,
                    'automatic_retry': False})
            except Exception:
                pass  # Disk failure can prevent status persistence; remain stopped.
            if isinstance(error, KeyboardInterrupt):
                raise
            raise TransportStopped(type(error).__name__) from None
        finally:
            if response is not None:
                response.close()

    def stop(self):
        self.stopped = True
        if self.session is not None:
            self.session.close()
