import json
import os
from dataclasses import dataclass

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


@dataclass
class ServicePrincipalConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    onelake_account_name: str
    workspace_name: str
    lakehouse_name: str
    root_path: str


class KeyVaultConfigError(Exception):
    pass


def load_json_secret(secret_name: str) -> dict:
    key_vault_url = os.getenv("KEY_VAULT_URL")
    if not key_vault_url:
        raise KeyVaultConfigError("Missing KEY_VAULT_URL environment variable.")

    secret_client = SecretClient(vault_url=key_vault_url, credential=DefaultAzureCredential())
    secret_bundle = secret_client.get_secret(secret_name)

    try:
        return json.loads(secret_bundle.value)
    except json.JSONDecodeError as exc:
        raise KeyVaultConfigError(
            f"Secret '{secret_name}' must contain a JSON payload."
        ) from exc


def load_service_principal_config(secret_name: str) -> ServicePrincipalConfig:
    payload = load_json_secret(secret_name)

    workspace_name = payload["workspace_name"]
    lakehouse_name = payload["lakehouse_name"]

    return ServicePrincipalConfig(
        tenant_id=payload["tenant_id"],
        client_id=payload["client_id"],
        client_secret=payload["client_secret"],
        onelake_account_name=payload.get("onelake_account_name", "onelake"),
        workspace_name=workspace_name,
        lakehouse_name=lakehouse_name,
        root_path=payload.get("root_path", f"{lakehouse_name}.Lakehouse/Files"),
    )
