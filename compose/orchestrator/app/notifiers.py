import smtplib
from email.message import EmailMessage
import requests


def send_telegram(bot_token, chat_id, text):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    return r.status_code == 200


def ping_heartbeat(url):
    """Dead-man's-switch ping (healthchecks.io kabi). Bo'sh URL => no-op."""
    if not url:
        return False
    try:
        requests.get(url, timeout=10)
        return True
    except Exception:  # noqa: BLE001 — heartbeat hech qachon asosiy oqimni buzmasin
        return False


def send_email(host, port, sender, to, subject, body,
               user=None, password=None, use_tls=False, html=None, attachments=None):
    # Parolni cleartext kanalda yubormaslik: auth faqat TLS bilan
    if (user or password) and not use_tls:
        raise ValueError("SMTP autentifikatsiyasi use_tls=True talab qiladi")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)                       # text/plain fallback
    if html:
        msg.add_alternative(html, subtype="html")
    for fname, content, mime in (attachments or []):
        maintype, _, subtype = mime.partition("/")
        data = content.encode() if isinstance(content, str) else content
        msg.add_attachment(data, maintype=maintype, subtype=subtype or "octet-stream",
                           filename=fname)
    with smtplib.SMTP(host, port, timeout=30) as s:
        if use_tls:
            s.starttls()
        if user and password:
            s.login(user, password)
        s.send_message(msg)
    return True
