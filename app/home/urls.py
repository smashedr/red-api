from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home_view, name='index'),
    path('contact/', views.contact_view, name='contact'),
    path('verify/', views.verify_view, name='verify'),
]
