from django.urls import path
from clashstats import views

urlpatterns = [
    path('clashstats/menu/', views.clashstats, name='clashstats-menu'),
    path('clashstats/cards/', views.cards, name='clashstats-cards'),
    path('clashstats/segments/', views.segments, name='clashstats-segments'),
    path('clashstats/segment/<int:pk>/', views.segment, name='clashstats-segment'),
    path('clashstats/cardsegt/', views.cardsegt, name='clashstats-cardsegt'),
    path('clashstats/findsegt/', views.findsegt, name='clashstats-findsegt'),
    path('clashstats/segtrslt/<int:pk>/', views.segtrslt, name='clashstats-segtrslt'),
    path('clashstats/clanrept/', views.clanrept, name='clashstats-clanrept'),
    path('clashstats/membslct/', views.membslct, name='clashstats-membslct'),
    path('clashstats/membrept/', views.membrept, name='clashstats-membrept'),
    path('clashstats/win_deep/<int:pk>/', views.win_deep, name='clashstats-win_deep'),
    path('clashstats/win_deep/get_ajax/', views.retrieveAsync, name='clashstats-get_ajax'),
    ]