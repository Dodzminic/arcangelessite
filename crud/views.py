import csv
import io
import json
from datetime import timedelta, date
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from .models import UserProfile, Gender, ActivityLog, AssignmentLocation, EmployeeRole

# --- PORTAL SECURITY LOGIN ---
def login_view(request):
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
    return redirect('/login/?logout=1')

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
    query             = request.GET.get('q', '')
    sort              = request.GET.get('sort', 'newest')
    filter_assignment = request.GET.get('assignment', '')
    filter_role       = request.GET.get('role', '')
    page_number       = request.GET.get('page', 1)
    
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
            g_name  = request.POST.get('gender_name')
            g_icon  = request.POST.get('gender_icon', 'bi-gender-ambiguous')
            g_color = request.POST.get('gender_color', '#c4b5fd')
            Gender.objects.create(gender=g_name, icon=g_icon, color=g_color)
            ActivityLog.objects.create(action=f"New gender '{g_name}' defined.")
            messages.success(request, "Gender type synchronized.")
            return redirect('/dashboard/?open_modal=genderRegistryModal')
        
        elif 'edit_gender' in request.POST:
            g_id    = request.POST.get('gender_id')
            g_name  = request.POST.get('gender_name')
            g_icon  = request.POST.get('gender_icon', 'bi-gender-ambiguous')
            g_color = request.POST.get('gender_color', '#c4b5fd')
            g = get_object_or_404(Gender, id=g_id)
            old_name = g.gender
            g.gender = g_name
            g.icon   = g_icon
            g.color  = g_color
            g.save()
            ActivityLog.objects.create(action=f"Gender '{old_name}' renamed to '{g_name}'. Linked profiles updated.")
            messages.success(request, f"Gender updated. All active records updated.")
            return redirect('/dashboard/?open_modal=genderRegistryModal')
            
        elif 'delete_gender' in request.POST:
            g = get_object_or_404(Gender, id=request.POST.get('gender_id'))
            if UserProfile.objects.filter(gender=g).exists():
                messages.error(request, f"PURGE DENIED: '{g.gender}' cannot be deleted because it is currently assigned to active identities.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Gender '{g.gender}' purged.")
                g.delete()
                messages.warning(request, "Gender type purged.")
            return redirect('/dashboard/?open_modal=genderRegistryModal')

        # --- ASSIGNMENT LOCATION CONSTRAINTS MATRIX ---
        elif 'add_assignment' in request.POST:
            a_name  = request.POST.get('assignment_name')
            b_color = request.POST.get('badge_color', 'badge-office-hq')
            a_icon  = request.POST.get('assignment_icon', 'bi-geo-alt-fill')
            AssignmentLocation.objects.create(name=a_name, badge_color=b_color, icon=a_icon)
            ActivityLog.objects.create(action=f"New Assignment Area '{a_name}' configured.")
            messages.success(request, "Assignment location added successfully.")
            return redirect('/dashboard/?open_modal=assignmentRegistryModal')




        elif 'reset_password' in request.POST:
            pk       = request.POST.get('user_pk')
            new_pwd  = request.POST.get('new_password', '')
            u = get_object_or_404(UserProfile, pk=pk)
            if new_pwd and len(new_pwd) >= 4:
                u.password = make_password(new_pwd)
                u.save()
                ActivityLog.objects.create(action=f"Password reset for employee '{u.employee_name}' ({u.username}) by admin.")
                messages.success(request, f"Password for {u.employee_name} has been reset successfully.")
            else:
                messages.error(request, "Password too short. Minimum 4 characters required.")
            return redirect('/dashboard/')

        elif 'import_csv' in request.POST:
            csv_file = request.FILES.get('csv_file')
            if not csv_file or not csv_file.name.endswith('.csv'):
                messages.error(request, "Invalid file. Please upload a .csv file.")
                return redirect('/dashboard/')
            try:
                decoded = csv_file.read().decode('utf-8-sig')
                reader  = csv.DictReader(io.StringIO(decoded))
                created = 0
                skipped = 0
                errors  = []
                for i, row in enumerate(reader, start=2):
                    try:
                        emp_name   = row.get('employee_name', '').strip()
                        email      = row.get('email', '').strip()
                        password   = row.get('password', 'GLI@2025').strip()
                        age        = int(row.get('age', 18) or 18)
                        gender_str = row.get('gender', '').strip()
                        address    = row.get('address', '').strip()
                        assign_str = row.get('assignment', '').strip()
                        role_str   = row.get('role', '').strip()

                        if not emp_name or not email:
                            errors.append(f"Row {i}: Missing employee_name or email — skipped.")
                            skipped += 1
                            continue
                        if UserProfile.objects.filter(email=email).exists():
                            errors.append(f"Row {i}: Email '{email}' already exists — skipped.")
                            skipped += 1
                            continue

                        # Resolve FK fields — create if not found
                        gender_obj = Gender.objects.filter(gender__iexact=gender_str).first()
                        if not gender_obj and gender_str:
                            gender_obj = Gender.objects.create(gender=gender_str)

                        assign_obj = AssignmentLocation.objects.filter(name__iexact=assign_str).first() if assign_str else None
                        role_obj   = EmployeeRole.objects.filter(name__iexact=role_str).first() if role_str else None

                        # Generate unique employee ID
                        year    = timezone.now().year
                        last_id = UserProfile.objects.filter(username__startswith=f'GLI-{year}-').count() + created + 1
                        emp_id  = f'GLI-{year}-{str(last_id).zfill(4)}'
                        while UserProfile.objects.filter(username=emp_id).exists():
                            last_id += 1
                            emp_id = f'GLI-{year}-{str(last_id).zfill(4)}'

                        UserProfile.objects.create(
                            username       = emp_id,
                            employee_name  = emp_name,
                            email          = email,
                            password       = make_password(password),
                            age            = age,
                            gender         = gender_obj,
                            address        = address,
                            assignment_rel = assign_obj,
                            role_rel       = role_obj,
                            department     = None,
                            is_active      = True,
                        )
                        created += 1
                    except Exception as row_err:
                        errors.append(f"Row {i}: {str(row_err)}")
                        skipped += 1

                ActivityLog.objects.create(action=f"CSV Import: {created} employees imported, {skipped} skipped by admin.")
                msg = f"Import complete — {created} employees added"
                if skipped: msg += f", {skipped} skipped"
                if errors:  msg += f". Issues: {'; '.join(errors[:3])}"
                if created > 0:
                    messages.success(request, msg)
                else:
                    messages.warning(request, msg)
            except Exception as e:
                messages.error(request, f"CSV Import failed: {str(e)}")
            return redirect('/dashboard/')

        elif 'edit_assignment' in request.POST:
            a_id = request.POST.get('assignment_id')
            a_name = request.POST.get('assignment_name')
            a = get_object_or_404(AssignmentLocation, id=a_id)
            old_name = a.name
            a.name = a_name
            a.badge_color = request.POST.get('badge_color', a.badge_color)
            a.icon = request.POST.get('assignment_icon', a.icon)
            a.save()
            ActivityLog.objects.create(action=f"Assignment area '{old_name}' renamed to '{a_name}'.")
            messages.success(request, "Assignment area updated. All profiles synced.")
            return redirect('/dashboard/?open_modal=assignmentRegistryModal')

        elif 'delete_assignment' in request.POST:
            a = get_object_or_404(AssignmentLocation, id=request.POST.get('assignment_id'))
            if UserProfile.objects.filter(assignment_rel=a).exists():
                messages.error(request, f"PURGE DENIED: '{a.name}' cannot be deleted because it is currently assigned to active identities.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Assignment location '{a.name}' deleted.")
                a.delete()
                messages.warning(request, "Assignment location successfully cleared.")
            return redirect('/dashboard/?open_modal=assignmentRegistryModal')


        # ROLE MANAGEMENT
        elif 'add_role' in request.POST:
            r_name  = request.POST.get('role_name')
            r_icon  = request.POST.get('role_icon', 'bi-briefcase-fill')
            r_color = request.POST.get('role_color', '#3d7fff')
            EmployeeRole.objects.create(name=r_name, icon=r_icon, color=r_color)
            ActivityLog.objects.create(action=f"New role '{r_name}' defined.")
            messages.success(request, "Role synchronized.")
            return redirect('/dashboard/?open_modal=roleRegistryModal')

        elif 'edit_role' in request.POST:
            r_id    = request.POST.get('role_id')
            r_name  = request.POST.get('role_name')
            r_icon  = request.POST.get('role_icon', 'bi-briefcase-fill')
            r_color = request.POST.get('role_color', '#3d7fff')
            r = get_object_or_404(EmployeeRole, id=r_id)
            old_name = r.name
            r.name  = r_name
            r.icon  = r_icon
            r.color = r_color
            r.save()
            ActivityLog.objects.create(action=f"Role '{old_name}' renamed to '{r_name}'.")
            messages.success(request, f"Role updated.")
            return redirect('/dashboard/?open_modal=roleRegistryModal')

        elif 'delete_role' in request.POST:
            r = get_object_or_404(EmployeeRole, id=request.POST.get('role_id'))
            if UserProfile.objects.filter(role_rel=r).exists():
                messages.error(request, f"PURGE DENIED: '{r.name}' is assigned to active employees.", extra_tags='in_use')
            else:
                ActivityLog.objects.create(action=f"Role '{r.name}' purged.")
                r.delete()
                messages.warning(request, "Role purged.")
            return redirect('/dashboard/?open_modal=roleRegistryModal')

        # IDENTITY ACTIONS
        elif 'add_user' in request.POST or 'edit_user' in request.POST:
            # --- ROOT FIX: HTML form sends 'pk', not 'user_id' — must match the hidden input name="pk" ---
            u_id = request.POST.get('pk', '').strip()
            new_email = request.POST.get('email', '').strip()
            is_editing = u_id and u_id not in ('', 'None', 'null', '0')

            if is_editing:
                # Fetch the EXISTING user record to update it, never create a new one
                user = get_object_or_404(UserProfile, id=u_id)
                action_mode = "Updated"
            else:
                user = UserProfile()
                # Auto ID generation ONLY for new records
                current_year = timezone.now().year
                prefix = f"GLI-{current_year}-"
                last_user = UserProfile.objects.filter(username__startswith=prefix).order_by('-username').first()
                new_number = (int(last_user.username.split('-')[-1]) + 1) if last_user else 1
                user.username = f"{prefix}{new_number:04d}"
                action_mode = "Created"

            # Email duplicate check — when editing, exclude self so unchanged email never triggers false error
            duplicate_email = UserProfile.objects.filter(email__iexact=new_email)
            if is_editing:
                duplicate_email = duplicate_email.exclude(id=u_id)
            
            if duplicate_email.exists():
                messages.error(request, f"Action Denied: The email '{new_email}' is already registered to another user.")
            else:
                user.employee_name = request.POST.get('employee_name')
                # Birthday → auto-calculate age
                bday_str = request.POST.get('birthday', '').strip()
                if bday_str:
                    try:
                        bday = date.fromisoformat(bday_str)
                        user.birthday = bday
                        today = date.today()
                        user.age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
                    except ValueError:
                        user.age = int(request.POST.get('age', 18))
                else:
                    user.age = int(request.POST.get('age', 18))
                user.email = new_email
                user.address = request.POST.get('address')
                user.assignment_rel_id = request.POST.get('office_or_field')
                user.role_rel_id = request.POST.get('role')
                user.gender_id = request.POST.get('gender')
                
                # Only update password if user typed something new
                raw_password = request.POST.get('password')
                if raw_password and len(raw_password) > 0:
                    user.password = make_password(raw_password)
                    
                if request.FILES.get('profile_pic'): 
                    user.profile_pic = request.FILES.get('profile_pic')
                
                user.save()
                ActivityLog.objects.create(action=f"Employee '{user.employee_name}' {action_mode} (ID: {user.username}).")
                messages.success(request, f"Vault: {user.employee_name} {action_mode} successfully.")
            
            return redirect('user_list')

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

    # FIX: Seed generator for the next ID
    next_year_string = timezone.now().year
    prefix = f"GLI-{next_year_string}-"
    last_user = UserProfile.objects.filter(username__startswith=prefix).order_by('-username').first()
    next_num = (int(last_user.username.split('-')[-1]) + 1) if last_user else 1
    generated_id_seed = f"{prefix}{next_num:04d}"

    office_count = UserProfile.objects.filter(is_active=True, assignment_rel__badge_color="badge-office-hq").count()
    field_count  = UserProfile.objects.filter(is_active=True, assignment_rel__badge_color="badge-field-site").count()

    today      = timezone.now().date()
    week_ago   = timezone.now() - timedelta(days=7)
    month_ago  = timezone.now() - timedelta(days=30)
    active_qs  = UserProfile.objects.filter(is_active=True)
    added_today  = active_qs.filter(created_at__date=today).count()
    added_week   = active_qs.filter(created_at__gte=week_ago).count()
    added_month  = active_qs.filter(created_at__gte=month_ago).count()
    archived_count = UserProfile.objects.filter(is_active=False).count()
    role_stats   = [{'name': r.name, 'icon': r.icon or 'bi-briefcase-fill', 'color': r.color or '#3d7fff', 'count': active_qs.filter(role_rel=r).count()} for r in EmployeeRole.objects.all()]
    assign_stats = [{'name': a.name, 'icon': a.icon or 'bi-geo-alt-fill', 'badge': a.badge_color or 'badge-office-hq', 'count': active_qs.filter(assignment_rel=a).count()} for a in AssignmentLocation.objects.all()]


    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        table_html = render_to_string('user_table_partial.html', {'users': page_obj}, request=request)
        pagination_html = render_to_string('pagination_partial.html', {'users': page_obj, 'query': query, 'current_sort': sort, 'current_assignment': filter_assignment, 'current_role': filter_role}, request=request) if True else ''
        return JsonResponse({'html': table_html, 'pagination_html': pagination_html, 'total_count': page_obj.paginator.count})

    return render(request, 'user_list.html', {
        'users': page_obj,
        'archived_users': UserProfile.objects.filter(is_active=False),
        'genders':     Gender.objects.all(),
        'assignments': AssignmentLocation.objects.all(),
        'roles':       EmployeeRole.objects.all(),
        'recent_logs': ActivityLog.objects.all().order_by('-timestamp')[:4],
        'all_logs':    ActivityLog.objects.all().order_by('-timestamp'),
        'query': query,
        'current_sort': sort,
        'current_assignment': filter_assignment,
        'current_role':       filter_role,
        'total': active_qs.count(),
        'm_count': active_qs.filter(gender__gender__iexact='Male').count(),
        'f_count': active_qs.filter(gender__gender__iexact='Female').count(),
        'o_count': active_qs.exclude(gender__gender__iexact='Male').exclude(gender__gender__iexact='Female').count(),
        'office_count': office_count,
        'field_count':  field_count,
        'added_today':  added_today,
        'added_week':   added_week,
        'added_month':  added_month,
        'archived_count': archived_count,
        'role_stats':   role_stats,
        'assign_stats': assign_stats,
        'open_modal': request.GET.get('open_modal', ''),
        'next_id_generation': generated_id_seed
    })

