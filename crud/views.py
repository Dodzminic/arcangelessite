import csv
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from django.db.models import Q
from .models import UserProfile, Gender
from .forms import UserForm, GenderForm

# --- 1. EXPORT TO CSV ---
def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_directory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'Gender', 'Date Enrolled'])
    users = UserProfile.objects.filter(is_active=True).values_list('username', 'email', 'gender__gender', 'created_at')
    for user in users:
        writer.writerow(user)
    return response

# --- 2. MAIN DIRECTORY ---
def user_list(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-id')
    
    if request.method == "POST":
        if 'bulk_action' in request.POST:
            user_ids = request.POST.getlist('selected_users')
            if user_ids:
                UserProfile.objects.filter(id__in=user_ids).update(is_active=False)
                messages.warning(request, f"Archived {len(user_ids)} students.")
        
        elif 'add_gender' in request.POST:
            f = GenderForm(request.POST)
            if f.is_valid():
                f.save()
                messages.success(request, "Gender category added.")
        
        elif 'delete_gender' in request.POST:
            g_id = request.POST.get('gender_id')
            get_object_or_404(Gender, id=g_id).delete()
            messages.warning(request, "Gender category removed.")
        
        return redirect('user_list')

    users = UserProfile.objects.filter(Q(is_active=True) & (Q(username__icontains=query) | Q(email__icontains=query)))
    
    if sort_by == 'name_asc': users = users.order_by('username')
    elif sort_by == 'oldest': users = users.order_by('id')
    else: users = users.order_by('-id')

    paginator = Paginator(users, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'user_list.html', {
        'page_obj': page_obj, 'genders': Gender.objects.all(), 
        'gender_form': GenderForm(), 'total_users': users.count(), 
        'query': query, 'sort_by': sort_by
    })

# --- 3. UPDATED CRUD (FILES FIXED) ---
def add_user(request):
    if request.method == "POST":
        # request.FILES must be here for images to work!
        form = UserForm(request.POST, request.FILES) 
        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Student {user.username} enrolled successfully!')
            return redirect('user_list')
    else:
        form = UserForm()
    return render(request, 'form.html', {'form': form, 'title': 'New Enrollment'})

def edit_user(request, pk):
    user = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        # request.FILES must be here for images to work!
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            u = form.save(commit=False)
            if form.cleaned_data.get('password'):
                u.password = make_password(form.cleaned_data['password'])
            u.save()
            messages.success(request, 'Profile updated!')
            return redirect('user_list')
    else:
        form = UserForm(instance=user)
    return render(request, 'form.html', {'form': form, 'title': 'Edit Profile'})

def delete_user(request, pk):
    user = get_object_or_404(UserProfile, pk=pk)
    user.is_active = False
    user.save()
    messages.error(request, 'User archived.')
    return redirect('user_list')

def edit_gender(request, pk):
    gender = get_object_or_404(Gender, id=pk)
    if request.method == "POST":
        form = GenderForm(request.POST, instance=gender)
        if form.is_valid():
            form.save()
            messages.success(request, "Gender updated!")
            return redirect('user_list')
    return render(request, 'edit_gender.html', {'form': GenderForm(instance=gender)})