from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home_view, name='index'),
    path('contact/', views.contact_view, name='contact'),
    path('flightaware/', views.fa_view, name='flightaware'),
    path('youtube/', views.yt_view, name='youtube'),
    path('verify/', views.verify_view, name='verify'),
    path('plotly/', views.plotly_view, name='plotly'),
    path('plotly/<str:pk>/', views.plotly_view, name='plotly_pk'),
]
