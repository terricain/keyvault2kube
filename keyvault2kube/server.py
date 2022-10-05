import logging
import os
import signal
import sys
import time
from pathlib import Path

import pylogrus

from keyvault2kube.keyvault import KeyVaultManager
from keyvault2kube.kube import KubeSecretManager, load_config

logging.setLoggerClass(pylogrus.PyLogrus)
logger = logging.getLogger("keyvault2kube")


def main():
    if sys.stdout.isatty():
        formatter = pylogrus.TextFormatter(datefmt="Z", colorize=True)
    else:
        enabled_fields = [
            ("asctime", "timestamp"),
            "message",
            ("name", "logger_name"),
            ("levelname", "level"),
            ("exception", "exception_class"),
            ("stacktrace", "stack_trace"),
            ("pathname", "file"),
            ("lineno", "lineno"),
        ]
        formatter = pylogrus.JsonFormatter(datefmt="Z", enabled_fields=enabled_fields)
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    try:
        keyvault_urls = os.environ["KEY_VAULT_URLS"].split(",")
    except KeyError:
        logger.error("Environment variable KEY_VAULT_URLS is required")
        sys.exit(1)

    keyvault_managers = []
    for keyvault_url in keyvault_urls:
        logger.info(f"Creating KeyVault manager for {keyvault_url}")
        keyvault_managers.append(KeyVaultManager(keyvault_url))

    logger.info("Loading Kubernetes config")
    load_config()
    logger.info("Loading Kubernetes manager")
    kube = KubeSecretManager()

    running = True

    def stop_signal_handler(signal_number, frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop_signal_handler)

    while running:
        secrets = []
        for kv_manager in keyvault_managers:
            logger.info(f"Getting secrets from {kv_manager.url}")
            try:
                secrets.extend(kv_manager.get_secrets())
            except Exception as err:
                logger.exception(
                    "Failed to get secrets from keyvault", extra={"keyvault": kv_manager.url}, exc_info=err
                )

        try:
            kube.update_secrets(secrets)
            Path("/tmp/done").touch()
        except Exception as err:
            logger.exception("Failed to update Kubernetes secrets", exc_info=err)

        for _ in range(0, 5 * 60):
            if not running:
                break
            time.sleep(1)

    logger.info("Shutting down")


if __name__ == "__main__":
    main()
