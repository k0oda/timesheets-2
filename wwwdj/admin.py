from django.contrib import admin
from django.contrib.auth import get_user_model

from wwwdj import models


class WorkSessionAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return ("starting_date", "finish_date")


class WorkDayAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return ("date", "day_of_week")


class RecordAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return ("worker", "workday", "project", "total_hours", "earnings")

admin.site.register(get_user_model())
admin.site.register(models.Project)
admin.site.register(models.WorkSession, WorkSessionAdmin)
admin.site.register(models.WorkDay, WorkDayAdmin)
admin.site.register(models.Record, RecordAdmin)
admin.site.register(models.ProjectInvoice)
