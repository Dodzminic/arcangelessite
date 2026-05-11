from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import UserProfile, Gender # Make sure Gender is imported
from .forms import UserForm

def user_list(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-id') 
    users = UserProfile.objects.filter(username__icontains=query)

    if sort_by == 'name_asc':
        users = users.order_by('username')
    elif sort_by == 'name_desc':
        users = users.order_by('-username')
    elif sort_by == 'oldest':
        users = users.order_by('id')
    else:
        users = users.order_by('-id')

    paginator = Paginator(users, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'user_list.html', {
        'page_obj': page_obj, 
        'query': query, 
        'sort_by': sort_by,
        'total_users': users.count() 
    })

# THIS IS THE MISSING FUNCTION CAUSING YOUR ERROR
def add_user(request):
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = UserForm()
    return render(request, 'form.html', {'form': form, 'title': 'Add New User'})

def edit_user(request, pk):
    user = get_object_or_404(UserProfile, pk=pk)
    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        form = UserForm(instance=user)
    return render(request, 'form.html', {'form': form, 'title': 'Edit User'})

def delete_user(request, pk):
    user = get_object_or_404(UserProfile, pk=pk)
    user.delete()
    return redirect('user_list')