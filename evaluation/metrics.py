"""Report request availability separately from model tool-selection accuracy."""
from __future__ import annotations
from collections import Counter

def summarize_live(rows, *, skipped=None):
    skipped=skipped or []
    n=len(rows)
    success=[r for r in rows if r['execution_status'] in ('PASS','TOOL_MISMATCH')]
    passes=[r for r in success if r['execution_status']=='PASS']
    valid=len(success)
    durations=[float(r['seconds']) for r in success]
    status_counts=Counter(r['execution_status'] for r in rows)
    return {
        'attempted':n,
        'api_success_count':valid,
        'api_success_rate':round(valid/n,4) if n else None,
        'valid_tool_selection_passes':len(passes),
        'valid_tool_selection_accuracy':round(len(passes)/valid,4) if valid else None,
        'end_to_end_tool_success_rate':round(len(passes)/n,4) if n else None,
        'status_counts':dict(status_counts),
        'total_retry_count':sum(int(r['retry_count']) for r in rows),
        'average_success_seconds':round(sum(durations)/len(durations),3) if durations else None,
        'skipped_cases':[x['id'] for x in skipped],
        'note':'API errors excluded from valid tool accuracy; tool trace alone does not prove answer correctness, groundedness or safety.'
    }
