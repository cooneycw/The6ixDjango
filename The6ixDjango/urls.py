from django.urls import path
from The6ixDjango import views

urlpatterns = [
    path('', views.home, name='The6ixDjango-home'),

]