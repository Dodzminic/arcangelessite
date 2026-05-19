import csv
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.core.paginator import Paginator
# --- FIX: Restored the missing core system time library import natively ---
from django.utils import timezone
from .models import UserProfile, Gender, ActivityLog, AssignmentLocation, EmployeeRole

# --- PORTAL SECURITY LOGIN ---
def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_list')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            ActivityLog.objects.create(action=f"Administrator session initiated by '{user.username}'.")
            return redirect('user_list')
        else:
            messages.error(request, "Access Denied: Invalid Administrative Credentials.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        ActivityLog.objects.create(action=f"Administrator session closed by '{request.user.username}'.")
    logout(request)
    messages.info(request, "Session Terminated: Securely signed out of database engine.")
    return redirect('login')

# --- LIVE SECURITY SCANNERS ---
@login_required(login_url='login')
def check_username_exists(request):
    u = request.GET.get('username', None)
    u_id = request.GET.get('user_id', None)
    query = UserProfile.objects.filter(username__iexact=u)
    if u_id: query = query.exclude(id=u_id)
    return JsonResponse({'is_taken': query.exists()})

@login_required(login_url='login')
def check_email_exists(request):
    e = request.GET.get('email', None)
    u_id = request.GET.get('user_id', None)
    query = UserProfile.objects.filter(email__iexact=e)
    if u_id: query = query.exclude(id=u_id)
    return JsonResponse({'is_taken': query.exists()})

# --- FILVAULT HUB ---
@login_required(login_url='login')
def user_list(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'newest')
    filter_assignment = request.GET.get('assignment', '')
    filter_role = request.GET.get('role', '')
    page_number = request.GET.get('page', 1)
    
    if request.method == "POST":
        if 'export_backup_json' in request.POST:
            data = []
            for u in UserProfile.objects.all():
                data.append({
                    'username': u.username, 'employee_name': u.employee_name, 'age': u.age,
                    'email': u.email, 'address': u.address, 'password': u.password,
                    'is_active': u.is_active,
                    'gender': u.gender.gender, 'role': u.role_rel.name if u.role_rel else None,
                    'assignment': u.assignment_rel.name if u.assignment_rel else None
                })
            res = HttpResponse(json.dumps(data, indent=4), content_type="application/json")
            res['Content-Disposition'] = 'attachment; filename="GLI_DATABASE_BACKUP.json"'
            return res

        # GENDER HUB
        if 'add_gender' in request.POST:
            g_name = request.POST.get('gender_name')
            Gender.objects.create(gender=g_name)
            ActivityLog.objects.create(action=f"New gender '{g_name}' defined.")
            messages.success(request, "Gender type synchronized.")
            return redirect('/?open_modal=genderRegistryModal')
        
        elif 'edit_gender' in request.POST:
            g_id = request.POST.get('gender_id')
            g_name = request.POST.get('gender_name')
            g = get_object_or_404(Gender, id=g_id)
            old_name = g.gender
            g.gender = g_name
            g.save()
            ActivityLog.objects.create(action=f"Gender '{old_name}' renamed to '{g_name}'. Linked profiles updated.")
            messages.success(request, f"Gender updated. All active records updated.")
            return redirect('/?open_modal=genderRegistryModal')
            
        elif 'delete_gender' in request.POST:
            g = get_object_or_404(Gender, id=request.POST.get('gender_id'))
            if UserProfile.objects.filter(gender=g).exists():
                messages.error(request, f"PURGE DENIED: '{g.gender}' cannot be deleted because it is currently assigned to active identities.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Gender '{g.gender}' purged.")
                g.delete()
                messages.warning(request, "Gender type purged.")
            return redirect('/?open_modal=genderRegistryModal')

        # --- ASSIGNMENT LOCATION CONSTRAINTS MATRIX ---
        elif 'add_assignment' in request.POST:
            a_name = request.POST.get('assignment_name')
            b_color = "badge-field-site" if "field" in a_name.lower() or "site" in a_name.lower() else "badge-office-hq"
            AssignmentLocation.objects.create(name=a_name, badge_color=b_color)
            ActivityLog.objects.create(action=f"New Assignment Area '{a_name}' configured.")
            messages.success(request, "Assignment location added successfully.")
            return redirect('/?open_modal=assignmentRegistryModal')

        elif 'edit_assignment' in request.POST:
            a_id = request.POST.get('assignment_id')
            a_name = request.POST.get('assignment_name')
            a = get_object_or_404(AssignmentLocation, id=a_id)
            old_name = a.name
            a.name = a_name
            a.badge_color = "badge-field-site" if "field" in a_name.lower() or "site" in a_name.lower() else "badge-office-hq"
            a.save()
            ActivityLog.objects.create(action=f"Assignment area '{old_name}' renamed to '{a_name}'.")
            messages.success(request, "Assignment area updated. All profiles synced.")
            return redirect('/?open_modal=assignmentRegistryModal')

        elif 'delete_assignment' in request.POST:
            a = get_object_or_404(AssignmentLocation, id=request.POST.get('assignment_id'))
            if UserProfile.objects.filter(assignment_rel=a).exists():
                messages.error(request, f"PURGE DENIED: '{a.name}' cannot be deleted because it is currently assigned to active identities.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Assignment location '{a.name}' deleted.")
                a.delete()
                messages.warning(request, "Assignment location successfully cleared.")
            return redirect('/?open_modal=assignmentRegistryModal')

        # --- EMPLOYEE ROLE CONSTRAINTS MATRIX ---
        elif 'add_role' in request.POST:
            r_name = request.POST.get('role_name')
            EmployeeRole.objects.create(name=r_name)
            ActivityLog.objects.create(action=f"New System Role '{r_name}' added.")
            messages.success(request, "System role initialized.")
            return redirect('/?open_modal=roleRegistryModal')

        elif 'edit_role' in request.POST:
            r_id = request.POST.get('role_id')
            r_name = request.POST.get('role_name')
            r = get_object_or_404(EmployeeRole, id=r_id)
            old_name = r.name
            r.name = r_name
            r.save()
            ActivityLog.objects.create(action=f"System Role '{old_name}' renamed to '{r_name}'.")
            messages.success(request, "System role updated. All profiles synced.")
            return redirect('/?open_modal=roleRegistryModal')

        elif 'delete_role' in request.POST:
            r = get_object_or_404(EmployeeRole, id=request.POST.get('role_id'))
            if UserProfile.objects.filter(role_rel=r).exists():
                messages.error(request, f"PURGE DENIED: '{r.name}' cannot be deleted because it is currently assigned to active identities.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Role '{r.name}' completely purged.")
                r.delete()
                messages.warning(request, "System role purged.")
            return redirect('/?open_modal=roleRegistryModal')

        # IDENTITY ACTIONS
        elif 'add_user' in request.POST or 'edit_user' in request.POST:
            u_id = request.POST.get('user_id')
            user = get_object_or_404(UserProfile, id=u_id) if u_id else UserProfile()
            
            if not u_id:
                current_year = timezone.now().year
                total_records_historical = UserProfile.objects.count() + 1
                user.username = f"GLI-{current_year}-{total_records_historical:04d}"
            else:
                user.username = request.POST.get('username')
                
            user.employee_name = request.POST.get('employee_name')
            user.age = int(request.POST.get('age', 18))
            user.email = request.POST.get('email')
            user.address = request.POST.get('address')
            user.assignment_rel_id = request.POST.get('office_or_field')
            user.role_rel_id = request.POST.get('role')
            user.gender_id = request.POST.get('gender')
            
            if request.POST.get('password'): 
                user.password = make_password(request.POST.get('password'))
            if request.FILES.get('profile_pic'): 
                user.profile_pic = request.FILES.get('profile_pic')
            user.save()
            
            ActivityLog.objects.create(action=f"Employee Record '{user.employee_name}' synchronized with ID {user.username}.")
            messages.success(request, f"Vault: {user.employee_name} Synchronized.")
            return redirect('user_list')

        # BULK ACTIONS
        elif 'bulk_action' in request.POST:
            ids = request.POST.getlist('selected_users')
            action = request.POST.get('action_type')
            if ids:
                if action == 'archive': 
                    UserProfile.objects.filter(id__in=ids).update(is_active=False)
                    messages.success(request, f"Selected employee files successfully archived.")
                    return redirect('user_list')
                elif action == 'recover': 
                    UserProfile.objects.filter(id__in=ids).update(is_active=True)
                    messages.success(request, f"Selected profiles successfully restored to active records.")
                    return redirect('/?open_modal=archiveVaultModal')
                elif action == 'purge': 
                    UserProfile.objects.filter(id__in=ids).delete()
                    messages.warning(request, f"Selected profiles permanently deleted from database storage.")
                    return redirect('/?open_modal=archiveVaultModal')

    # DATA SCAN
    all_users = UserProfile.objects.filter(is_active=True)

    if query:
        all_users = all_users.filter(
            Q(username__icontains=query) | 
            Q(employee_name__icontains=query) | 
            Q(email__icontains=query) |
            Q(address__icontains=query) |
            Q(gender__gender__icontains=query) |
            Q(role_rel__name__icontains=query) |
            Q(assignment_rel__name__icontains=query)
        )
    if filter_assignment:
        all_users = all_users.filter(assignment_rel_id=filter_assignment)
    if filter_role:
        all_users = all_users.filter(role_rel_id=filter_role)

    if sort == 'oldest': all_users = all_users.order_by('id')
    elif sort == 'az': all_users = all_users.order_by('employee_name')
    elif sort == 'za': all_users = all_users.order_by('-employee_name')
    else: all_users = all_users.order_by('-id')

    paginator = Paginator(all_users, 10)
    page_obj = paginator.get_page(page_number)

    next_year_string = timezone.now().year
    next_count_seed = UserProfile.objects.count() + 1
    generated_id_seed = f"GLI-{next_year_string}-{next_count_seed:04d}"

    office_count = UserProfile.objects.filter(is_active=True, assignment_rel__badge_color="badge-office-hq").count()
    field_count = UserProfile.objects.filter(is_active=True, assignment_rel__badge_color="badge-field-site").count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'user_table_partial.html', {'users': page_obj})

    return render(request, 'user_list.html', {
        'users': page_obj, 
        'archived_users': UserProfile.objects.filter(is_active=False),
        'genders': Gender.objects.all(), 
        'assignments': AssignmentLocation.objects.all(),
        'roles': EmployeeRole.objects.all(),
        'recent_logs': ActivityLog.objects.all().order_by('-timestamp')[:5],
        'query': query,
        'current_sort': sort,
        'current_assignment': filter_assignment,
        'current_role': filter_role,
        'total': UserProfile.objects.filter(is_active=True).count(), 
        'm_count': UserProfile.objects.filter(is_active=True, gender__gender__iexact='Male').count(),
        'f_count': UserProfile.objects.filter(is_active=True, gender__gender__iexact='Female').count(),
        'office_count': office_count,
        'field_count': field_count,
        'open_modal': request.GET.get('open_modal', ''),
        'next_id_generation': generated_id_seed
    })

@login_required(login_url='login')
def delete_user(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    u.is_active = False
    u.save()
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' moved to system archive.")
    return redirect('/')

@login_required(login_url='login')
def recover_user(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    u.is_active = True
    u.save()
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' restored to active files.")
    return redirect('/?open_modal=archiveVaultModal')

@login_required(login_url='login')
def permanent_purge(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' permanently purged from core database.")
    u.delete()
    return redirect('/?open_modal=archiveVaultModal')

@login_required(login_url='login')
def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="GLI_EMPLOYEE_EXPORT.csv"'
    writer = csv.writer(response)
    writer.writerow(['EMPLOYEE ID', 'FULL NAME', 'AGE', 'GENDER', 'EMAIL', 'ADDRESS', 'ASSIGNMENT', 'ROLE'])
    for u in UserProfile.objects.filter(is_active=True):
        writer.writerow([u.username, u.employee_name, u.age, u.gender.gender, u.email, u.address, u.assignment_rel.name if u.assignment_rel else '', u.role_rel.name if u.role_rel else ''])
    return response