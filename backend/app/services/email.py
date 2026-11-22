"""Pluggable email sender with console (dev) and SMTP (prod) backends.

Templates are bilingual (EN/AR) and rendered with simple string formatting.
No external templating dependency is required.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from app.config import settings

log = logging.getLogger("teledesk.email")


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, text_body: str, html_body: str) -> None: ...  # noqa: E701


class ConsoleEmailSender:
    """Dev backend: writes emails to stdout instead of sending."""

    async def send(self, to: str, subject: str, text_body: str, html_body: str) -> None:
        print("=" * 60)
        print(f"EMAIL TO: {to}")
        print(f"SUBJECT: {subject}")
        print("-" * 60)
        print(text_body)
        print("=" * 60)


class SmtpEmailSender:
    """Production SMTP backend."""

    def __init__(self, host: str, port: int, username: str, password: str, from_email: str, use_tls: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.use_tls = use_tls

    async def send(self, to: str, subject: str, text_body: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)


def get_email_sender() -> EmailSender:
    if settings.APP_ENV == "development":
        return ConsoleEmailSender()
    return SmtpEmailSender(
        host=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        from_email=settings.SMTP_FROM_EMAIL,
        use_tls=settings.SMTP_USE_TLS,
    )


# ---------------------------------------------------------------------------
# Templates (EN/AR)
# ---------------------------------------------------------------------------

def _verify_email_text(name: str, code: str, base_url: str, lang: str) -> str:
    if lang == "ar":
        return f"""أهلاً {name},

رمز التحقق من بريدك الإلكتروني هو: {code}

إذا لم تطلب هذا التجاهل هذه الرسالة.

تحياتي,
فريق TeleDesk"""
    return f"""Hi {name},

Your email verification code is: {code}

If you didn't request this, ignore this message.

Regards,
The TeleDesk team"""


def _verify_email_html(name: str, code: str, base_url: str, lang: str) -> str:
    if lang == "ar":
        return f"""<p>أهلاً <b>{name}</b>,</p><p>رمز التحقق من بريدك الإلكتروني هو: <b>{code}</b></p><p>إذا لم تطلب هذا التجاهل هذه الرسالة.</p>"""
    return f"""<p>Hi <b>{name}</b>,</p><p>Your email verification code is: <b>{code}</b></p><p>If you didn't request this, ignore this message.</p>"""


def verify_email_template(name: str, code: str, base_url: str, lang: str = "en") -> tuple[str, str, str]:
    subject = "تأكيد البريد الإلكتروني" if lang == "ar" else "Verify your email"
    return subject, _verify_email_text(name, code, base_url, lang), _verify_email_html(name, code, base_url, lang)


def _reset_password_text(name: str, code: str, lang: str) -> str:
    if lang == "ar":
        return f"""أهلاً {name},

رمز إعادة تعيين كلمة المرور هو: {code}

الرمز صالح لمدة 15 دقيقة.

تحياتي,
فريق TeleDesk"""
    return f"""Hi {name},

Your password reset code is: {code}

The code is valid for 15 minutes.

Regards,
The TeleDesk team"""


def _reset_password_html(name: str, code: str, lang: str) -> str:
    if lang == "ar":
        return f"""<p>أهلاً <b>{name}</b>,</p><p>رمز إعادة تعيين كلمة المرور هو: <b>{code}</b></p><p>الرمز صالح لمدة 15 دقيقة.</p>"""
    return f"""<p>Hi <b>{name}</b>,</p><p>Your password reset code is: <b>{code}</b></p><p>The code is valid for 15 minutes.</p>"""


def reset_password_template(name: str, code: str, lang: str = "en") -> tuple[str, str, str]:
    subject = "إعادة تعيين كلمة المرور" if lang == "ar" else "Reset your password"
    return subject, _reset_password_text(name, code, lang), _reset_password_html(name, code, lang)


def welcome_template(name: str, lang: str = "en") -> tuple[str, str, str]:
    subject = "أهلاً بك في TeleDesk" if lang == "ar" else "Welcome to TeleDesk"
    if lang == "ar":
        text = f"""أهلاً {name},

أهلاً بك في TeleDesk، صندوق الوارد المدعوم بالذكاء الاصطناعي لدعم العملاء.

ابدأ بتوصيل قناتك ورفع قاعدة معرفتك.

تحياتي,
فريق TeleDesk"""
        html = f"""<p>أهلاً <b>{name}</b>,</p><p>أهلاً بك في TeleDesk، صندوق الوارد المدعوم بالذكاء الاصطناعي لدعم العملاء.</p><p>ابدأ بتوصيل قناتك ورفع قاعدة معرفتك.</p>"""
    else:
        text = f"""Hi {name},

Welcome to TeleDesk, the AI-powered inbox for customer support.

Start by connecting a channel and uploading your knowledge base.

Regards,
The TeleDesk team"""
        html = f"""<p>Hi <b>{name}</b>,</p><p>Welcome to TeleDesk, the AI-powered inbox for customer support.</p><p>Start by connecting a channel and uploading your knowledge base.</p>"""
    return subject, text, html


def _normalize_lang(lang: str | None) -> str:
    return "ar" if (lang or "en").startswith("ar") else "en"


def invitation_email_template(inviter_name: str, invitee_email: str, token: str, base_url: str, lang: str = "en") -> tuple[str, str, str]:
    accept_url = f"{base_url.rstrip('/')}/auth/accept-invitation?token={token}"
    if lang == "ar":
        subject = "دعوة للانضمام إلى فريق TeleDesk"
        text = f"""أهلاً،

دُعيت من قبل {inviter_name} للانضمام إلى فريقه على TeleDesk.

اضغط على الرابط التالي لقبول الدعوة وإنشاء حسابك:
{accept_url}

الرابط صالح لمدة 7 أيام.

تحياتي,
فريق TeleDesk"""
        html = f"""<p>أهلاً،</p><p>دُعيت من قبل <b>{inviter_name}</b> للانضمام إلى فريقه على TeleDesk.</p><p>اضغط على الرابط التالي لقبول الدعوة وإنشاء حسابك:</p><p><a href="{accept_url}">{accept_url}</a></p><p>الرابط صالح لمدة 7 أيام.</p><p>تحياتي,<br>فريق TeleDesk</p>"""
    else:
        subject = "Invitation to join TeleDesk team"
        text = f"""Hi,

You've been invited by {inviter_name} to join their team on TeleDesk.

Click the link below to accept the invitation and create your account:
{accept_url}

The link is valid for 7 days.

Regards,
The TeleDesk team"""
        html = f"""<p>Hi,</p><p>You've been invited by <b>{inviter_name}</b> to join their team on TeleDesk.</p><p>Click the link below to accept the invitation and create your account:</p><p><a href="{accept_url}">{accept_url}</a></p><p>The link is valid for 7 days.</p><p>Regards,<br>The TeleDesk team</p>"""
    return subject, text, html
