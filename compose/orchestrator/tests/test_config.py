from app.config import Settings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("WAZUH_API_URL", "https://wazuh.manager:55000")
    monkeypatch.setenv("WAZUH_API_USER", "wazuh-wui")
    monkeypatch.setenv("WAZUH_API_PASSWORD", "pw")
    monkeypatch.setenv("INDEXER_URL", "https://wazuh.indexer:9200")
    monkeypatch.setenv("INDEXER_PASSWORD", "ipw")
    monkeypatch.setenv("DEFECTDOJO_URL", "http://nginx:8080")
    monkeypatch.setenv("DD_API_TOKEN", "tok")
    s = Settings()
    assert s.wazuh_api_user == "wazuh-wui"
    assert s.defectdojo_url.endswith(":8080")
    assert s.verify is True  # SECURE default — TLS verification ON


def test_settings_uses_ca_bundle_when_set(monkeypatch):
    monkeypatch.setenv("CA_BUNDLE", "/opt/tizim/certs/root-ca.pem")
    s = Settings()
    assert s.verify == "/opt/tizim/certs/root-ca.pem"
