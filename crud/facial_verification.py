"""
crud/facial_verification.py  (NEW FILE)
Face ID for admin login. The browser (face-api.js) does the liveness check and turns the
face into 128 numbers; the server only stores/compares those numbers. No photos are saved.
"""
import json
import math

from django.contrib.auth import login
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import ActivityLog, AdminFace

# Lower = stricter. 0.6 is the library default; 0.45 is a safer value for a login.
MATCH_THRESHOLD = 0.45
MAX_FAILS = 8            # per IP
LOCK_SECONDS = 600       # 10 minutes


def parse_descriptor(raw):
    """Return a clean list of 128 floats, or None if the data is invalid."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(data, list) or len(data) != 128:
            return None
        vec = [float(x) for x in data]
        if any(math.isnan(x) or math.isinf(x) for x in vec):
            return None
        return vec
    except (ValueError, TypeError):
        return None


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def find_matching_face(descriptor):
    """Return (AdminFace, distance) of the closest face under the threshold, else (None, None)."""
    best, best_d = None, 9.9
    for face in AdminFace.objects.select_related('user').filter(user__is_active=True):
        stored = parse_descriptor(face.descriptor)
        if not stored:
            continue
        d = distance(descriptor, stored)
        if d < best_d:
            best, best_d = face, d
    if best is not None and best_d <= MATCH_THRESHOLD:
        return best, best_d
    return None, None


def _client_ip(request):
    return request.META.get('REMOTE_ADDR', 'unknown')


def face_login_page(request):
    return render(request, 'facial_login.html')


@require_POST
def face_login_verify(request):
    key = f"facelogin:{_client_ip(request)}"
    fails = cache.get(key, 0)
    if fails >= MAX_FAILS:
        return JsonResponse({'ok': False, 'error': 'Too many failed attempts. Try again in 10 minutes or use your password.'}, status=429)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Bad request.'}, status=400)

    descriptor = parse_descriptor(payload.get('descriptor'))
    if descriptor is None:
        return JsonResponse({'ok': False, 'error': 'Invalid face data.'}, status=400)

    face, dist = find_matching_face(descriptor)
    if face is None:
        cache.set(key, fails + 1, LOCK_SECONDS)
        return JsonResponse({'ok': False, 'error': 'Face not recognized. Try again or use your password.'}, status=401)

    cache.delete(key)
    user = face.user
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    ActivityLog.objects.create(action=f"Administrator session initiated by '{user.username}' via Face ID.")
    return JsonResponse({'ok': True, 'redirect': reverse('user_list')})
