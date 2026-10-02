"""
crud/admin_panel.py  (NEW FILE)
Admin Approvals panel: pending requests (with face photo), current admins, activity logs.
Locked behind: superuser login + a one-time code emailed to ADMIN_PANEL_CODE_EMAILS.
"""
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme

from .admin_registration import (
    panel_required, decide_request, _hash_code, _mail,
    PANEL_UNLOCK_MINUTES, MAX_CODE_ATTEMPTS,
)
from .models import ActivityLog, AdminFace, AdminOTP, AdminRegistrationRequest


def _panel_emails():
    # Optional override in settings.py:  ADMIN_SPANEL_CODE_EMAILS = ['you@gmail.com']
    return getattr(settings, 'ADMIN_PANEL_CODE_EMAILS', ['kyoshidecastro@gmail.com'])


def _mask(email):
    name, _, domain = email.partition('@')
    return f"{name[:1]}{'*' * max(len(name) - 1, 2)}@{domain}"


# ─────────── unlock gate ───────────
def panel_unlock(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not request.user.is_superuser:
        messages.error(request, "Only the superuser can open Admin Approvals.")
        return redirect('user_list')

    nxt = request.GET.get('next') or request.POST.get('next') or '/admin-panel/'
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = '/admin-panel/'
    back = f"{request.path}?next={quote(nxt)}"

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_code':
            last = AdminOTP.objects.filter(purpose='panel').order_by('-created_at').first()
            wait = settings.ADMIN_REG_CODE_COOLDOWN
            if last and (timezone.now() - last.created_at).total_seconds() < wait:
                left = int(wait - (timezone.now() - last.created_at).total_seconds())
                messages.error(request, f"Cooldown active. Wait {left} seconds before requesting another code.")
                return redirect(back)

            AdminOTP.objects.filter(purpose='panel', is_used=False).update(is_used=True)
            code = f"{secrets.randbelow(10**6):06d}"
            minutes = settings.ADMIN_REG_CODE_MINUTES
            otp = AdminOTP.objects.create(
                purpose='panel', code_hash=_hash_code(code),
                expires_at=timezone.now() + timedelta(minutes=minutes),
            )
            try:
                _mail(
                    "GLI Admin Panel — Unlock Code",
                    f"'{request.user.username}' is trying to open the Admin Approvals panel.\n\n"
                    f"Unlock code: {code}\nValid for {minutes} minutes, single use.\n\n"
                    f"If this was not you, do NOT share this code and change your password.",
                    _panel_emails(),
                )
            except Exception as e:
                otp.is_used = True
                otp.save()
                messages.error(request, f"Could not send the email: {e}")
                return redirect(back)
            request.session['panel_otp_id'] = otp.id
            messages.success(request, f"Unlock code sent to {', '.join(_mask(e) for e in _panel_emails())}.")
            return redirect(back)

        if action == 'verify_code':
            entered = (request.POST.get('code') or '').strip()
            otp = AdminOTP.objects.filter(id=request.session.get('panel_otp_id'), purpose='panel').first()
            if not otp or otp.is_used or otp.expires_at < timezone.now():
                messages.error(request, "No valid code. Please request a new one.")
                return redirect(back)
            otp.attempts += 1
            if otp.attempts > MAX_CODE_ATTEMPTS:
                otp.is_used = True
                otp.save()
                messages.error(request, "Too many wrong attempts. Request a new code.")
                return redirect(back)
            if not constant_time_compare(_hash_code(entered), otp.code_hash):
                otp.save()
                messages.error(request, f"Wrong code. {MAX_CODE_ATTEMPTS - otp.attempts} attempt(s) left.")
                return redirect(back)

            otp.is_used = True
            otp.save()
            request.session['panel_unlocked_until'] = (timezone.now() + timedelta(minutes=PANEL_UNLOCK_MINUTES)).timestamp()
            ActivityLog.objects.create(action=f"Admin Approvals panel unlocked by '{request.user.username}'.")
            return redirect(nxt)

    has_code = AdminOTP.objects.filter(
        id=request.session.get('panel_otp_id'), purpose='panel', is_used=False, expires_at__gt=timezone.now()
    ).exists()
    return render(request, 'admin_panel_gate.html', {
        'has_code': has_code, 'next': nxt,
        'cooldown': settings.ADMIN_REG_CODE_COOLDOWN,
        'masked': [_mask(e) for e in _panel_emails()],
    })


# ─────────── the panel ───────────
@panel_required
def panel_home(request):
    if request.method == 'POST':
        tab = request.POST.get('tab', 'pending')
        if tab not in ('pending', 'admins', 'logs'):
            tab = 'pending'

        if 'lock_panel' in request.POST:
            request.session.pop('panel_unlocked_until', None)
            messages.success(request, "Admin Approvals panel locked.")
            return redirect('user_list')

        if 'decision' in request.POST:
            req = get_object_or_404(AdminRegistrationRequest, token=request.POST.get('token', ''))
            decide_request(request, req, request.POST.get('decision'))

        elif 'toggle_user' in request.POST:
            target = get_object_or_404(User, pk=request.POST.get('toggle_user'))
            if target.pk == request.user.pk or target.is_superuser:
                messages.error(request, "You cannot disable yourself or a superuser.")
            else:
                target.is_active = not target.is_active
                target.save()
                state = 'ENABLED' if target.is_active else 'DISABLED'
                ActivityLog.objects.create(action=f"Admin '{target.username}' {state} by '{request.user.username}'.")
                messages.success(request, f"{target.username} {state.lower()}.")
        return redirect(f"/admin-panel/?tab={tab}")

    photos = {r.user_id: r.face_photo for r in AdminRegistrationRequest.objects.filter(user__isnull=False)}
    face_ids = set(AdminFace.objects.values_list('user_id', flat=True))
    admins = [
        {'u': u, 'photo': photos.get(u.id, ''), 'has_face': u.id in face_ids}
        for u in User.objects.order_by('-is_superuser', 'username')
    ]
    pending = AdminRegistrationRequest.objects.filter(status='pending').order_by('-created_at')
    left = int((request.session.get('panel_unlocked_until', 0) - timezone.now().timestamp()) / 60)

    tab = request.GET.get('tab', 'pending')
    return render(request, 'admin_panel.html', {
        'pending': pending,
        'admins': admins,
        'logs': ActivityLog.objects.order_by('-timestamp')[:200],
        'active_tab': tab if tab in ('pending', 'admins', 'logs') else 'pending',
        'minutes_left': max(left, 0),
    })
