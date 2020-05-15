from typing import cast, List, Dict

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from keyvault2kube.secret import Secret


class KeyVaultManager(object):
    def __init__(self, vault_url: str) -> None:
        credential = cast("TokenCredential", DefaultAzureCredential())
        self._secret_client = SecretClient(vault_url=vault_url, credential=credential)

    def get_secrets(self) -> List[Secret]:
        secrets: Dict[str, Secret] = {}

        for secret in self._secret_client.list_properties_of_secrets():
            if not secret.tags:
                continue
            if 'k8s_secret_name' not in secret.tags:
                continue

            secret_value_obj = self._secret_client.get_secret(secret.name)

            secret = Secret(
                secret_value_obj.value,
                key_vault_secret_name=secret.name,
                key_vault=secret.vault_url,
                k8s_secret_name=secret.tags['k8s_secret_name'],
                last_updated=secret.updated_on,
                content_type=secret.content_type,
                k8s_secret_key=secret.tags.get('k8s_secret_key'),
                k8s_namespaces=secret.tags.get('k8s_namespaces'),
                k8s_type=secret.tags.get('k8s_type'),
                convert=secret.tags.get('k8s_convert')
            )

            # Simple joining of secrets into 1 kube secret if needed
            if secret.k8s_secret_name in secrets:
                secrets[secret.k8s_secret_name].add_key(secret)
            else:
                secrets[secret.k8s_secret_name] = secret

        return list(secrets.values())


if __name__ == '__main__':
    a = KeyVaultManager('https://terrytest2.vault.azure.net/')
    b = a.get_secrets()
    c = [x.to_yaml() for x in b]
    for s in a.get_secrets():
        for yaml in s.to_yaml().values():
            print('---')
            print(yaml)
