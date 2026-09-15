"""Container-only cell execution. The parent supplies isolation and grades the returned value."""
from contextlib import redirect_stderr, redirect_stdout
import importlib
from importlib.metadata import version
import io
import json
import keyword
import math
from pathlib import Path
import re
import sys


class OutputLimit(Exception):
    pass


class Capture(io.TextIOBase):
    def __init__(self):
        self.parts, self.length, self.exceeded = [], 0, False

    def write(self, text):
        if not isinstance(text, str):
            raise TypeError('Text output requires a string.')
        if self.exceeded:
            raise OutputLimit('Python output exceeded 8192 characters.')
        remaining = 8192 - self.length
        if text and remaining:
            self.parts.append(text[:remaining])
        self.length += min(len(text), remaining)
        if len(text) > remaining:
            self.exceeded = True
            raise OutputLimit('Python output exceeded 8192 characters.')
        return len(text)


def error(kind, exc):
    try:
        message = str(exc)[:2048]
    except BaseException:
        message = 'Error text unavailable.'
    return {'kind': kind, 'error': {'type': type(exc).__name__, 'message': message}}


def main():
    protocol = sys.stdout

    def emit(value):
        protocol.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n')
        protocol.flush()

    try:
        if not Path('/.dockerenv').exists():
            raise RuntimeError('Run this worker only inside its isolated Docker container.')
        raw = sys.stdin.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('Input exceeds 1 MiB.')
        request = json.loads(raw)
        if set(request) != {'source', 'library', 'library_version', 'table', 'column', 'result', 'values'}:
            raise ValueError('Unexpected worker input fields.')
        if (not isinstance(request['source'], str) or request['library'] not in ('pandas', 'babypandas')
                or not isinstance(request['library_version'], str) or not request['library_version']
                or not isinstance(request['column'], str) or not request['column']
                or not isinstance(request['values'], list)
                or any(not isinstance(value, str) for value in request['values'])):
            raise ValueError('Supply source, a declared library version, a column and string values.')
        for key in ('table', 'result'):
            name = request[key]
            if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name)
                    or keyword.iskeyword(name) or name == '__builtins__'):
                raise ValueError('Use non-keyword ASCII identifiers other than __builtins__.')
        libraries = {name: version(name) for name in ('pandas', 'babypandas', 'numpy')}
    except BaseException as exc:
        emit(error('environment-error', exc))
        return
    emit({'kind': 'runtime', 'python': sys.version.split()[0], 'libraries': libraries, 'library': request['library']})
    capture = Capture()
    with redirect_stdout(capture), redirect_stderr(capture):
        try:
            if libraries[request['library']] != request['library_version']:
                raise RuntimeError('Installed library version differs from the declared version.')
            library = importlib.import_module(request['library'])
            numpy = importlib.import_module('numpy')
            namespace = {request['table']: library.DataFrame(data={request['column']: request['values']})}
        except BaseException as exc:
            response = error('environment-error', exc)
        else:
            try:
                exec(compile(request['source'], '<submitted-cell>', 'exec'), namespace)
                if request['result'] not in namespace:
                    raise NameError(f"Result variable {request['result']!r} is not defined.")
                value = namespace[request['result']]
                value_type = type(value).__name__
                if isinstance(value, numpy.generic):
                    value = value.item()
                if type(value) not in (str, int, float, bool, type(None)):
                    value = None
                if type(value) is float and not math.isfinite(value):
                    raise ValueError('Result is not a finite JSON scalar.')
                response = {'kind': 'value', 'value': value, 'value_type': value_type}
            except BaseException as exc:
                response = error('runtime-error', exc)
    if capture.exceeded:
        response = {'kind': 'output-limit'}
    response['output'] = ''.join(capture.parts)
    emit(response)


if __name__ == '__main__':
    main()
