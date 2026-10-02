"""
crud/admin_registration.py
Flow: request code (emailed to both approvers) -> enter code -> fill form + face scan
      -> saved as PENDING (with face photo) -> approvers get an email -> approve = real admin account.
Also holds the shared helpers used by the Admin Approvals panel (panel_required, decide_request).
"""
import base64
import email.message
import email.policy
import json
import re
import secrets
from datetime import timedelta
from email.utils import formatdate, make_msgid
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.mail.utils import DNS_NAME
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import salted_hmac, constant_time_compare

from . import email_templates as et
from .facial_verification import parse_descriptor, find_matching_face
from .models import ActivityLog, AdminOTP, AdminRegistrationRequest, AdminFace

MAX_CODE_ATTEMPTS = 5
FORM_WINDOW_MINUTES = 15
PANEL_UNLOCK_MINUTES = 30
USERNAME_RE = re.compile(r'^[A-Za-z0-9_.-]{4,30}$')


# ─────────── helpers ───────────
def _hash_code(code):
    return salted_hmac('gli-admin-otp', code).hexdigest()


class _SmtpMsg(email.message.EmailMessage):
    """Accepts the old `linesep=` argument too, so it works on every Django version."""
    def as_bytes(self, unixfrom=False, policy=None, linesep=None):
        policy = policy or self.policy
        if linesep:
            policy = policy.clone(linesep=linesep)
        return super().as_bytes(unixfrom=unixfrom, policy=policy)


class _GliMail(EmailMultiAlternatives):
    """Builds the email itself (text + designed HTML + embedded cid: images + attachments)."""

    def __init__(self, subject, body, to, html=None, inline_images=None, attachments=None):
        super().__init__(subject, body, settings.DEFAULT_FROM_EMAIL, to)
        if html:
            self.attach_alternative(html, "text/html")
        self._inline = list(inline_images or [])
        self._files = list(attachments or [])

    def message(self, *args, **kwargs):
        m = _SmtpMsg(policy=email.policy.SMTP)
        m['Subject'] = self.subject
        m['From'] = self.from_email
        m['To'] = ', '.join(self.to)
        m['Date'] = formatdate(localtime=True)
        m['Message-ID'] = make_msgid(domain=str(DNS_NAME))
        m.set_content(self.body)
        if self.alternatives:
            m.add_alternative(self.alternatives[0][0], subtype='html')
            html_part = m.get_payload()[-1]
            for cid, data, subtype in self._inline:
                html_part.add_related(data, 'image', subtype, cid=f'<{cid}>',
                                      disposition='inline', filename=f'{cid}.{subtype}')
        for name, data, mime in self._files:
            maintype, subtype = mime.split('/', 1)
            m.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)
        return m


def _mail(subject, body, to, attachments=None, html=None, inline_images=None):
    """Send a plain-text email, optionally with a designed HTML version + embedded (cid:) images."""
    _GliMail(subject, body, to, html=html, inline_images=inline_images, attachments=attachments).send(fail_silently=False)


def photo_bytes(data_url):
    """Return JPEG bytes if data_url is a valid, small JPEG data-URL, else None."""
    prefix = 'data:image/jpeg;base64,'
    if not isinstance(data_url, str) or not data_url.startswith(prefix) or len(data_url) > 250_000:
        return None
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except Exception:
        return None
    return raw if raw[:2] == b'\xff\xd8' else None


