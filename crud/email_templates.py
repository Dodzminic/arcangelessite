"""
crud/email_templates.py  (NEW FILE)
Designed HTML emails for GLI. Uses inline CSS + tables so it looks right in Gmail/Outlook/phones.
(Email apps do not run animations or scripts, so these are static designs.)
"""
import os
from datetime import datetime
from html import escape

from django.conf import settings
from django.utils import timezone

FONT = "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


# ───────── logo (embedded inside the email if found in your static folder) ─────────
def _logo_inline():
    base = str(getattr(settings, 'BASE_DIR', '.'))
    for p in (os.path.join(base, 'static', 'glilogo.jpg'),
              os.path.join(base, 'crud', 'static', 'glilogo.jpg')):
        if os.path.exists(p):
            with open(p, 'rb') as f:
                return [('gli_logo', f.read(), 'jpeg')]
    return []


def _when():
    return timezone.localtime().strftime('%b %d, %Y · %I:%M %p')


# ───────── shared layout ─────────
def _layout(preheader, icon, title, subtitle, body, has_logo, accent="#3d7fff"):
    logo = ('<img src="cid:gli_logo" width="46" height="46" alt="GLI" '
            'style="display:block;border-radius:12px;border:2px solid rgba(255,255,255,0.25);">') if has_logo else ''
    logo_cell = f'<td width="58" valign="middle">{logo}</td>' if has_logo else ''
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"><title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background-color:#060d1a;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#060d1a;">{escape(preheader)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" bgcolor="#060d1a" style="background-color:#060d1a;">
<tr><td align="center" style="padding:28px 12px;">

  <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:600px;border-radius:20px;overflow:hidden;background-color:#ffffff;box-shadow:0 20px 60px rgba(0,0,0,0.5);">

    <!-- HEADER -->
    <tr><td bgcolor="#0d2356" style="background-color:#0d2356;background-image:linear-gradient(135deg,#050f28 0%,#0d2356 45%,#2558c0 100%);padding:26px 30px 22px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr>
        {logo_cell}
        <td valign="middle" style="font-family:{FONT};">
          <div style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">GLI<span style="color:#7fb3ff;font-style:italic;">Const</span><span style="color:#3d7fff;">.</span></div>
          <div style="font-size:10px;letter-spacing:2.5px;color:#a0c4ff;text-transform:uppercase;margin-top:3px;">Secure Access System</div>
        </td>
        <td align="right" valign="middle" style="font-size:30px;line-height:1;">{icon}</td>
      </tr></table>
    </td></tr>
    <tr><td height="4" style="height:4px;line-height:4px;font-size:0;background-color:{accent};background-image:linear-gradient(90deg,#3d7fff,#10b981,#a78bfa);">&nbsp;</td></tr>

    <!-- TITLE -->
    <tr><td style="padding:32px 34px 6px;font-family:{FONT};">
      <div style="font-size:24px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;line-height:1.25;">{title}</div>
      <div style="font-size:14px;color:#64748b;margin-top:8px;line-height:1.6;">{subtitle}</div>
    </td></tr>

    <!-- BODY -->
    <tr><td style="padding:18px 34px 30px;font-family:{FONT};">{body}</td></tr>

    <!-- FOOTER -->
    <tr><td bgcolor="#f1f5ff" style="background-color:#f1f5ff;padding:20px 34px;font-family:{FONT};border-top:1px solid #e2e8f5;">
      <div style="font-size:11px;color:#64748b;line-height:1.7;">
        🔒 This message was generated automatically by the <b style="color:#1a4494;">GLI Construction Services</b> secure access system.
        Never share your codes with anyone.<br>
        <span style="color:#94a3b8;">Sent {escape(_when())}</span>
      </div>
    </td></tr>

  </table>

  <div style="font-family:{FONT};font-size:10px;color:#4a5e80;margin-top:16px;letter-spacing:1px;">GLI CONSTRUCTION SERVICES · ONE TEAM. ONE MISSION.</div>

</td></tr></table>
</body></html>"""


def _button(label, url, color="#2255cc"):
    return f"""<table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:26px auto 4px;"><tr>
<td align="center" bgcolor="{color}" style="border-radius:12px;background-color:{color};background-image:linear-gradient(135deg,#1a4494,#3d7fff);">
<a href="{escape(url)}" style="display:inline-block;padding:15px 38px;font-family:{FONT};font-size:14px;font-weight:800;letter-spacing:1.5px;color:#ffffff;text-decoration:none;border-radius:12px;">{label}</a>
</td></tr></table>"""


def _notice(text, color="#b45309", bg="#fffbeb", border="#fde68a", icon="⚠️"):
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top:22px;"><tr>'
            f'<td style="background-color:{bg};border:1px solid {border};border-radius:12px;padding:12px 16px;font-family:{FONT};font-size:12px;color:{color};line-height:1.6;">'
            f'{icon}&nbsp; {text}</td></tr></table>')


# ───────── 1) one-time code (register + panel unlock) ─────────
def code_email(kind, code, minutes, who=None, ip=None):
    if kind == 'panel':
        icon, title = "🔐", "Admin panel unlock code"
        subtitle = (f"<b>{escape(who or 'An administrator')}</b> is trying to open the "
                    "<b>Admin Approvals</b> panel. Use this code to unlock it.")
    else:
        icon, title = "🛡️", "Your one-time code"
        subtitle = "Someone started a <b>new administrator registration</b>. Give this code only to the person you are expecting."

    boxes = ""
    for i, ch in enumerate(str(code)):
        if i:
            boxes += '<td width="8" style="width:8px;font-size:0;">&nbsp;</td>'
        boxes += (f'<td align="center" width="48" height="62" bgcolor="#f1f5ff" '
                  f'style="width:48px;height:62px;background-color:#f1f5ff;border:2px solid #c7d6fb;border-radius:12px;'
                  f'font-family:Consolas,\'Courier New\',monospace;font-size:32px;font-weight:800;color:#1a4494;">{escape(ch)}</td>')
    meta = f"Valid for <b>{minutes} minutes</b> · single use"
    if ip:
        meta += f" · requested from <b>{escape(str(ip))}</b>"
    body = f"""
<table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:10px auto 0;"><tr>{boxes}</tr></table>
<div style="text-align:center;font-family:{FONT};font-size:12px;color:#64748b;margin-top:16px;">⏱️&nbsp; {meta}</div>
{_notice("If you did <b>not</b> expect this, ignore this email — nothing happens unless the code is entered.", icon="⚠️")}"""
    logo = _logo_inline()
    return _layout(f"Your code is {code}", icon, title, subtitle, body, bool(logo)), logo


# ───────── 2) approval request (shows the applicant's face) ─────────
def approval_email(req, link, photo_jpeg):
    rows = [("Full name", req.full_name), ("Employee ID", req.employee_id), ("Age", req.age),
            ("Location", req.location), ("Email", req.email), ("Username", req.username)]
    trs = ""
    for i, (k, v) in enumerate(rows):
        bg = "#f8faff" if i % 2 == 0 else "#ffffff"
        trs += (f'<tr><td style="background-color:{bg};padding:11px 16px;font-family:{FONT};font-size:11px;font-weight:700;letter-spacing:1px;'
                f'color:#64748b;text-transform:uppercase;width:130px;">{k}</td>'
                f'<td style="background-color:{bg};padding:11px 16px;font-family:{FONT};font-size:14px;font-weight:600;color:#0f172a;">{escape(str(v))}</td></tr>')

    photo = ""
    imgs = _logo_inline()
    if photo_jpeg:
        imgs.append(('applicant_face', photo_jpeg, 'jpeg'))
        photo = f"""<table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin:6px auto 18px;"><tr><td align="center">
<img src="cid:applicant_face" width="240" alt="Applicant face" style="display:block;width:240px;max-width:100%;border-radius:16px;border:3px solid #3d7fff;">
<div style="font-family:{FONT};font-size:10px;letter-spacing:2px;color:#64748b;margin-top:8px;">APPLICANT FACE SCAN</div>
</td></tr></table>"""
    body = f"""{photo}
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #e2e8f5;border-radius:14px;overflow:hidden;">{trs}</table>
{_button("REVIEW REQUEST &nbsp;→", link)}
{_notice("To approve or reject, log in as <b>superuser</b> and enter the emailed unlock code. Only approve people you recognize.", icon="🔒")}"""
    return (_layout(f"{req.full_name} is waiting for approval", "📝", "New administrator request",
                    f"<b>{escape(req.full_name)}</b> registered and is waiting for your approval. Compare the face and details below.",
                    body, bool(_logo_inline())), imgs)


# ───────── 3) result (approved / declined) ─────────
def result_email(name, approved, login_url):
    logo = _logo_inline()
    if approved:
        body = f"""<div style="text-align:center;font-size:54px;line-height:1.2;margin-top:6px;">✅</div>
<div style="font-family:{FONT};font-size:14px;color:#334155;line-height:1.7;text-align:center;margin-top:8px;">
Your administrator account is now <b style="color:#059669;">active</b>.<br>You can log in with your <b>password</b> or <b>Face ID</b>.</div>
{_button("GO TO LOGIN &nbsp;→", login_url, "#047857")}"""
        html = _layout("Your admin account was approved", "🎉", "You're approved!",
                       f"Hi <b>{escape(name)}</b>, welcome to the GLI team portal.", body, bool(logo))
    else:
        body = f"""<div style="text-align:center;font-size:54px;line-height:1.2;margin-top:6px;">❌</div>
<div style="font-family:{FONT};font-size:14px;color:#334155;line-height:1.7;text-align:center;margin-top:8px;">
Your administrator registration was <b style="color:#dc2626;">not approved</b>.<br>If you think this is a mistake, please contact the approvers directly.</div>"""
        html = _layout("Your admin request was declined", "📋", "Request declined",
                       f"Hi <b>{escape(name)}</b>, we have an update on your registration.", body, bool(logo), accent="#ef4444")
    return html, logo
