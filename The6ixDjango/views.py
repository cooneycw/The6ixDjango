from django.shortcuts import render


def home(request):
    return render(request, 'The6ixDjango/home.html', {'title': 'The6ixDjango: Home'})


def about(request):
    return render(request, 'The6ixDjango/about.html', {'title': 'The6ixDjango: About'})
