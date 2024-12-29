from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from members.forms import RegisterUserForm

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request,user)
            return redirect('stocks')
        else: 
            messages.success(request, 'There was an error loggging in. Try again')
            return redirect('user_login')
    else:
        return render(request, 'login.html', {})

def user_registration(request):
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, 'Registration Successful!')
            return redirect('home')
    else: 
        form = RegisterUserForm()
    return render(request, 'register_user.html', {'form':form})

def user_logout(request):
    logout(request)
    messages.success(request, 'You were successfully logged out.')
    return redirect('home')

