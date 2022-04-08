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
    path("user_settings/", views.user_settings, name="user_settings"),
    path("sign_in/", views.sign_in, name="sign_in"),
    path("sign_out/", views.sign_out, name="sign_out"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("start_work/", views.start_work, name="start_work"),
    path("stop_work/<int:record_id>/", views.stop_work, name="stop_work"),
    path("edit_record/<int:record_id>/", views.edit_record, name="edit_record"),
    path("delete_work/<int:record_id>/", views.delete_work, name="delete_work"),

    # Staff
    path("dashboard/staff/", views.staff_dashboard, name="staff_dashboard"),
    path("dashboard/staff/<int:session_number>/", views.staff_dashboard, name="staff_dashboard"),
    path("dashboard/staff/<int:session_number>/<int:worker_number>/", views.staff_dashboard, name="staff_dashboard"),
    path("dashboard/staff/totals/", views.totals, name="totals"),
    path("dashboard/staff/totals/<int:session_number>/", views.totals, name="totals"),

    # Projects Management
    path("dashboard/staff/projects/", views.projects, name="projects"),
    path("dashboard/staff/projects/<int:session_number>/", views.projects, name="projects"),
    path("dashboard/staff/projects/add/", views.add_project, name="add_project"),
    path("dashboard/staff/projects/<int:session_number>/add/", views.add_project, name="add_project"),
    path("dashboard/staff/projects/edit/<int:project_number>/", views.edit_project, name="edit_project"),
    path("dashboard/staff/projects/<int:session_number>/edit/<int:project_number>/", views.edit_project, name="edit_project"),
    path("dashboard/staff/projects/delete/<int:project_number>/", views.delete_project, name="delete_project"),
    path("dashboard/staff/projects/<int:session_number>/delete/<int:project_number>/", views.delete_project, name="delete_project"),
    path("dashboard/staff/projects/<int:project_number>/rates/add/", views.add_personal_rate, name="add_personal_rate"),
    path("dashboard/staff/projects/<int:session_number>/<int:project_number>/rates/add/", views.add_personal_rate, name="add_personal_rate"),
    path("dashboard/staff/projects/<int:project_number>/rates/edit/<int:rate_number>/", views.edit_personal_rate, name="edit_personal_rate"),
    path("dashboard/staff/projects/<int:session_number>/<int:project_number>/rates/edit/<int:rate_number>/", views.edit_personal_rate, name="edit_personal_rate"),
    path("dashboard/staff/projects/<int:project_number>/rates/delete/<int:rate_number>/", views.delete_personal_rate, name="delete_personal_rate"),
    path("dashboard/staff/projects/<int:session_number>/<int:project_number>/rates/delete/<int:rate_number>/", views.delete_personal_rate, name="delete_personal_rate"),

    # Workers Management
    path("dashboard/staff/worker/<int:worker_number>/", views.worker_timesheet, name="worker_timesheet"),
    path("dashboard/staff/worker/<int:session_number>/<int:worker_number>/", views.worker_timesheet, name="worker_timesheet"),
    path("dashboard/staff/worker/<int:worker_number>/edit/", views.edit_worker, name="edit_worker"),
    path("dashboard/staff/worker/<int:session_number>/<int:worker_number>/edit/", views.edit_worker, name="edit_worker"),
    path("dashboard/staff/worker/<int:worker_number>/delete/", views.delete_worker, name="delete_worker"),
    path("dashboard/staff/worker/<int:session_number>/<int:worker_number>/delete/", views.delete_worker, name="delete_worker"),
    path("dashboard/staff/add_worker/", views.add_worker, name="add_worker"),
    path("dashboard/staff/add_worker/<int:session_number>/", views.add_worker, name="add_worker"),

    # Invoices
    path("dashboard/staff/sign_invoice/<int:session_number>/<int:project_number>/", views.sign_invoice, name="sign_invoice"),
    path("dashboard/staff/invoice/<int:session_number>/<int:project_number>/", views.download_invoice, name="download_invoice"),
]
