from django.urls import path
from clashstats import views

urlpatterns = [
    path('clashstats/menu/', views.clashstats, name='clashstats-menu'),
    path('clashstats/cards/', views.cards, name='clashstats-cards'),
]