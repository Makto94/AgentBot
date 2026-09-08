import ast
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from types import SimpleNamespace
import pandas as pd

source = Path('/root/AgentBot/bot.py').read_bytes()
names = {'_normalize_ohlc', 'resample_to_4h', '_check_breakout', 'process_ticker'}
functions = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
logged = []
def fail_save(*args):
    raise RuntimeError('synthetic database failure')
ns = dict(pd=pd, datetime=datetime, timedelta=timedelta,
    _REQUIRED_COLS=('Open','High','Low','Close'), PCT_THRESHOLD=.01,
    CANDLES_TO_PERSIST=8, SR_PERIOD=2, EMA_GATE_ENABLED=False,
    logger=SimpleNamespace(error=logged.append, info=lambda *a:None),
    save_candles=fail_save, find_swing_levels=lambda *a,**k:[],
    calc_atr=lambda *a,**k:0, save_sr_levels=lambda *a:None,
    insert_signal=lambda *a:123)
exec(compile(ast.Module(body=functions, type_ignores=[]), 'bot.py AST excerpt', 'exec'), ns)
index = pd.date_range(datetime.now().replace(minute=0,second=0,microsecond=0)-timedelta(hours=15), periods=16, freq='h')
frame = pd.DataFrame({'Open':10.,'High':11.,'Low':9.,'Close':10.,'Volume':100}, index=index)
result = ns['process_ticker']('SYNTHETIC', frame, 1, {}, {})
assert len(logged) == 2 and result == (0,0,0), (logged,result)
print('Two candle writes failed; reported errors:', result[2])
logged.clear()
ns['save_candles'] = lambda *a: None
frame.loc[index[-1], ['High','Close']] = [13.,12.]
with_volume = ns['process_ticker']('SYNTHETIC', frame, 1, {}, {})
missing_volume = frame.drop(columns=['Volume'])
assert ns['_normalize_ohlc'](missing_volume) is not None
without_volume = ns['process_ticker']('SYNTHETIC', missing_volume, 1, {}, {})
assert with_volume == (1,0,0), with_volume
assert without_volume == (0,0,0) and not logged, (without_volume,logged)
print('Identical OHLC: with Volume=',with_volume,'without Volume=',without_volume,'logged errors=',len(logged))
print('bot.py SHA256:',hashlib.sha256(source).hexdigest())
