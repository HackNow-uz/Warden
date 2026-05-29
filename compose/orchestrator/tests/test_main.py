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
