"""Bounded retries for transient remote inference errors. Never retries invalid credentials or validation errors."""
from __future__ import annotations
import random
import re
import time

TRANSIENT_CODES = {429, 503, 504}

def error_code(exc):
    """Derive HTTP status from common Google SDK exceptions (fallback to message)."""
    for attr in ('code', 'status_code'):
        val = getattr(exc, attr, None)
        if callable(val):
            try: val = val()
            except Exception: val = None
        if isinstance(val, int) and 100 <= val <= 599: return val
        if isinstance(val, str) and val.isdigit(): return int(val)
    message=str(exc)
    m=re.search(r'(?<!\d)(429|503|504)(?!\d)', message)
    return int(m.group(1)) if m else None

def classify_exception(exc):
    code=error_code(exc)
    return ('API_ERROR' if code in (400,401,403,404,408,409,429,500,502,503,504) else 'RUNTIME_ERROR',code)

def call_with_retry(invoke, *, max_retries=1, base_delay=2.0, sleep=time.sleep, jitter=random.random):
    if max_retries < 0 or max_retries > 5: raise ValueError('max_retries must be 0..5')
    if base_delay < 0 or base_delay > 60: raise ValueError('base_delay must be 0..60')
    retries=0
    while True:
        try:
            return invoke(), retries
        except Exception as exc:
            if error_code(exc) not in TRANSIENT_CODES or retries >= max_retries:
                # preserves last error and number of attempted retries for reporting
                try: setattr(exc,'fg_retry_count',retries)
                except Exception: pass
                raise
            delay=min(30.0,base_delay*(2**retries)) + min(1.0,max(0.0,float(jitter())))
            retries += 1
            sleep(delay)
