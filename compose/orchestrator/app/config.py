from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    wazuh_api_url: str = "https://wazuh.manager:55000"
    wazuh_api_user: str = "wazuh-wui"
    wazuh_api_password: str = ""
    indexer_url: str = "https://wazuh.indexer:9200"
    indexer_user: str = "admin"
    indexer_password: str = ""

    defectdojo_url: str = "http://nginx:8080"
    dd_api_token: str = ""
    dd_product_id: int = 1

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_from: str = "tizim@local"
    smtp_to: str = "secops@local"
    smtp_user: str = ""        # bo'sh => auth yo'q (mailhog)
    smtp_password: str = ""
    smtp_tls: bool = False     # gmail/relay uchun true

    # TLS: do NOT disable verification. For Wazuh self-signed certs, mount the
    # generated root CA and point CA_BUNDLE at it. Empty => use system trust store.
    ca_bundle: str = ""

    @property
    def verify(self):
        """requests `verify` value: CA path if provided, else True (verify ON)."""
        return self.ca_bundle or True
