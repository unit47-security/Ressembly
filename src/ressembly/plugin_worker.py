"""Internal worker: only invoked after explicit trust. No automatic plugin discovery."""
import json
import resource
import sys

resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
# RLIMIT_AS is not consistently usable on macOS; no memory-isolation claim.
request = json.loads(sys.stdin.buffer.read(1024 * 1024 + 1))
namespace = {'__name__': 'ressembly_trusted_plugin', '__file__': '<explicitly-trusted-plugin>'}
exec(compile(request['code'], '<explicitly-trusted-plugin>', 'exec'), namespace)
result = namespace['analyze'](request['snapshot'])
sys.stdout.write(json.dumps(result, allow_nan=False, ensure_ascii=True))
