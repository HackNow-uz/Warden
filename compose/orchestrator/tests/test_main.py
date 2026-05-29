from unittest.mock import patch
from app import main


@patch("app.main.send_email", return_value=True)
@patch("app.main.send_telegram", return_value=True)
def test_run_daily_sends_report(mock_tg, mock_mail):
    findings = [{"cve": "CVE-1", "severity": "Critical", "package": "openssl", "location": "web-01"}]
    with patch("app.main.WazuhClient") as MC:
        MC.return_value.get_vulnerabilities.return_value = findings
        with patch("app.main.scan_all", return_value=[]):
            with patch("app.main.import_to_defectdojo", return_value=0):
                rc = main.run_daily()
    assert rc == 0
    assert mock_tg.called and mock_mail.called
    sent_text = mock_tg.call_args[0][2]
    assert "CVE-1" in sent_text


@patch("app.main.send_email", return_value=True)
@patch("app.main.send_telegram", return_value=True)
def test_run_daily_alerts_on_failure(mock_tg, mock_mail):
    """No silent failure: an exception during the cycle must trigger an alert + rc=1."""
    with patch("app.main.WazuhClient") as MC:
        MC.return_value.get_vulnerabilities.side_effect = RuntimeError("indexer down")
        rc = main.run_daily()
    assert rc == 1
    assert mock_tg.called
    assert "XATO" in mock_tg.call_args[0][2]
