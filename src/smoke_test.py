"""Start a real headless Streamlit server, check health, and stop it cleanly."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen


def run():
    import importlib.util
    assert importlib.util.find_spec('app') is not None
    with socket.socket() as s:
        s.bind(('127.0.0.1',0))
        port=s.getsockname()[1]
    log=Path('data/results/streamlit_startup.log')
    status={'status':'failed','health_response':None,'stopped':False}
    log.parent.mkdir(parents=True, exist_ok=True)
    Path('data/results/streamlit_smoke.json').write_text(json.dumps(status,indent=2))
    with log.open('w',encoding='utf-8') as stream:
        process=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.headless','true',
            '--server.address','127.0.0.1','--server.port',str(port),'--browser.gatherUsageStats','false'],stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    raise RuntimeError(f'Streamlit exited early: {log.read_text()}')
                try:
                    with urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=2) as response:
                        body=response.read().decode()
                        if response.status==200 and body=='ok':
                            status.update(status='passed',health_response=body)
                            break
                except OSError:
                    time.sleep(.3)
            if status['status']!='passed':
                raise RuntimeError('Streamlit health endpoint did not become ready')
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            status['stopped']=process.poll() is not None
            Path('data/results/streamlit_smoke.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status))


if __name__=='__main__':
    run()
