import sys
from app.config import Settings
from app.wazuh_client import WazuhClient
from app.report import render_text_report
from app.notifiers import send_telegram, send_email

# Phase 4 fills these in (scanners.py / defectdojo_client.py)
try:
    from app.scanners import scan_all
except ImportError:
    def scan_all(_settings):
        return []
try:
    from app.defectdojo_client import import_to_defectdojo
except ImportError:
    def import_to_defectdojo(_settings, _results):
        return 0


def run_daily():
    s = Settings()
    wz = WazuhClient(s.indexer_url, s.indexer_user, s.indexer_password, s.verify)
    findings = wz.get_vulnerabilities()
    scan_results = scan_all(s)
    import_to_defectdojo(s, scan_results)
    text = render_text_report(findings)
    send_telegram(s.telegram_bot_token, s.telegram_chat_id, text)
    send_email(s.smtp_host, s.smtp_port, s.smtp_from, s.smtp_to,
               "TIZIM kunlik hisobot", text)
    print(text)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run-daily"
    if cmd == "run-daily":
        sys.exit(run_daily())
    print(f"noma'lum buyruq: {cmd}", file=sys.stderr)
    sys.exit(2)
