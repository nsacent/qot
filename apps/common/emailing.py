from html import escape

from django.conf import settings


def build_branded_email_html(
    *,
    title,
    message,
    action_url="",
    action_label="Open QOT",
):
    """Return an email-client-safe QOT transactional email body."""
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    avatar_url = getattr(
        settings,
        "EMAIL_BRAND_IMAGE_URL",
        f"{frontend_url}/qot-info-avatar.png",
    )
    message_markup = escape(str(message)).replace("\n", "<br>")
    action_markup = ""

    if action_url:
        action_markup = f"""
          <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:24px 0 4px">
            <tr>
              <td bgcolor="#f97316" style="border-radius:12px">
                <a href="{escape(str(action_url), quote=True)}" style="display:inline-block;color:#ffffff;text-decoration:none;font-size:14px;font-weight:800;padding:13px 20px">
                  {escape(str(action_label))}
                </a>
              </td>
            </tr>
          </table>
        """

    return f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background:#fff7f2;font-family:Arial,Helvetica,sans-serif;color:#0f172a">
    <div role="article" aria-label="{escape(str(title), quote=True)}" style="background:#fff7f2;padding:28px 14px">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff;border:1px solid #fed7aa;border-radius:20px;overflow:hidden">
              <tr>
                <td style="padding:18px 24px;background:#0f172a">
                  <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                      <td style="padding-right:13px">
                        <img src="{escape(str(avatar_url), quote=True)}" width="54" height="54" alt="QOT Uganda" style="display:block;width:54px;height:54px;border:0;border-radius:50%" />
                      </td>
                      <td>
                        <div style="color:#ffffff;font-size:20px;font-weight:900;line-height:1.2">QOT Uganda</div>
                        <div style="margin-top:3px;color:#fdba74;font-size:11px;font-weight:700;letter-spacing:1.2px">BUY &amp; SELL FOR FREE</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:28px 24px">
                  <h1 style="margin:0;color:#0f172a;font-size:22px;line-height:1.35">{escape(str(title))}</h1>
                  <p style="margin:14px 0 0;color:#475569;font-size:15px;line-height:1.7">{message_markup}</p>
                  {action_markup}
                </td>
              </tr>
              <tr>
                <td style="padding:16px 24px;background:#f8fafc;color:#64748b;font-size:12px;line-height:1.6">
                  QOT Uganda &middot; <a href="mailto:info@qot.ug" style="color:#475569;text-decoration:none">info@qot.ug</a> &middot; 0200911678
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </div>
  </body>
</html>"""
