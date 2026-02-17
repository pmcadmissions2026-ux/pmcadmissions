from email.message import EmailMessage
import smtplib
from flask import current_app


def send_email_smtp(subject: str, body: str, to_email: str, from_name: str = None, reply_to: str = None, html_body: str = None) -> bool:
    """Send an email via SMTP using app config.

    Supports both plain-text `body` and optional `html_body` (HTML alternative).
    Returns True on success, False on failure (and logs exceptions).
    """
    cfg = current_app.config
    host = cfg.get('SMTP_HOST')
    port = cfg.get('SMTP_PORT', 587)
    user = cfg.get('SMTP_USER')
    password = cfg.get('SMTP_PASS')
    use_tls = str(cfg.get('SMTP_USE_TLS', 'True')).lower() in ('true', '1', 'yes')

    if not host or not user or not password:
        current_app.logger.warning('SMTP not configured (SMTP_HOST/SMTP_USER/SMTP_PASS missing)')
        return False

    msg = EmailMessage()
    from_addr = f"{from_name} <{user}>" if from_name else user
    msg['From'] = from_addr
    msg['To'] = to_email
    msg['Subject'] = subject
    if reply_to:
        msg['Reply-To'] = reply_to

    # Set plain-text body and optional HTML alternative
    msg.set_content(body)
    if html_body:
        try:
            msg.add_alternative(html_body, subtype='html')
        except Exception:
            current_app.logger.exception('Failed to attach HTML alternative to email')

    try:
        with smtplib.SMTP(host, port, timeout=20) as s:
            if use_tls:
                s.starttls()
            s.login(user, password)
            s.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception('SMTP send failed')
        return False
