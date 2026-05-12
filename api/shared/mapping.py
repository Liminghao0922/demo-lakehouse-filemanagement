import json
import os
from dataclasses import dataclass


@dataclass
class UserMapping:
    upn: str
    service_principal_secret_name: str


class MappingNotFoundError(Exception):
    pass


def load_user_mapping(user_upn: str) -> UserMapping:
    mapping_file = os.getenv("USER_SP_MAPPING_FILE", "config/user_sp_mapping.json")

    with open(mapping_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    users = raw.get("users", {})
    normalized_users = {k.lower(): v for k, v in users.items()}
    sp_secret_name = normalized_users.get(user_upn.lower())

    if not sp_secret_name:
        raise MappingNotFoundError(f"No mapping configured for user: {user_upn}")

    return UserMapping(
        upn=user_upn,
        service_principal_secret_name=sp_secret_name,
    )
