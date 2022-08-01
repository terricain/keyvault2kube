import logging
from typing import List, Optional, cast

import pylogrus
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

from keyvault2kube.secret import Secret

logging.setLoggerClass(pylogrus.PyLogrus)
logger = cast(pylogrus.PyLogrus, logging.getLogger("keyvault2kube.kube"))


def load_config():
    try:
        logger.info("Looking for Kubernetes cluster config")
        config.load_incluster_config()
    except ConfigException:
        logger.info("Looking for Kubernetes ~/.kube/config")
        try:
            config.load_kube_config()
        except ConfigException as err:
            logger.exception("Failed to find any useable Kubernetes config", exc_info=err)
            raise err


class KubeSecretManager(object):
    def __init__(self):
        self.logger = logger
        self.client = client.CoreV1Api()

    def update_secrets(self, secrets: List[Secret]) -> None:
        for secret in secrets:
            for ns, secret_obj in secret.to_kubesecret(self.client):
                # Get secret if it exists
                kube_secret: Optional[client.V1Secret] = None
                try:
                    kube_secret = self.client.read_namespaced_secret(name=secret_obj.metadata.name, namespace=ns)
                except ApiException as err:
                    if err.reason == "Not Found":
                        pass
                    else:
                        self.logger.withFields({"secret": secret_obj.metadata.name}).exception(
                            "Failed to read secret", exc_info=err
                        )
                        continue

                if kube_secret is None:
                    # Create secret
                    try:
                        self.client.create_namespaced_secret(namespace=ns, body=secret_obj)
                        self.logger.info(f"Created secret {secret_obj.metadata.name} in namespace {ns}")
                    except ApiException as err:
                        if err.reason == "Not Found":
                            self.logger.withFields({"secret": secret_obj.metadata.name, "namespace": ns}).warning(
                                f"Failed to create secret, namespace {ns} doesnt exist"
                            )
                        else:
                            self.logger.withFields({"secret": secret_obj.metadata.name}).exception(
                                "Failed to create secret", exc_info=err
                            )
                        continue
                    except Exception as err:
                        self.logger.withFields({"secret": secret_obj.metadata.name}).exception(
                            "Failed to create secret", exc_info=err
                        )
                        continue
                else:
                    # Compare secret
                    kube_secret_annotations = kube_secret.metadata.annotations or {}
                    changed = False

                    for key, value in secret.annotations.items():
                        if not key.endswith("version"):
                            continue

                        if kube_secret_annotations.get(key) != value:
                            changed = True
                            break

                    if changed:
                        try:
                            self.client.patch_namespaced_secret(
                                name=secret.k8s_secret_name, namespace=ns, body=secret_obj.to_dict()
                            )
                            self.logger.info(f"Updated secret {secret_obj.metadata.name} in namespace {ns}")
                        except Exception as err:
                            self.logger.withFields({"secret": secret_obj.metadata.name}).exception(
                                "Failed to patch secret", exc_info=err
                            )
                            continue
                    else:
                        self.logger.info(f"Skipped updating secret {secret_obj.metadata.name} in namespace {ns}")
