import datetime

from weasyprint import HTML, CSS

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from wwwdj import models


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
                if latest_session.closed:
                    raise models.WorkSession.DoesNotExist
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


def get_project_work(session_number, project_number):
    session = models.WorkSession.objects.get(pk=session_number)
    project = models.Project.objects.get(pk=project_number)
    workers = get_user_model().objects.all()
    work_records = {
        "meta": {
            "total_hours": 0,
            "total_payable_earnings": 0,
            "total_billable_earnings": 0,
        },
        "records": [],
    }
    for worker in workers:
        work_total_hours = 0
        work_total_payable_earnings = 0
        work_total_billable_earnings = 0
        work_total_days = 0
        for workday in session.workday_set.all().order_by("day_of_week"):
            records = models.Record.objects.filter(
                worker=worker,
                workday=workday,
                project=project,
            )
            workday_worked = False
            for record in records:
                if record.total_hours:
                    workday_worked = True
                    work_total_hours += record.total_hours
                    work_total_payable_earnings += record.payable_earnings
                    work_total_billable_earnings += record.billable_earnings
            if workday_worked:
                work_total_days += 1
        if work_total_days == 0:
            continue
        work_record = [worker, work_total_hours, work_total_payable_earnings, work_total_billable_earnings, work_total_days]
        work_records["meta"]["total_hours"] += work_total_hours
        work_records["meta"]["total_payable_earnings"] += work_total_payable_earnings
        work_records["meta"]["total_billable_earnings"] += work_total_billable_earnings
        work_records["records"].append(work_record)
    return work_records


def get_work_timesheet(session, worker):
    workdays = [[], []]
    work_total_hours = 0
    work_total_payable_earnings = 0
    work_total_billable_earnings = 0
    for workday in session.workday_set.all().order_by("day_of_week"):
        records = models.Record.objects.filter(
            worker=worker,
            workday=workday,
        )
        hours = 0
        payable_earnings = 0
        billable_earnings = 0
        for record in records:
            if record.total_hours:
                hours += record.total_hours
                payable_earnings += record.payable_earnings
                billable_earnings += record.billable_earnings
        workdays[session.starting_date + datetime.timedelta(days=7) <= workday.date if 1 else 0].append([workday, records, hours, payable_earnings, billable_earnings])
        work_total_hours += hours
        work_total_payable_earnings += payable_earnings
        work_total_billable_earnings += billable_earnings
    return (workdays, work_total_hours, work_total_payable_earnings, work_total_billable_earnings)


# AJAX views
#

def get_worker(request):
    if request.is_ajax:
        data = {}
        worker_number = request.GET.get("number")
        try:
            worker = models.User.objects.get(pk=worker_number)
        except models.User.DoesNotExist:
            data["status"] = "ERR"
        else:
            data = {
                "status": "OK",
                "username": worker.username,
                "first_name": worker.first_name,
                "last_name": worker.last_name,
                "email": worker.email,
                "payable_hour_rate": worker.payable_hour_rate,
            }
        return JsonResponse(data)
    else:
        return HttpResponseBadRequest()


# Worker-faced views
#

def index(request):
    return redirect("dashboard")


@login_required
def start_work(request):
    if request.method == "POST":
        current_datetime = timezone.now()
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
        project = models.Project.objects.get(pk=request.POST.get("project"))
        record = models.Record.objects.create(
            worker=request.user,
            project=project,
            workday=workday,
            start_time=current_datetime,
        )
        record.save()
    return redirect("dashboard")


