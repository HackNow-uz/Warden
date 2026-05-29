import json
from unittest.mock import patch, MagicMock
from app.scanners import run_trivy_image, run_grype

TRIVY_JSON = json.dumps({"Results": [{"Vulnerabilities": [
    {"VulnerabilityID": "CVE-X", "Severity": "HIGH", "PkgName": "openssl"}]}]})


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