# --- DEDICATED MAIN DASHBOARD BULK ACTION OPERATION ENGINE ---
@login_required(login_url='login')
def bulk_archive(request):
    if request.method == 'POST':
        user_ids = request.POST.getlist('selected_user_ids')
        if user_ids:
            UserProfile.objects.filter(id__in=user_ids).update(is_active=False)
            ActivityLog.objects.create(action=f"Bulk Engine: Coerced {len(user_ids)} employee records into system archive storage.")
            messages.success(request, f"Global Operations: Successfully archived {len(user_ids)} selected personnel profiles.")
    return redirect('user_list')

@login_required(login_url='login')
def delete_user(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    u.is_active = False
    u.save()
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' moved to system archive.")
    return redirect('/dashboard/')

@login_required(login_url='login')
def recover_user(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    u.is_active = True
    u.save()
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' restored to active files.")
    return redirect('/dashboard/?open_modal=archiveVaultModal')

@login_required(login_url='login')
def permanent_purge(request, pk):
    u = get_object_or_404(UserProfile, pk=pk)
    ActivityLog.objects.create(action=f"Employee Record '{u.employee_name}' permanently purged from core database.")
    u.delete()
    return redirect('/dashboard/?open_modal=archiveVaultModal')

@login_required(login_url='login')
def export_users_csv(request):
    query             = request.GET.get('q', '')
    filter_assignment = request.GET.get('assignment', '')
    filter_role       = request.GET.get('role', '')
    sort              = request.GET.get('sort', 'newest')
    export_type       = request.GET.get('export', 'csv')
    is_template       = request.GET.get('template', '') == '1'

    # ── CSV Template download
    if is_template:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="GLI_IMPORT_TEMPLATE.csv"'
        writer = csv.writer(response)
        writer.writerow(['employee_name', 'email', 'password', 'age', 'gender', 'address', 'assignment', 'role'])
        writer.writerow(['Juan Dela Cruz', 'juan@example.com', 'GLI@2025', '28', 'Male', '123 Main St, City', 'Creative Design Office', 'Social Media Manager'])
        writer.writerow(['Maria Santos', 'maria@example.com', 'GLI@2025', '24', 'Female', '456 Oak Ave, Town', 'Logistics Fulfillment Field', 'Administrator Developer'])
        return response

    # ── Build queryset with filters
    users = UserProfile.objects.filter(is_active=True)
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(employee_name__icontains=query) |
            Q(email__icontains=query) | Q(address__icontains=query) |
            Q(gender__gender__icontains=query) | Q(role_rel__name__icontains=query) |
            Q(assignment_rel__name__icontains=query)
        )
    if filter_assignment: users = users.filter(assignment_rel_id=filter_assignment)
    if filter_role:       users = users.filter(role_rel_id=filter_role)
    if sort == 'oldest':  users = users.order_by('id')
    elif sort == 'az':    users = users.order_by('employee_name')
    elif sort == 'za':    users = users.order_by('-employee_name')
    else:                 users = users.order_by('-id')

    label = 'FILTERED' if (query or filter_assignment or filter_role) else 'ALL'

    # ── PDF Export
    if export_type == 'pdf':
        from django.utils import timezone as tz
        now_str = tz.now().strftime('%B %d, %Y at %I:%M %p')
        rows_html = ''
        for i, u in enumerate(users, start=1):
            bg = 'rgba(61,127,255,0.04)' if i % 2 == 0 else 'transparent'
            rows_html += f'''<tr style="background:{bg};">
                <td style="padding:9px 12px;font-weight:700;color:#3d7fff;font-size:11px;font-family:monospace;">{u.username}</td>
                <td style="padding:9px 12px;font-weight:600;font-size:12px;">{u.employee_name}</td>
                <td style="padding:9px 12px;font-size:11px;color:#64748b;">{u.age}</td>
                <td style="padding:9px 12px;font-size:11px;">{u.gender.gender if u.gender else "—"}</td>
                <td style="padding:9px 12px;font-size:11px;color:#64748b;">{u.email}</td>
                <td style="padding:9px 12px;font-size:11px;">{u.assignment_rel.name if u.assignment_rel else "—"}</td>
                <td style="padding:9px 12px;font-size:11px;">{u.role_rel.name if u.role_rel else "—"}</td>
            </tr>'''

        html_content = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Plus Jakarta Sans',sans-serif; background:#f0f4ff; color:#0f172a; padding:32px; }}
  .header {{ background:linear-gradient(135deg,#0b1631,#1a4494,#3d7fff); border-radius:16px; padding:28px 32px; margin-bottom:28px; color:#fff; display:flex; justify-content:space-between; align-items:center; }}
  .header-title {{ font-size:22px; font-weight:800; letter-spacing:-0.5px; }}
  .header-sub {{ font-size:11px; opacity:0.7; margin-top:4px; }}
  .header-badge {{ background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.25); padding:6px 14px; border-radius:8px; font-size:11px; font-weight:700; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:24px; }}
  .stat-box {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:16px; text-align:center; }}
  .stat-num {{ font-size:28px; font-weight:800; color:#1a4494; }}
  .stat-lbl {{ font-size:9px; font-weight:700; color:#94a3b8; letter-spacing:1px; text-transform:uppercase; margin-top:4px; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:14px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.06); }}
  thead tr {{ background:linear-gradient(90deg,#0b1631,#1a4494); }}
  th {{ padding:11px 12px; text-align:left; font-size:9px; font-weight:800; letter-spacing:1.5px; text-transform:uppercase; color:rgba(255,255,255,0.8); }}
  td {{ border-bottom:1px solid #f1f5f9; }}
  .footer {{ margin-top:20px; text-align:center; font-size:10px; color:#94a3b8; }}
  .accent-bar {{ height:4px; background:linear-gradient(90deg,#3d7fff,#10b981,#c4b5fd); border-radius:99px; margin-bottom:20px; }}
  @media print {{ body {{ padding:16px; background:#fff; }} .header {{ -webkit-print-color-adjust:exact; print-color-adjust:exact; }} }}
</style></head><body>
<div class="accent-bar"></div>
<div class="header">
  <div>
    <div class="header-title">GLI Construction Services</div>
    <div class="header-sub">Employee Registry Export — {label} Records · {now_str}</div>
  </div>
  <div class="header-badge">GLI HR SYSTEM</div>
</div>
<div class="stats">
  <div class="stat-box"><div class="stat-num">{users.count()}</div><div class="stat-lbl">Total Exported</div></div>
  <div class="stat-box"><div class="stat-num">{users.filter(gender__gender__iexact="Male").count()}</div><div class="stat-lbl">Male</div></div>
  <div class="stat-box"><div class="stat-num">{users.filter(gender__gender__iexact="Female").count()}</div><div class="stat-lbl">Female</div></div>
  <div class="stat-box"><div class="stat-num">{UserProfile.objects.filter(is_active=False).count()}</div><div class="stat-lbl">Archived</div></div>
</div>
<table>
  <thead><tr><th>Employee ID</th><th>Full Name</th><th>Age</th><th>Gender</th><th>Email</th><th>Assignment</th><th>Role</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
<div class="footer">Generated by GLI HR System · {now_str} · Confidential — Internal Use Only</div>
</body></html>'''
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = f'inline; filename="GLI_EMPLOYEE_REPORT_{label}.html"'
        ActivityLog.objects.create(action=f"PDF Report: {users.count()} records exported ({label}).")
        return response

    # ── CSV Export (default)
    filename = f"GLI_EMPLOYEE_EXPORT_{label}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(['EMPLOYEE ID', 'FULL NAME', 'AGE', 'GENDER', 'EMAIL', 'ADDRESS', 'ASSIGNMENT', 'ROLE'])
    for u in users:
        writer.writerow([
            u.username, u.employee_name, u.age,
            u.gender.gender if u.gender else '',
            u.email, u.address,
            u.assignment_rel.name if u.assignment_rel else '',
            u.role_rel.name if u.role_rel else ''
        ])
    ActivityLog.objects.create(action=f"CSV Export: {users.count()} records exported ({label}).")
    return response

@login_required(login_url='login')
def bulk_archive_action(request):
    """Handles bulk restore or purge from the archive vault modal."""
    if request.method == 'POST':
        user_ids = request.POST.getlist('selected_users')
        action = request.POST.get('action_type', 'recover')
        if user_ids:
            if action == 'purge':
                UserProfile.objects.filter(id__in=user_ids).delete()
                ActivityLog.objects.create(action=f"Bulk Engine: Permanently purged {len(user_ids)} archived records.")
                messages.success(request, f"Purged {len(user_ids)} records permanently.")
            else:
                UserProfile.objects.filter(id__in=user_ids).update(is_active=True)
                ActivityLog.objects.create(action=f"Bulk Engine: Restored {len(user_ids)} archived records to active.")
                messages.success(request, f"Restored {len(user_ids)} personnel records.")
    return redirect('/dashboard/?open_modal=archiveVaultModal')

# ══ EMPLOYEE RECORD (QR Scan Target) ══
# No @login_required — any device on the same network can view after scanning
def employee_record(request, emp_id):
    employee = get_object_or_404(UserProfile, username=emp_id, is_active=True)
    return render(request, 'employee_record.html', {
        'employee': employee,
        'now': timezone.now(),
    })