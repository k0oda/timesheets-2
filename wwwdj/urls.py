"""wwwdj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from wwwdj import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    
    # Auth
    path("sign_in/", views.sign_in, name="sign_in"),
    path("sign_out/", views.sign_out, name="sign_out"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("start_work/", views.start_work, name="start_work"),
    path("stop_work/<int:record_id>/", views.stop_work, name="stop_work"),
    path("delete_work/<int:record_id>/", views.delete_work, name="delete_work"),
]
