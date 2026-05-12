import base64
import json
import os
from typing import Optional

import azure.functions as func


def _decode_client_principal(header_value: str) -> dict:
    decoded = base64.b64decode(header_value)
    return json.loads(decoded)


def get_user_upn(req: func.HttpRequest) -> Optional[str]:
    principal_header = req.headers.get("x-ms-client-principal")
    if principal_header:
        principal = _decode_client_principal(principal_header)
        return principal.get("userDetails")

    # Local development fallback (disabled by default in cloud).
    allow_local = os.getenv("ALLOW_LOCAL_DEV_AUTH", "false").lower() == "true"
    if allow_local:
        return os.getenv("DEV_USER_UPN")

    return None
