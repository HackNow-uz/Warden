import requests


class WazuhClient:
    """Queries the Wazuh indexer vulnerability-states index (4.8+ CTI engine).

    `verify` is a requests TLS-verify value: True (system trust), or a path to a
    CA bundle (the Wazuh-generated root-ca.pem). TLS verification is NEVER disabled.
    """

    def __init__(self, indexer_url, user, password, verify=True):
        self.url = indexer_url.rstrip("/")
        self.auth = (user, password)
        self.verify = verify

    def get_vulnerabilities(self, size=2000):
        body = {"size": size, "query": {"match_all": {}}}
        r = requests.get(
            f"{self.url}/wazuh-states-vulnerabilities-*/_search",
            json=body, auth=self.auth, verify=self.verify, timeout=30,
        )
        r.raise_for_status()
        out = []
        for hit in r.json().get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            vuln = src.get("vulnerability", {})
            out.append({
                "cve": vuln.get("id", ""),
                "severity": vuln.get("severity", "Low"),
                "package": src.get("package", {}).get("name", ""),
                "location": src.get("agent", {}).get("name", ""),
            })
        return out
