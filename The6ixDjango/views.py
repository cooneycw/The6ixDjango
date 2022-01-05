from django.shortcuts import render


def home(request):
    return render(request, 'The6ixDjango/home.html', {'title': 'The6ixClan: Home'})
