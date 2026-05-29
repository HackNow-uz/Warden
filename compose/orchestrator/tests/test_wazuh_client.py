from unittest.mock import patch, MagicMock
from app.wazuh_client import WazuhClient

SAMPLE_HITS = {"hits": {"hits": [
    {"_source": {"vulnerability": {"id": "CVE-2025-1", "severity": "Critical"},
                 "package": {"name": "openssl"}, "agent": {"name": "web-01"}}},
    {"_source": {"vulnerability": {"id": "CVE-2025-2", "severity": "High"},
                 "package": {"name": "nginx"}, "agent": {"name": "web-02"}}},
]}}


@patch("app.wazuh_client.requests.get")
def test_get_vulnerabilities_maps_findings(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: SAMPLE_HITS)
    c = WazuhClient("https://idx:9200", "admin", "pw", verify=True)
    out = c.get_vulnerabilities()
    assert out[0]["cve"] == "CVE-2025-1"
    assert out[0]["severity"] == "Critical"
    assert out[0]["package"] == "openssl"
    assert out[0]["location"] == "web-01"
    assert out[0]["source"] == "Wazuh"
    assert len(out) == 2