@login_required
def stop_work(request, record_id):
    if request.method == "POST":
        current_datetime = timezone.now()
        record = models.Record.objects.get(
            id=record_id,
            worker=request.user,
        )
        record.finish_time = current_datetime
        total_seconds = (current_datetime - record.start_time).total_seconds()
        total_minutes = (total_seconds // 60) % 60
        total_hours = total_seconds // 3600
        if total_minutes > 45:
            total_hours += 1
        elif total_minutes > 8 and total_minutes <= 45:
            total_hours += 0.5
        record.total_hours = total_hours
        try:
            rate = models.PersonalRate.objects.get(
                project=record.project,
                worker=request.user,
            )
        except models.PersonalRate.DoesNotExist:
            record.payable_earnings = record.total_hours * float(record.worker.payable_hour_rate)
            record.billable_earnings = record.total_hours * float(record.project.billable_rate)
        else:
            record.payable_earnings = record.total_hours * float(rate.payable_rate)
            record.billable_earnings = record.total_hours * float(rate.billable_rate)
        summary = request.POST.get("summary")
        record.summary = summary
        record.stopped = True
        record.save()
    return redirect("dashboard")


@login_required
def edit_record(request, record_id):
    if request.method == "POST":
        record = models.Record.objects.get(
            id=record_id,
            worker=request.user,
        )
        record.project = models.Project.objects.get(pk=request.POST.get("project"))
        record.summary = request.POST.get("summary")
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
    current_date = timezone.now()
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
    projects = models.Project.objects.all()
    workdays, work_total_hours, work_total_payable_earnings, work_total_billable_earnings = get_work_timesheet(session, request.user)
    return render(
        request,
        "pages/dashboard.html",
        {
            "session": session,
            "projects": projects,
            "workdays": workdays,
            "total_hours": work_total_hours,
            "total_payable_earnings": work_total_payable_earnings,
            "total_billable_earnings": work_total_billable_earnings,
        }
    )


# Staff panel
#

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
        projects = models.Project.objects.all()
        workers = get_user_model().objects.all()
        session_total_hours = 0
        session_total_payable_earnings = 0
        session_total_billable_earnings = 0
        work_records = {}
        for project in projects:
            project_work = get_project_work(session.pk, project.pk)
            work_records[project] = project_work
            session_total_hours += project_work["meta"]["total_hours"]
            session_total_payable_earnings += project_work["meta"]["total_payable_earnings"]
            session_total_billable_earnings += project_work["meta"]["total_billable_earnings"]
        return render(
            request,
            "pages/staff/totals.html",
            {
                "session": session,
                "projects": projects,
                "previous_session_number": previous_session_number,
                "next_session_number": next_session_number,
                "workers": workers,
                "work_records": work_records,
                "session_total_hours": session_total_hours,
                "session_total_payable_earnings": session_total_payable_earnings,
                "session_total_billable_earnings": session_total_billable_earnings,
            }
        )
    else:
        return redirect("dashboard")


@login_required
def projects(request, session_number=None):
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
        projects = {}
        for project in models.Project.objects.all():
            new_personal_rates_workers = []
            for worker in workers:
                try:
                    models.PersonalRate.objects.get(
                        project=project,
                        worker=worker
                    )
                except models.PersonalRate.DoesNotExist:
                    new_personal_rates_workers.append(worker)
            projects[project] = new_personal_rates_workers
        return render(
            request,
            "pages/staff/projects.html",
            {
                "session": session,
                "previous_session_number": previous_session_number,
                "next_session_number": next_session_number,
                "workers": workers,
                "projects": projects,
            }
        )
    else:
        return redirect("dashboard")


@login_required
def add_project(request, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            project = models.Project.objects.create(
                name = request.POST.get("name"),
                client_name = request.POST.get("client_name"),
                description = request.POST.get("description"),
                billable_rate = request.POST.get("billable_rate"),
            )
            project.save()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def edit_project(request, project_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            project = models.Project.objects.get(pk=project_number)
            project.name = request.POST.get("name")
            project.client_name = request.POST.get("client_name")
            project.description = request.POST.get("description")
            project.billable_rate = request.POST.get("billable_rate")
            project.save()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def delete_project(request, project_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        models.Project.objects.get(pk=project_number).delete()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def add_personal_rate(request, project_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            project = models.Project.objects.get(pk=project_number)
            worker = get_user_model().objects.get(pk=request.POST.get("worker"))
            rate = models.PersonalRate.objects.create(
                worker = worker,
                project = project,
                payable_rate = request.POST.get("payable_rate"),
                billable_rate = request.POST.get("billable_rate"),
            )
            rate.save()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def recalculate_project_records(request, project_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        project = models.Project.objects.get(pk=project_number)
        records = models.Record.objects.filter(project=project)
        for record in records:
            record_session = record.workday.session
            try:
                models.ProjectInvoice.objects.get(
                    session=record_session,
                    project=project,
                )
            except models.ProjectInvoice.DoesNotExist:
                if record.total_hours and record.start_time:
                    try:
                        rate = models.PersonalRate.objects.get(
                            project=record.project,
                            worker=record.worker,
                        )
                    except models.PersonalRate.DoesNotExist:
                        record.payable_earnings = record.total_hours * record.worker.payable_hour_rate
                        record.billable_earnings = record.total_hours * record.project.billable_rate
                    else:
                        record.payable_earnings = record.total_hours * rate.payable_rate
                        record.billable_earnings = record.total_hours * rate.billable_rate
                    record.save()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def edit_personal_rate(request, project_number, rate_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            project = models.Project.objects.get(pk=project_number)
            rate = models.PersonalRate.objects.get(pk=rate_number, project=project)
            rate.payable_rate = request.POST.get("payable_rate")
            rate.billable_rate = request.POST.get("billable_rate")
            rate.save()
        return redirect("projects", session_number=session.pk)
    else:
        return redirect("dashboard")


@login_required
def delete_personal_rate(request, project_number, rate_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        project = models.Project.objects.get(pk=project_number)
        models.PersonalRate.objects.get(pk=rate_number, project=project).delete()
        return redirect("projects", session_number=session.pk)
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
        projects = models.Project.objects.all()
        workers = get_user_model().objects.all()
        current_worker = get_user_model().objects.get(pk=worker_number)
        workdays, work_total_hours, work_total_payable_earnings, work_total_billable_earnings = get_work_timesheet(session, current_worker)
        return render(
            request,
            "pages/staff/worker_timesheet.html",
            {
                "session": session,
                "projects": projects,
                "previous_session_number": previous_session_number,
                "next_session_number": next_session_number,
                "workers": workers,
                "current_worker": current_worker,
                "workdays": workdays,
                "total_hours": work_total_hours,
                "total_payable_earnings": work_total_payable_earnings,
                "total_billable_earnings": work_total_billable_earnings,
            }
        )
    else:
        return redirect("dashboard")


@login_required
def add_worker(request, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            is_staff = False
            if "is_staff" in request.POST:
                is_staff = True
            worker = get_user_model().objects.create_user(
                username=request.POST.get('username'),
                email=request.POST.get('email'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                payable_hour_rate=request.POST.get('payable_hour_rate'),
                password=request.POST.get('password'),
                is_staff=is_staff,
            )
            worker.save()
        return redirect("staff_dashboard", session.pk)
    else:
        return redirect("dashboard")


@login_required
def edit_worker(request, worker_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        if request.method == "POST":
            is_staff = False
            if "is_staff" in request.POST:
                is_staff = True
            worker = get_user_model().objects.get(pk=worker_number)
            worker.username=request.POST.get('username')
            worker.email=request.POST.get('email')
            worker.first_name=request.POST.get('first_name')
            worker.last_name=request.POST.get('last_name')
            worker.payable_hour_rate=request.POST.get('payable_hour_rate')
            worker.is_staff=is_staff
            worker.save()
        return redirect("worker_timesheet", session.pk, worker_number)
    else:
        return redirect("dashboard")


@login_required
def recalculate_worker_records(request, worker_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        worker = models.User.objects.get(pk=worker_number)
        records = models.Record.objects.filter(worker=worker)
        for record in records:
            record_session = record.workday.session
            try:
                models.ProjectInvoice.objects.get(
                    session=record_session,
                    project=record.project,
                )
            except models.ProjectInvoice.DoesNotExist:
                if record.total_hours and record.start_time:
                    try:
                        rate = models.PersonalRate.objects.get(
                            project=record.project,
                            worker=worker,
                        )
                    except models.PersonalRate.DoesNotExist:
                        record.payable_earnings = record.total_hours * record.worker.payable_hour_rate
                        record.billable_earnings = record.total_hours * record.project.billable_rate
                    else:
                        record.payable_earnings = record.total_hours * rate.payable_rate
                        record.billable_earnings = record.total_hours * rate.billable_rate
                    record.save()
        return redirect("worker_timesheet", session_number=session.pk, worker_number=worker_number)
    else:
        return redirect("dashboard")


@login_required
def delete_worker(request, worker_number, session_number=None):
    if request.user.is_staff:
        session = perform_session(session_number)
        get_user_model().objects.get(pk=worker_number).delete()
        return redirect("staff_dashboard", session.pk)
    else:
        return redirect("dashboard")


@login_required
def sign_invoice(request, session_number, project_number):
    if request.user.is_staff:
        session = perform_session(session_number)
        project = models.Project.objects.get(pk=project_number)
        work_records = get_project_work(session.pk, project.pk)
        invoice = models.ProjectInvoice.objects.create(
            session=session,
            project=project,
            date=datetime.date.today(),
        )
        page = render_to_string(
            template_name="pdf/invoice.html",
            context={
                "session": session,
                "project": project,
                "invoice": invoice,
                "work_records": work_records,
            },
        )
        filename = f"Invoice_{invoice.pk}.pdf"
        filepath = f"{settings.MEDIA_ROOT}/{filename}"
        htmldoc = HTML(string=page)
        htmldoc.write_pdf(
            target=filepath,
            stylesheets=[CSS(
                string=
                """
                @page {
                    size: Letter;
                    margin: 0;
                }
                body {
                    display: block;
                    margin: 0;
                }
                """
            )]
        )
        invoice.invoice = filepath
        invoice.save()
        projects = models.Project.objects.all()
        try:
            for project in projects:
                models.ProjectInvoice.objects.get(session=session, project=project)
        except models.ProjectInvoice.DoesNotExist:
            pass
        else:
            session.closed = True
            session.save()
        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=filename)
    else:
        return redirect("dashboard")


@login_required
def download_invoice(request, session_number, project_number):
    if request.user.is_staff:
        session = perform_session(session_number)
        project = models.Project.objects.get(pk=project_number)
        invoice = models.ProjectInvoice.objects.get(session=session, project=project)
        return FileResponse(open(invoice.invoice.name, "rb"), as_attachment=True, filename=invoice.filename())
    else:
        return redirect("dashboard")


# Auth
#

def user_settings(request):
    user = request.user
    if request.method == "POST":
        user.username=request.POST.get('username')
        user.email=request.POST.get('email')
        user.first_name=request.POST.get('first_name')
        user.last_name=request.POST.get('last_name')
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        if user.check_password(old_password) and new_password:
            user.set_password(new_password)
        user.save()
        return redirect("dashboard")
    return render(
        request,
        "pages/user_settings.html",
        {
            "user": request.user,
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
