import datetime
import os
import subprocess
import sys
from pathlib import Path

stage, *args = sys.argv[1:]
result = subprocess.run([str(Path('.venv/bin/pytest')), '-q', *args], env={**os.environ, 'PYTHONPATH': str(Path('src').resolve())}, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
entry = f'\n{datetime.datetime.now(datetime.timezone.utc).isoformat()} {stage} {args} exit={result.returncode}\n{result.stdout}'
with Path('.scratch/sharey-mvp/tdd.log').open('a') as log:
    log.write(entry)
print(entry)
expected_failure = stage == 'RED'
sys.exit(0 if ((result.returncode == 1) if expected_failure else (result.returncode == 0)) else 1)
