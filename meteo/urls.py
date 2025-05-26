from django.conf.urls.static import static
from django.urls import path
from meteo import views

from django.contrib import admin  # Django admin module
from authentication.views import *  # Import views from the authentication app
from django.conf import settings   # Application settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns  # Static files serving
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/home/", permanent=True)),
    path("home/", views.home, name="home"),
    path('admin_dashboard/', views.admin_page, name="admin_dash"),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('permission-denied/', views.permission_denied, name='permission_denied'),
    path('login/', views.login_page, name='login_page'),
    path('register/', views.register_page, name='register'),
    path("my_meteo/", views.my_meteo, name="my_meteo"),
    path("random_city/", views.random_city_view, name="random_city"),
    path("upload_city/", views.upload_city_view, name="upload_city"),
    path('search_city/', views.search_city, name='search_city')
]

# Serve media files if DEBUG is True (development mode)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve mystaticfiles files using staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()