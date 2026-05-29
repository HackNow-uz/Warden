import smtplib
from email.message import EmailMessage
import requests


def send_telegram(bot_token, chat_id, text):
    if not bot_token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    return r.status_code == 200


def send_email(host, port, sender, to, subject, body,
               user=None, password=None, use_tls=False):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=30) as s:
        if use_tls:
            s.starttls()
        if user and password:
            s.login(user, password)
        s.send_message(msg)
    return True
