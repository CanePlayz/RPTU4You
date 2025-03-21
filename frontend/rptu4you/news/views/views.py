from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from ..forms import PreferencesForm, UserCreationForm


# Create your views here.
def News(request):
    return render(request, "news/News.html")



def Links(request):
    return render(request, "news/Links.html")


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('ForYouPage')
        else:
            messages.error(request, 'Ungültige Anmeldedaten.')
    return render(request, 'news/login.html')

def logout_view(request):
    logout(request)
    return redirect('News')

def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registrierung erfolgreich! Bitte melde dich an.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'news/register.html', {'form': form})


def ForYouPage(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Die For You-Seite ist nur mit Anmeldung einsehbar.')
        return redirect('login')
    else:
        return render(request, "news/ForYouPage.html")

def update_preferences(request):
    if request.method == 'POST':
        form = PreferencesForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('ForYouPage')
    else:
        form = PreferencesForm(instance=request.user)
    return render(request, 'news/preferences.html', {'form': form})    return render(request, 'news/preferences.html', {'form': form})
