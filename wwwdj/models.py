from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models.query_utils import select_related_descend

from wwwdj import model_choices as choices


class User(AbstractUser):
    email = models.EmailField(unique=True)
    hour_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "password"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    hour_rate_increase = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return self.name


class WorkSession(models.Model):
    starting_date = models.DateField(unique=True)
    finish_date = models.DateField(unique=True)
    closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.starting_date} - {self.finish_date}"


class WorkDay(models.Model):
    day_of_week = models.IntegerField(default=0, choices=choices.DAY_OF_WEEK)
    date = models.DateField(unique=True)
    session = models.ForeignKey(WorkSession, on_delete=models.CASCADE)

    def __str__(self):
        return self.get_day_of_week_display()


class Record(models.Model):
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    workday = models.ForeignKey(WorkDay, on_delete=models.CASCADE)
    start_time = models.TimeField()
    finish_time = models.TimeField(blank=True, null=True)
    total_hours = models.SmallIntegerField(blank=True, null=True)
    earnings = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    stopped = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.worker} - {self.workday} | {str(self.total_hours)}"


class WorkSummary(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    summary = models.TextField()

    def __str__(self):
        return f"{self.record.worker} - {self.project}"