def panel_required(view):
    """Superuser only + must have unlocked the panel with the emailed code (valid 30 min)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_superuser:
            messages.error(request, "Only the superuser can open Admin Approvals.")
            return redirect('user_list')
        if request.session.get('panel_unlocked_until', 0) < timezone.now().timestamp():
            return redirect(f"{reverse('admin_panel_unlock')}?next={quote(request.get_full_path())}")
        return view(request, *args, **kwargs)
    return wrapper


def decide_request(request, req, decision):
    """Approve or reject a pending request. Returns True if something was done."""
    if req.status != 'pending':
        messages.error(request, "This request was already reviewed.")
        return False

    if decision == 'approve':
        with transaction.atomic():
            if User.objects.filter(username__iexact=req.username).exists():
                messages.error(request, "Username was taken in the meantime. Reject this request.")
                return False
            user = User(username=req.username, email=req.email,
                        first_name=req.full_name[:150], password=req.password_hash,
                        is_staff=False, is_superuser=False, is_active=True)
            user.save()
            AdminFace.objects.create(user=user, descriptor=req.face_descriptor)
            req.user, req.status = user, 'approved'
        ActivityLog.objects.create(action=f"Admin '{req.username}' APPROVED by '{request.user.username}'.")
        subject = "Your GLI admin account was approved"
        body = f"Hi {req.full_name}, you can now log in with your password or Face ID."
        html, imgs = et.result_email(req.full_name, True, request.build_absolute_uri('/login/'))
    elif decision == 'reject':
        req.status = 'rejected'
        req.face_descriptor = ''   # drop biometric data of rejected applicants
        req.face_photo = ''
        ActivityLog.objects.create(action=f"Admin request '{req.username}' REJECTED by '{request.user.username}'.")
        subject = "Your GLI admin request was declined"
        body = f"Hi {req.full_name}, your administrator registration was not approved."
        html, imgs = et.result_email(req.full_name, False, request.build_absolute_uri('/login/'))
    else:
        return False

    req.reviewed_at, req.reviewed_by = timezone.now(), request.user.username
    req.save()
    try:
        _mail(subject, body, [req.email], html=html, inline_images=imgs)
    except Exception:
        pass
    messages.success(request, f"Request {req.status}: {req.full_name}.")
    return True


# ─────────── STEP 1 + 2: request code / enter code ───────────
def register_start(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'request_code':
            last = AdminOTP.objects.filter(purpose='register').order_by('-created_at').first()
            wait = settings.ADMIN_REG_CODE_COOLDOWN
            if last and (timezone.now() - last.created_at).total_seconds() < wait:
                left = int(wait - (timezone.now() - last.created_at).total_seconds())
                messages.error(request, f"Cooldown active. Please wait {left} seconds before requesting another code.")
                return redirect('admin_register')

            AdminOTP.objects.filter(purpose='register', is_used=False).update(is_used=True)   # cancel older codes
            code = f"{secrets.randbelow(10**6):06d}"
            minutes = settings.ADMIN_REG_CODE_MINUTES
            otp = AdminOTP.objects.create(
                purpose='register',
                code_hash=_hash_code(code),
                expires_at=timezone.now() + timedelta(minutes=minutes),
            )
            html, imgs = et.code_email('register', code, minutes, ip=request.META.get('REMOTE_ADDR'))
            try:
                _mail(
                    "GLI Admin Registration — One-Time Code",
                    f"Someone started a new administrator registration.\n\n"
                    f"One-time code: {code}\n"
                    f"Valid for {minutes} minutes, single use.\n\n"
                    f"Only give this code to the person you are expecting. If this was not expected, ignore this email.",
                    settings.ADMIN_APPROVER_EMAILS,
                    html=html, inline_images=imgs,
                )
            except Exception as e:
                otp.is_used = True
                otp.save()
                messages.error(request, f"Could not send the email: {e}")
                return redirect('admin_register')

            request.session['admin_otp_id'] = otp.id
            messages.success(request, "A one-time code was sent to the approvers. Ask them for the code, then enter it below.")
            return redirect('admin_register')

        if action == 'verify_code':
            entered = (request.POST.get('code') or '').strip()
            otp = AdminOTP.objects.filter(id=request.session.get('admin_otp_id'), purpose='register').first()
            if not otp or otp.is_used or otp.expires_at < timezone.now():
                messages.error(request, "No valid code. Please request a new one.")
                return redirect('admin_register')
            otp.attempts += 1
            if otp.attempts > MAX_CODE_ATTEMPTS:
                otp.is_used = True
                otp.save()
                messages.error(request, "Too many wrong attempts. Request a new code.")
                return redirect('admin_register')
            if not constant_time_compare(_hash_code(entered), otp.code_hash):
                otp.save()
                messages.error(request, f"Wrong code. {MAX_CODE_ATTEMPTS - otp.attempts} attempt(s) left.")
                return redirect('admin_register')

            otp.is_used = True
            otp.save()
            request.session['admin_reg_ok_until'] = (timezone.now() + timedelta(minutes=FORM_WINDOW_MINUTES)).timestamp()
            return redirect('admin_register_form')

    has_code = AdminOTP.objects.filter(
        id=request.session.get('admin_otp_id'), purpose='register', is_used=False, expires_at__gt=timezone.now()
    ).exists()
    return render(request, 'admin_register_code.html', {
        'has_code': has_code,
        'cooldown': settings.ADMIN_REG_CODE_COOLDOWN,
    })


# ─────────── STEP 3: basic info + face → PENDING ───────────
def register_form(request):
    ok_until = request.session.get('admin_reg_ok_until')
    if not ok_until or ok_until < timezone.now().timestamp():
        messages.error(request, "Code verification required (or it expired). Please start again.")
        return redirect('admin_register')

    values = {}
    if request.method == 'POST':
        values = {k: (request.POST.get(k) or '').strip() for k in
                  ['full_name', 'employee_id', 'age', 'location', 'email', 'username']}
        pw1, pw2 = request.POST.get('password', ''), request.POST.get('confirm_password', '')
        descriptor = parse_descriptor(request.POST.get('face_descriptor'))
        photo = request.POST.get('face_photo', '')
        errors = []

        if not values['full_name']:   errors.append("Full name is required.")
        if not values['employee_id']: errors.append("Employee ID is required.")
        if not values['location']:    errors.append("Location is required.")
        try:
            age = int(values['age'])
            if not 18 <= age <= 100: raise ValueError
        except ValueError:
            age = None
            errors.append("Age must be a number between 18 and 100.")
        if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', values['email']):
            errors.append("Enter a valid email.")
        if not USERNAME_RE.match(values['username']):
            errors.append("Username must be 4-30 letters, numbers, dot, dash or underscore.")
        if (User.objects.filter(username__iexact=values['username']).exists() or
                AdminRegistrationRequest.objects.filter(username__iexact=values['username'], status='pending').exists()):
            errors.append("That username is already taken.")
        if (User.objects.filter(email__iexact=values['email']).exists() or
                AdminRegistrationRequest.objects.filter(email__iexact=values['email'], status='pending').exists()):
            errors.append("That email is already registered or pending.")
        if pw1 != pw2:
            errors.append("Passwords do not match.")
        else:
            try:
                validate_password(pw1)
            except ValidationError as e:
                errors.extend(e.messages)
        if descriptor is None:
            errors.append("Face scan is required.")
        elif find_matching_face(descriptor)[0] is not None:
            errors.append("This face is already registered to an administrator.")
        if photo_bytes(photo) is None:
            errors.append("Face photo is missing. Please scan your face again.")

        # Double-submit protection: same request was just saved a moment ago -> show the pending page
        just_saved = AdminRegistrationRequest.objects.filter(
            username__iexact=values['username'], email__iexact=values['email'],
            status='pending', created_at__gte=timezone.now() - timedelta(minutes=2),
        ).exists()
        if errors and just_saved:
            return redirect('admin_register_pending')

        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            req = AdminRegistrationRequest.objects.create(
                full_name=values['full_name'], employee_id=values['employee_id'], age=age,
                location=values['location'], email=values['email'], username=values['username'],
                password_hash=make_password(pw1),
                face_descriptor=json.dumps(descriptor),
                face_photo=photo,
                token=secrets.token_urlsafe(32),
            )
            link = request.build_absolute_uri(f"/admin-approve/{req.token}/")
            html, imgs = et.approval_email(req, link, photo_bytes(photo))
            try:
                _mail(
                    "GLI Admin Registration — APPROVAL NEEDED",
                    f"A new administrator is waiting for approval. The applicant's face photo is attached.\n\n"
                    f"Name: {req.full_name}\nEmployee ID: {req.employee_id}\nAge: {req.age}\n"
                    f"Location: {req.location}\nEmail: {req.email}\nUsername: {req.username}\n\n"
                    f"Review (superuser login + emailed unlock code required):\n{link}\n",
                    settings.ADMIN_APPROVER_EMAILS,
                    attachments=[('applicant_face.jpg', photo_bytes(photo), 'image/jpeg')],
                    html=html, inline_images=imgs,
                )
            except Exception:
                pass  # request is still saved; it will show in the Admin Approvals panel
            ActivityLog.objects.create(action=f"Admin registration request submitted by '{req.full_name}' (pending approval).")
            request.session.pop('admin_reg_ok_until', None)
            return redirect('admin_register_pending')

    return render(request, 'admin_register_form.html', {'v': values})


def register_pending(request):
    return render(request, 'admin_pending.html')


# ─────────── approve / reject from the emailed link ───────────
@panel_required
def approve_request(request, token):
    req = get_object_or_404(AdminRegistrationRequest, token=token)
    if request.method == 'POST':
        decide_request(request, req, request.POST.get('decision'))
        return redirect('admin_approve', token=token)
    return render(request, 'admin_approve.html', {'req': req})