import requests
from flask import current_app


def send_email_sendgrid(subject: str, body: str, to_email: str, from_email: str = None, from_name: str = None, reply_to: str = None, html_body: str = None) -> bool:
    """Send email via SendGrid v3 API. Returns True on success, False otherwise.

    Accepts optional `html_body` to send HTML content alongside plain text.
    """
    api_key = current_app.config.get('SENDGRID_API_KEY')
    if not api_key:
        current_app.logger.warning('SendGrid API key not configured')
        return False

    from_email = from_email or current_app.config.get('SENDGRID_FROM_EMAIL')
    from_name = from_name or current_app.config.get('SENDGRID_FROM_NAME') or ''
    if not from_email:
        current_app.logger.warning('SendGrid from email not configured')
        return False

    payload = {
        "personalizations": [
            {"to": [{"email": to_email}]}
        ],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body}]
    }
    if html_body:
        payload['content'].append({"type": "text/html", "value": html_body})
    if reply_to:
        payload['reply_to'] = {"email": reply_to}

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        resp = requests.post('https://api.sendgrid.com/v3/mail/send', json=payload, headers=headers, timeout=10)
        if resp.status_code in (200, 202):
            return True
        current_app.logger.warning('SendGrid send failed: %s %s', resp.status_code, resp.text)
        return False
    except Exception:
        current_app.logger.exception('SendGrid send exception')
        return False
