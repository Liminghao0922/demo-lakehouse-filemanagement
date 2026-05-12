import json
import os
from dataclasses import dataclass

from shared.keyvault import KeyVaultConfigError, load_json_secret


@dataclass
class UserMapping:
    upn: str
    service_principal_secret_name: str


class MappingNotFoundError(Exception):
    pass


def _load_mapping_data() -> dict:
    mapping_secret_name = os.getenv("USER_SP_MAPPING_SECRET_NAME")
    mapping_file = os.getenv("USER_SP_MAPPING_FILE", "config/user_sp_mapping.json")

    if mapping_secret_name:
        try:
            return load_json_secret(mapping_secret_name)
        except Exception:
            allow_fallback = os.getenv("USER_SP_MAPPING_ALLOW_FILE_FALLBACK", "true").lower() == "true"
            if not allow_fallback:
                raise

    with open(mapping_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_user_mapping(user_upn: str) -> UserMapping:
    try:
        raw = _load_mapping_data()
    except (FileNotFoundError, json.JSONDecodeError, KeyVaultConfigError) as exc:
        raise MappingNotFoundError(f"Failed to load user mapping configuration: {exc}") from exc

    users = raw.get("users", {})
    normalized_users = {k.lower(): v for k, v in users.items()}
    sp_secret_name = normalized_users.get(user_upn.lower())

    if not sp_secret_name:
        raise MappingNotFoundError(f"No mapping configured for user: {user_upn}")

    return UserMapping(
        upn=user_upn,
        service_principal_secret_name=sp_secret_name,
    )
