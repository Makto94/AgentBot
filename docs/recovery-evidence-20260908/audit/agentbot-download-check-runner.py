import os
from pathlib import Path
import sys
import types

available = next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
pressure = float(Path('/proc/pressure/memory').read_text().splitlines()[0].split()[1].split('=')[1])
print(f'MemAvailable={available} KiB; memory PSI some avg10={pressure}', flush=True)
if available < 4 * 1024 * 1024 or pressure > 5:
    print('RESOURCE GATE: deferred', flush=True)
    sys.exit(75)

os.environ.update(POSTGRES_PASSWORD='test', TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_ID='', LOG_FILE='/tmp/system-efficiency-20260908/agentbot-offline-test-app.log')
sys.path.insert(0, '/root/AgentBot/tests')
import conftest

def deny_db(*args, **kwargs):
    raise AssertionError('Unexpected DB access in offline diagnostic check')

driver = types.ModuleType('psycopg2')
driver.extensions = types.SimpleNamespace(connection=object)
driver.connect = deny_db
driver.extras = types.ModuleType('psycopg2.extras')
driver.extras.RealDictCursor = object
driver.extras.execute_values = deny_db
sys.modules['psycopg2'] = driver
sys.modules['psycopg2.extras'] = driver.extras

from test_download_diagnostics import test_scan_logs_all_final_failures_and_excludes_recovered
test_scan_logs_all_final_failures_and_excludes_recovered()
print('PASS: full final-failure list beyond 20 symbols; recovered symbols excluded; counters and processing preserved; no warning when all recover')
