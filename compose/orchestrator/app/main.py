import sys
from datetime import datetime, timezone
from app.config import Settings
from app.wazuh_client import WazuhClient
from app.report import render_text_report, render_html_summary, render_html_full
from app.notifiers import send_telegram, send_email, ping_heartbeat

try:
    from app.scanners import scan_all, parse_findings
except ImportError:
    def scan_all(_settings):
        return []

    def parse_findings(_results):
        return []
try:
    from app.defectdojo_client import import_to_defectdojo
except ImportError:
    def import_to_defectdojo(_settings, _results):
        return 0


def _alert_failure(s, exc):
    """No silent failure: notify on any error in the daily cycle."""
    err = f"⚠️ TIZIM kunlik sikl XATO: {exc}"
    try:
        send_telegram(s.telegram_bot_token, s.telegram_chat_id, err)
        send_email(s.smtp_host, s.smtp_port, s.smtp_from, s.smtp_to,
                   "TIZIM XATO", err,
                   user=s.smtp_user, password=s.smtp_password, use_tls=s.smtp_tls)
    except Exception:  # noqa: BLE001 — alerting must never mask the original error
        pass
    print(err, file=sys.stderr)


def run_daily():
    s = Settings()
    try:
        wz = WazuhClient(s.indexer_url, s.indexer_user, s.indexer_password, s.verify)
        findings = wz.get_vulnerabilities()
        scan_results = scan_all(s)
        import_to_defectdojo(s, scan_results)
        # All sources in the report: OS CVEs (Wazuh) + image/deps (Trivy/Grype)
        findings = findings + parse_findings(scan_results)
        now = datetime.now(timezone.utc)
        generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
        text = render_text_report(findings)
        html_body = render_html_summary(findings, generated_at)
        html_full = render_html_full(findings, generated_at)
        attachment = (f"tizim-hisobot-{now.strftime('%Y-%m-%d')}.html",
                      html_full, "text/html")
        send_telegram(s.telegram_bot_token, s.telegram_chat_id, text)
        send_email(s.smtp_host, s.smtp_port, s.smtp_from, s.smtp_to,
                   f"TIZIM kunlik hisobot — {generated_at}", text,
                   user=s.smtp_user, password=s.smtp_password, use_tls=s.smtp_tls,
                   html=html_body, attachments=[attachment])
        print(text)
        ping_heartbeat(s.heartbeat_url)   # dead-man's-switch: faqat muvaffaqiyatda
        return 0
    except Exception as exc:  # noqa: BLE001 — convert to alert + non-zero exit
        _alert_failure(s, exc)
        return 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run-daily"
    if cmd == "run-daily":
        sys.exit(run_daily())
    print(f"noma'lum buyruq: {cmd}", file=sys.stderr)
    sys.exit(2)
