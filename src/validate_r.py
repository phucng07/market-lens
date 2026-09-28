"""Run R when available, reporting execution truthfully."""
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from .config import RESULTS


def run():
    executable = shutil.which('Rscript')
    if not executable and os.name == 'nt':
        candidates = sorted(Path(os.environ.get('ProgramFiles', '')).glob('R/R-*/bin/Rscript.exe'),
                            key=lambda path: tuple(map(int, re.findall(r'\d+', path.parents[1].name))))
        executable = str(candidates[-1]) if candidates else None
    if not executable:
        status = {'status': 'unavailable', 'message': 'Rscript was not found; R validation was not executed.'}
    else:
        environment = os.environ.copy()
        if os.name == 'nt':
            environment['LC_ALL'] = 'C'
            environment['LANG'] = 'C'
        try:
            result = subprocess.run([executable, '--vanilla', 'R/validation_analysis.R'], capture_output=True, text=True, timeout=120, env=environment)
            status = {'status': 'passed' if result.returncode == 0 else 'failed',
                      'message': result.stdout.strip(), 'stderr': result.stderr.strip(), 'returncode': result.returncode}
        except (OSError, subprocess.SubprocessError) as error:
            status = {'status': 'failed', 'message': str(error)}
    (RESULTS / 'r_validation.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    if status['status'] == 'failed':
        raise RuntimeError(f'R validation failed: {status}')
    return status
