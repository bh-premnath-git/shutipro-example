import os
import hvac
from kyc_adapter import ShuftiProAdapter


def get_shuftipro_adapter() -> ShuftiProAdapter:
    vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200")
    vault_token = os.getenv("VAULT_TOKEN", "root")

    client = hvac.Client(url=vault_addr, token=vault_token)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")

    secret = client.secrets.kv.v2.read_secret_version(path="shuftipro")
    data = secret["data"]["data"]
    client_id = data["client_id"]
    secret_key = data["secret_key"]

    return ShuftiProAdapter(client_id=client_id, secret_key=secret_key)
