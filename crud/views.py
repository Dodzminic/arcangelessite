from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .models import UserProfile, Gender
from .forms import UserForm, GenderForm

def user_list(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-id') 
    
    # Sidebar Logic
    genders = Gender.objects.all()
    gender_form = GenderForm()

    if request.method == "POST" and 'add_gender' in request.POST:
        form = GenderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'New gender added!')
            return redirect('user_list')

    if request.method == "POST" and 'delete_gender' in request.POST:
        gender_id = request.POST.get('gender_id')
        gender = get_object_or_404(Gender, id=gender_id)
        try:
            gender.delete()
            messages.warning(request, 'Gender removed.')
        except:
            messages.error(request, 'Cannot delete: assigned to students.')
        return redirect('user_list')

    # Filtering & Sorting
    users = UserProfile.objects.filter(username__icontains=query)
    if sort_by == 'name_asc': users = users.order_by('username')
    elif sort_by == 'name_desc': users = users.order_by('-username')
    elif sort_by == 'oldest': users = users.order_by('id')
    else: users = users.order_by('-id')

    paginator = Paginator(users, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'user_list.html', {
        'page_obj': page_obj, 'query': query, 'sort_by': sort_by,
        'total_users': users.count(), 'genders': genders, 'gender_form': gender_form
    })

def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # user.password = form.cleaned_data['password'] # For demo purposes
            user.save()
            messages.success(request, 'Student added successfully!')
            return redirect('user_list')
    else:
        form = UserForm()
    return render(request, 'form.html', {'form': form, 'title': 'Add New Student'})

def edit_user(request, pk):
    user = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('user_list')
    else:
        form = UserForm(instance=user)
    return render(request, 'form.html', {'form': form, 'title': 'Edit Student'})

def delete_user(request, pk):
    get_object_or_404(UserProfile, pk=pk).delete()
    messages.error(request, 'Student deleted.')
    return redirect('user_list')