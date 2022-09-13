import logging
import sys
from typing import Dict, List, cast

import azure.core.exceptions
import pylogrus
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from keyvault2kube.secret import Secret

logging.setLoggerClass(pylogrus.PyLogrus)


class KeyVaultManager(object):
    def __init__(self, vault_url: str) -> None:
        self.url = vault_url
        self.logger = cast(pylogrus.PyLogrus, logging.getLogger("keyvault2kube.keyvault")).withFields(
            {"vault": vault_url}
        )
        credential = cast(DefaultAzureCredential())
        self._secret_client = SecretClient(vault_url=vault_url, credential=credential)

    def get_secrets(self) -> List[Secret]:
        secrets: Dict[str, Secret] = {}

        try:
            for secret in self._secret_client.list_properties_of_secrets():
                if not secret.tags:
                    continue
                if "k8s_secret_name" not in secret.tags:
                    continue

                try:
                    secret_value_obj = self._secret_client.get_secret(secret.name)
                except Exception as err:
                    self.logger.withFields({"secret": secret.name}).exception(
                        "Failed to get secret from KeyVault", exc_info=err
                    )
                    continue

                secret = Secret(
                    secret_value_obj.value,
                    secret_version=secret_value_obj.properties.version,
                    key_vault_secret_name=secret.name,
                    key_vault=secret.vault_url,
                    k8s_secret_name=secret.tags["k8s_secret_name"],
                    last_updated=secret.updated_on,
                    content_type=secret.content_type,
                    k8s_secret_key=secret.tags.get("k8s_secret_key"),
                    k8s_namespaces=secret.tags.get("k8s_namespaces"),
                    k8s_type=secret.tags.get("k8s_type"),
                    convert=secret.tags.get("k8s_convert"),
                )

                # Simple joining of secrets into 1 kube secret if needed
                if secret.k8s_secret_name in secrets:
                    secrets[secret.k8s_secret_name].add_key(secret)
                else:
                    secrets[secret.k8s_secret_name] = secret
        except azure.core.exceptions.ClientAuthenticationError as err:
            self.logger.exception("No credentials available", exc_info=err)
            sys.exit(1)

        except Exception as err:
            self.logger.exception("Failed to list secrets from KeyVault", exc_info=err)

        return list(secrets.values())
