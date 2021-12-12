from django.contrib import admin
from django.contrib.auth import get_user_model

from wwwdj import models

admin.site.register(get_user_model())
admin.site.register(models.Project)
admin.site.register(models.WorkSession)
admin.site.register(models.WorkDay)
admin.site.register(models.Record)
admin.site.register(models.WorkSummary)
