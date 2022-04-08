from django.contrib import admin
from django.contrib.auth import get_user_model
from django import forms

from wwwdj import models


class CustomWorkDayChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.get_day_of_week_display()} {obj.date}"


class RecordAdminForm(forms.ModelForm):
    workday = CustomWorkDayChoiceField(queryset=models.WorkDay.objects.all())
    class Meta:
        model = models.Record
        fields = "__all__"


class WorkSessionAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return ("starting_date", "finish_date")


class WorkDayAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        return ("date", "day_of_week")


class RecordAdmin(admin.ModelAdmin):
    form = RecordAdminForm
    list_display = ("worker", "get_workday", "project", "total_hours", "payable_earnings", "billable_earnings")

    @admin.display(ordering="-date", description="Workday")
    def get_workday(self, obj):
        return f"{obj.workday.get_day_of_week_display()} {obj.workday.date}"

admin.site.register(get_user_model())
admin.site.register(models.Project)
admin.site.register(models.WorkSession, WorkSessionAdmin)
admin.site.register(models.WorkDay, WorkDayAdmin)
admin.site.register(models.Record, RecordAdmin)
admin.site.register(models.ProjectInvoice)
admin.site.register(models.PersonalRate)
