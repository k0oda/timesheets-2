import datetime

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from wwwdj import models


def index(request):
    return redirect("dashboard")


@login_required
def start_work(request):
    current_datetime = datetime.datetime.today()
    session = models.WorkSession.objects.get(starting_date__lte=current_datetime.date(), finish_date__gte=current_datetime.date())
    workday = models.WorkDay.objects.filter(date=current_datetime.date())
    if workday:
        workday = workday[0]
    else:
        workday = models.WorkDay.objects.create(
            day_of_week=current_datetime.weekday(),
            date=current_datetime.date(),
            session=session,
        )
        workday.save()
    record = models.Record.objects.create(
        worker=request.user,
        workday=workday,
        start_time=current_datetime.time(),
    )
    record.save()
    return redirect("dashboard")


@login_required
def stop_work(request, record_id):
    current_datetime = datetime.datetime.today()
    record = models.Record.objects.get(
        id=record_id,
        worker=request.user,
    )
    record.finish_time = current_datetime.time()
    record.total_hours = current_datetime.time().hour - record.start_time.hour
    record.earnings = record.total_hours * record.worker.hour_rate
    record.stopped = True
    record.save()
    return redirect("dashboard")


@login_required
def delete_work(request, record_id):
    record = models.Record.objects.get(
        id=record_id,
        worker=request.user,
    )
    record.delete()
    return redirect("dashboard")


@login_required
def dashboard(request):
    current_date = datetime.date.today()
    session = models.WorkSession.objects.get(starting_date__lte=current_date, finish_date__gte=current_date)
    workdays = [[], []]
    work_total_hours = 0
    work_total_earnings = 0
    for workday in session.workday_set.all().order_by("day_of_week"):
        records = models.Record.objects.filter(
            worker=request.user,
            workday=workday,
        )
        total_hours = 0
        earnings = 0
        for record in records:
            if record.total_hours:
                total_hours += record.total_hours
                earnings += record.earnings
        summaries = models.WorkSummary.objects.filter(
            record__in=records
        )
        workdays[session.starting_date.day + 7 <= workday.date.day if 1 else 0].append([workday, records, total_hours, earnings, summaries])
        work_total_hours += total_hours
        work_total_earnings += earnings
    return render(
        request,
        "pages/dashboard.html",
        {
            "session": session,
            "workdays": workdays,
            "total_hours": work_total_hours,
            "total_earnings": work_total_earnings,
        }
    )


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("index")
    if request.method == "POST":
        user = authenticate(
            email=request.POST.get("email"),
            password=request.POST.get("password")
        )
        if user is not None:
            login(request, user)
            return redirect("index")
    return render(
        request,
        "pages/sign_in.html",
        {}
    )


def sign_out(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("index")