import datetime

from fpdf import FPDF, HTMLMixin

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.template.loader import render_to_string

from wwwdj import models


class HtmlPDF(FPDF, HTMLMixin):
    pass


# Service functions
#

def perform_session(session_number=None):
    current_date = datetime.date.today()
    if not session_number:
        try:
            session = models.WorkSession.objects.get(starting_date__lte=current_date, finish_date__gte=current_date)
        except models.WorkSession.DoesNotExist:
            try:
                latest_session = models.WorkSession.objects.latest("finish_date")
            except models.WorkSession.DoesNotExist:
                session = models.WorkSession.objects.create(
                    starting_date=current_date - datetime.timedelta(days=current_date.weekday()),
                    finish_date=(current_date - datetime.timedelta(days=current_date.weekday())) + datetime.timedelta(days=13)
                )
            else:
                session = models.WorkSession.objects.create(
                    starting_date=latest_session.finish_date + datetime.timedelta(days=1),
                    finish_date=latest_session.finish_date + datetime.timedelta(days=14)
                )
            session.save()
    else:
        session = models.WorkSession.objects.get(pk=session_number)
    return session


def get_work_timesheet(session, worker):
    workdays = [[], []]
    work_total_hours = 0
    work_total_earnings = 0
    for workday in session.workday_set.all().order_by("day_of_week"):
        records = models.Record.objects.filter(
            worker=worker,
            workday=workday,
        )
        total_hours = 0
        earnings = 0
        for record in records:
            if record.total_hours:
                total_hours += record.total_hours
                earnings += record.earnings
        workdays[session.starting_date.day + 7 <= workday.date.day if 1 else 0].append([workday, records, total_hours, earnings])
        work_total_hours += total_hours
        work_total_earnings += earnings
    return (workdays, work_total_hours, work_total_earnings)


# Views
#

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
    try:
        session = models.WorkSession.objects.get(starting_date__lte=current_date, finish_date__gte=current_date)
    except models.WorkSession.DoesNotExist:
        try:
            latest_session = models.WorkSession.objects.latest("finish_date")
        except models.WorkSession.DoesNotExist:
            session = models.WorkSession.objects.create(
                starting_date=current_date - datetime.timedelta(days=current_date.weekday()),
                finish_date=(current_date - datetime.timedelta(days=current_date.weekday())) + datetime.timedelta(days=13)
            )
        else:
            session = models.WorkSession.objects.create(
                starting_date=latest_session.finish_date + datetime.timedelta(days=1),
                finish_date=latest_session.finish_date + datetime.timedelta(days=14)
            )
        session.save()
    workdays, work_total_hours, work_total_earnings = get_work_timesheet(session, request.user)
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


@login_required
def staff_dashboard(request, session_number=None, worker_number=None):
    if request.user.is_staff:
        if worker_number:
            if session_number:
                return redirect("worker_timesheet", session_number, worker_number)
            else:
                return redirect("worker_timesheet", worker_number)
        else:
            if session_number:
                return redirect("totals", session_number)
            else:
                return redirect("totals")
    else:
        return redirect("dashboard")


@login_required
def totals(request, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        try:
            previous_session_number = models.WorkSession.objects.get(pk=session.pk - 1).pk
        except models.WorkSession.DoesNotExist:
            previous_session_number = None
        try:
            next_session_number = models.WorkSession.objects.get(pk=session.pk + 1).pk
        except models.WorkSession.DoesNotExist:
            next_session_number = None
        workers = get_user_model().objects.all()
        session_total_hours = 0
        session_total_earnings = 0
        work_records = []
        for worker in workers:
            work_total_hours = 0
            work_total_earnings = 0
            work_total_days = 0
            for workday in session.workday_set.all().order_by("day_of_week"):
                records = models.Record.objects.filter(
                    worker=worker,
                    workday=workday,
                )
                workday_worked = False
                for record in records:
                    if record.total_hours:
                        workday_worked = True
                        work_total_hours += record.total_hours
                        work_total_earnings += record.earnings
                if workday_worked:
                    work_total_days += 1
            work_records.append([worker, work_total_hours, work_total_earnings, work_total_days])
            session_total_hours += work_total_hours
            session_total_earnings += work_total_earnings
        return render(
            request,
            "pages/staff/totals.html",
            {
                "session": session,
                "previous_session_number": previous_session_number,
                "next_session_number": next_session_number,
                "workers": workers,
                "work_records": work_records,
                "session_total_hours": session_total_hours,
                "session_total_earnings": session_total_earnings,
            }
        )
    else:
        return redirect("dashboard")


@login_required
def worker_timesheet(request, worker_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        try:
            previous_session_number = models.WorkSession.objects.get(pk=session.pk - 1).pk
        except models.WorkSession.DoesNotExist:
            previous_session_number = None
        try:
            next_session_number = models.WorkSession.objects.get(pk=session.pk + 1).pk
        except models.WorkSession.DoesNotExist:
            next_session_number = None
        workers = get_user_model().objects.all()
        current_worker = get_user_model().objects.get(pk=worker_number)
        workdays, work_total_hours, work_total_earnings = get_work_timesheet(session, current_worker)
        return render(
            request,
            "pages/staff/worker_timesheet.html",
            {
                "session": session,
                "previous_session_number": previous_session_number,
                "next_session_number": next_session_number,
                "workers": workers,
                "current_worker": current_worker,
                "workdays": workdays,
                "total_hours": work_total_hours,
                "total_earnings": work_total_earnings,
            }
        )
    else:
        return redirect("dashboard")


@login_required
def sign_invoice(request, session_number):
    if request.user.is_staff:
        session = perform_session(session_number)
        pdf = HtmlPDF()
        pdf.add_page()
        pdf.write_html(render_to_string("pdf/invoice.html"))
        filename = f"Invoice_{session.pk}.pdf"
        filepath = f"media/{filename}"
        pdf.output(name=filepath, dest="F")
        session.invoice = filepath
        session.closed = True
        session.save()
        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
    else:
        return redirect("dashboard")


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
