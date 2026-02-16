# cgpe/utils/json.py

from typing import Any, Optional
import json

def safe_dumps(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    return json.dumps(v)


def safe_loads(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    return json.loads(v)