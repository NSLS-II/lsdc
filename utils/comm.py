import json
from typing import Dict, List, Optional


def generate_server_message(
    function_name: str, args: Optional[List] = None, kwargs: Optional[Dict] = None
) -> str:
    if not args:
        args = []
    if not kwargs:
        kwargs = {}
    return json.dumps(
        {
            "function": function_name,
            "args": args,
            "kwargs": kwargs,
        }
    )
