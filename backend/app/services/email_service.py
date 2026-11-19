"""
Outgoing email for account provisioning.

The only message this module sends today is the "your account is ready"
notice, triggered by POST /api/v1/users. Keeping it in a service means the
router does not care whether delivery uses Gmail SMTP, a relay, or the
console in a test run.

Configuration lives in `app.config.Settings` and is read from `.env`:
    MAIL_USERNAME / MAIL_PASSWORD  (Gmail App Password, not the login one)
    MAIL_FROM / MAIL_SERVER / MAIL_PORT

Two failure modes are deliberately separated:

* `EmailNotConfiguredError` - no real credentials yet. The caller should
  report "created but not sent" instead of pretending it worked.
* `EmailDeliveryError` - SMTP rejected us or the network failed. Same
  user-facing outcome, but the cause is logged so a demo is debuggable.

The account itself is always created first. A bounced email must never roll
back a user row.
"""

import html
import logging

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings

logger = logging.getLogger(__name__)

SUBJECT = "FreshChain - Thông tin tài khoản của bạn"

# Sending with a placeholder address would authenticate against Gmail with
# fake credentials and fail after a timeout, which looks like a bug during a
# demo. `settings.mail_configured` already filters the documented
# placeholders, so this constant only documents the intent.
_GREETING_FALLBACK = "bạn"


class EmailNotConfiguredError(RuntimeError):
    """SMTP credentials are missing or still set to placeholder values."""


class EmailDeliveryError(RuntimeError):
    """The SMTP server refused the message or the connection failed."""


def _connection_config() -> ConnectionConfig:
    """Build the fastapi-mail config from settings (raises when unset)."""
    if not settings.mail_configured:
        raise EmailNotConfiguredError(
            "MAIL_USERNAME / MAIL_PASSWORD chưa được cấu hình trong .env"
        )

    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.mail_from_address,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
        VALIDATE_CERTS=True,
        TIMEOUT=settings.MAIL_TIMEOUT,
        SUPPRESS_SEND=settings.MAIL_SUPPRESS_SEND,
    )


def render_account_info(full_name: str, username: str, password: str) -> tuple[str, str]:
    """
    Return (plain_text, html_body) for the account notice.

    Both bodies carry the same facts so a mail client without HTML still
    shows a readable message. Values are escaped before being placed in the
    HTML part: the name comes from an admin form, not from us.
    """
    display_name = (full_name or "").strip() or _GREETING_FALLBACK

    plain = (
        f"Chào {display_name},\n"
        "\n"
        "Tài khoản của bạn trên hệ thống FreshChain đã được tạo.\n"
        "\n"
        f"Tên đăng nhập: {username}\n"
        f"Mật khẩu: {password}\n"
        "\n"
        "Vui lòng đăng nhập và đổi mật khẩu ngay sau lần đăng nhập đầu tiên.\n"
        "\n"
        "Trân trọng,\n"
        "FreshChain - Nền tảng quản trị chuỗi cung ứng chống lãng phí thực phẩm\n"
    )

    safe_name = html.escape(display_name)
    safe_username = html.escape(username)
    safe_password = html.escape(password)

    body = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#1e293b;line-height:1.6">
  <p>Chào <strong>{safe_name}</strong>,</p>
  <p>Tài khoản của bạn trên hệ thống <strong>FreshChain</strong> đã được tạo.</p>
  <table style="border-collapse:collapse;margin:16px 0">
    <tr>
      <td style="padding:6px 14px 6px 0;color:#64748b">Tên đăng nhập</td>
      <td style="padding:6px 0"><strong>{safe_username}</strong></td>
    </tr>
    <tr>
      <td style="padding:6px 14px 6px 0;color:#64748b">Mật khẩu</td>
      <td style="padding:6px 0"><strong>{safe_password}</strong></td>
    </tr>
  </table>
  <p>Vui lòng đăng nhập và đổi mật khẩu ngay sau lần đăng nhập đầu tiên.</p>
  <p style="color:#64748b;font-size:13px;margin-top:24px">
    Trân trọng,<br>
    FreshChain - Nền tảng quản trị chuỗi cung ứng chống lãng phí thực phẩm
  </p>
</div>
"""
    return plain, body


async def send_account_info_email(
    to_email: str,
    username: str,
    password: str,
    full_name: str,
) -> None:
    """
    Send the new-account notice to `to_email`.

    Raises `EmailNotConfiguredError` when SMTP is not set up and
    `EmailDeliveryError` when sending fails, so the router can tell the two
    apart in its response without parsing exception text.
    """
    config = _connection_config()
    plain, body = render_account_info(full_name, username, password)

    message = MessageSchema(
        subject=SUBJECT,
        recipients=[to_email],
        body=body,
        alternative_body=plain,
        subtype=MessageType.html,
    )

    try:
        await FastMail(config).send_message(message)
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain error
        logger.warning("Could not send account email to %s: %s", to_email, exc)
        raise EmailDeliveryError(str(exc)) from exc

    logger.info("Account email sent to %s", to_email)


__all__ = [
    "EmailDeliveryError",
    "EmailNotConfiguredError",
    "render_account_info",
    "send_account_info_email",
]
