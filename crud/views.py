import csv
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from .models import UserProfile, Gender

# --- LIVE SECURITY SCANNERS (AJAX) ---
def check_username_exists(request):
    u = request.GET.get('username', None)
    u_id = request.GET.get('user_id', None)
    query = UserProfile.objects.filter(username__iexact=u)
    if u_id: query = query.exclude(id=u_id)
    return JsonResponse({'is_taken': query.exists()})

def check_email_exists(request):
    e = request.GET.get('email', None)
    u_id = request.GET.get('user_id', None)
    query = UserProfile.objects.filter(email__iexact=e)
    if u_id: query = query.exclude(id=u_id)
    return JsonResponse({'is_taken': query.exists()})

# --- FILVAULT HUB ---
def user_list(request):
    query = request.GET.get('q', '')
    show_archived = request.GET.get('filter') == 'archived'
    
    if request.method == "POST":
        # 1. GENDER MANAGEMENT
        if 'add_gender' in request.POST:
            Gender.objects.create(gender=request.POST.get('gender_name'))
            messages.success(request, "New category synchronized.")
            return redirect('user_list')
        
        elif 'edit_gender' in request.POST:
            g = get_object_or_404(Gender, id=request.POST.get('gender_id'))
            g.gender = request.POST.get('gender_name')
            g.save()
            messages.success(request, "Category updated.")
            return redirect('user_list')

        elif 'delete_gender' in request.POST:
            get_object_or_404(Gender, id=request.POST.get('gender_id')).delete()
            messages.warning(request, "Category purged.")
            return redirect('user_list')

        # 2. IDENTITY REGISTRY (ADD & EDIT)
        elif 'add_user' in request.POST or 'edit_user' in request.POST:
            u_id = request.POST.get('user_id')
            user = get_object_or_404(UserProfile, id=u_id) if u_id else UserProfile()
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.gender_id = request.POST.get('gender')
            if request.POST.get('password'): 
                user.password = make_password(request.POST.get('password'))
            if request.FILES.get('profile_pic'): 
                user.profile_pic = request.FILES.get('profile_pic')
            user.save()
            messages.success(request, "Vault: Identity Synchronized.")
            return redirect('user_list')

        # 3. BULK ACTIONS
        elif 'bulk_action' in request.POST:
            ids = request.POST.getlist('selected_users')
            action = request.POST.get('action_type')
            if ids:
                if action == 'archive': UserProfile.objects.filter(id__in=ids).update(is_active=False)
                elif action == 'recover': UserProfile.objects.filter(id__in=ids).update(is_active=True)
                elif action == 'purge': UserProfile.objects.filter(id__in=ids).delete()
                messages.success(request, f"Bulk {action} complete.")
            return redirect('user_list')

    # DATA SCAN
    is_active_status = not show_archived
    users = UserProfile.objects.filter(is_active=is_active_status).filter(
        Q(username__icontains=query) | Q(email__icontains=query) | Q(gender__gender__icontains=query)
    ).order_by('-id')

    return render(request, 'user_list.html', {
        'users': users, 
        'genders': Gender.objects.all(), 
        'query': query,
        'total': UserProfile.objects.count(), 
        'is_archived_view': show_archived,
        'm_count': UserProfile.objects.filter(is_active=True, gender__gender__iexact='Male').count(),
        'f_count': UserProfile.objects.filter(is_active=True, gender__gender__iexact='Female').count(),
    })

def delete_user(request, pk):
    UserProfile.objects.filter(pk=pk).update(is_active=False)
    messages.warning(request, "Identity moved to archive.")
    return redirect('user_list')

def recover_user(request, pk):
    UserProfile.objects.filter(pk=pk).update(is_active=True)
    messages.success(request, "Identity restored.")
    return redirect('/?filter=archived')

def permanent_purge(request, pk):
    get_object_or_404(UserProfile, pk=pk).delete()
    messages.error(request, "PERMANENTLY PURGED.")
    return redirect('/?filter=archived')

def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="FILVAULT_EXPORT.csv"'
    writer = csv.writer(response)
    writer.writerow(['USERNAME', 'EMAIL', 'CATEGORY'])
    for u in UserProfile.objects.filter(is_active=True):
        writer.writerow([u.username, u.email, u.gender.gender])
    return response