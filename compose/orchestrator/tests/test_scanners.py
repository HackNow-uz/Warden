import json
from unittest.mock import patch, MagicMock
from app.scanners import run_trivy_image, run_grype, parse_findings

TRIVY_JSON = json.dumps({"Results": [{"Vulnerabilities": [
    {"VulnerabilityID": "CVE-X", "Severity": "HIGH", "PkgName": "openssl"}]}]})
GRYPE_JSON = json.dumps({"matches": [
    {"vulnerability": {"id": "CVE-Y", "severity": "Critical"},
     "artifact": {"name": "nginx"}}]})


@patch("app.scanners.subprocess.run")
def test_run_trivy_image_returns_raw_json(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=TRIVY_JSON, stderr="")
    out = run_trivy_image("nginx:1.27")
    assert out["scan_type"] == "Trivy Scan"
    assert out["target"] == "nginx:1.27"
    assert json.loads(out["raw"])["Results"][0]["Vulnerabilities"][0]["VulnerabilityID"] == "CVE-X"


@patch("app.scanners.subprocess.run")
def test_run_grype_returns_anchore_type(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout='{"matches":[]}', stderr="")
    out = run_grype("nginx:1.27")
    assert out["scan_type"] == "Anchore Grype"


def test_parse_findings_handles_trivy_and_grype():
    results = [
        {"scan_type": "Trivy Scan", "target": "nginx:1.27", "raw": TRIVY_JSON},
        {"scan_type": "Anchore Grype", "target": "nginx:1.27", "raw": GRYPE_JSON},
    ]
    findings = parse_findings(results)
    assert {"cve": "CVE-X", "severity": "High", "package": "openssl",
            "location": "nginx:1.27"} in findings
    assert {"cve": "CVE-Y", "severity": "Critical", "package": "nginx",
            "location": "nginx:1.27"} in findings
    assert len(findings) == 2


def test_parse_findings_skips_bad_json():
    assert parse_findings([{"scan_type": "Trivy Scan", "target": "x", "raw": "not json"}]) == []
