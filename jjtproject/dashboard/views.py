# dashboard/views.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO
from types import SimpleNamespace
from typing import Any, Iterable, List, Optional, Tuple

from django.apps import apps
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db.models import Count, Min, Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils import timezone


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

def _is_admin(u):
    return u.is_authenticated and (u.is_staff or u.groups.filter(name="ClientAdmin").exists())

admin_only = user_passes_test(_is_admin, login_url="staff_login")


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def _attempt_model():
    """Your canonical attempt model (exams.ExamAttempt) if available."""
    try:
        return apps.get_model("exams", "ExamAttempt")
    except (LookupError, ImproperlyConfigured):
        return None

def _get_any(obj: Any, names: Iterable[str], default=""):
    """Return the first present attribute from names on obj."""
    if not obj:
        return default
    for n in names:
        if hasattr(obj, n):
            val = getattr(obj, n)
            if val not in (None, ""):
                return val
    return default

def _safe_dt(obj, names):
    """Return the first datetime-like attr in names (or None)."""
    val = _get_any(obj, names, None)
    return val  # allow both date and datetime; template will handle formatting

def _exam_display(exam_obj):
    """Best-effort human name for an Exam object."""
    if not exam_obj:
        return "-"
    for attr in ("name", "title", "exam_title", "label", "code"):
        val = getattr(exam_obj, attr, None)
        if val:
            return val
    return str(exam_obj)


# ---------------------------------------------------------------------------
# Date ranges
# ---------------------------------------------------------------------------

def _range(label: str):
    now = timezone.localtime()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if label == "today":
        return start_today, now
    if label == "yesterday":
        return start_today - timedelta(days=1), start_today
    if label == "last7":
        return now - timedelta(days=7), now
    if label == "last30":
        return now - timedelta(days=30), now
    return None, None


# ---------------------------------------------------------------------------
# Fallback builder (when ExamAttempt is absent)
# ---------------------------------------------------------------------------

def _fallback_progress_queryset() -> List[SimpleNamespace]:
    """
    Build rows for dashboard/reports using your real Answer schema:
      - responses.Answer has fields: attempt, exam, examinee, question, created_at...
      - Group by attempt if present else by (examinee_id, exam_id)
      - Progress = answered_count / total_questions_for_exam * 100 (best-effort)
    Returns list of SimpleNamespace with attributes:
      started_at, progress, user/examinee, exam, id (stable), gender/position/level (best-effort)
    """
    Answer = apps.get_model("responses", "Answer")
    exam_field = Answer._meta.get_field("exam")
    examinee_field = Answer._meta.get_field("examinee")
    Exam = exam_field.remote_field.model
    Examinee = examinee_field.remote_field.model

    # Optional Question model for total count
    Question = None
    try:
        Question = apps.get_model("exams", "Question")
    except Exception:
        pass

    # Determine grouping
    has_attempt = False
    try:
        Answer._meta.get_field("attempt")
        has_attempt = True
        group_fields = ["attempt_id", "exam_id", "examinee_id"]
    except Exception:
        group_fields = ["examinee_id", "exam_id"]

    base = (
        Answer.objects
        .values(*group_fields)
        .annotate(answered=Count("id"), started_at=Min("created_at"))
        .order_by("-started_at")
    )

    # Prefetch people/exams
    ex_ids = {row["exam_id"] for row in base}
    pe_ids = {row["examinee_id"] for row in base}
    exams = {e.id: e for e in Exam.objects.filter(id__in=ex_ids)}
    people = {p.id: p for p in Examinee.objects.filter(id__in=pe_ids)}

    rows: List[SimpleNamespace] = []
    for row in base:
        exam = exams.get(row["exam_id"])
        examinee = people.get(row["examinee_id"])

        # Total questions
        if Question and exam:
            total_qs = Question.objects.filter(exam=exam).count()
        else:
            filt = {}
            for f in ("attempt_id", "examinee_id", "exam_id"):
                if f in row:
                    filt[f] = row[f]
            total_qs = (
                Answer.objects.filter(**filt)
                .values("question_id").distinct().count()
            )
        total_qs = max(total_qs, 1)

        progress = round((row["answered"] / total_qs) * 100, 0)
        stable_id = row["attempt_id"] if has_attempt else hash((row["examinee_id"], row["exam_id"]))
        started_at = row.get("started_at")

        rows.append(SimpleNamespace(
            id=stable_id,
            user=getattr(examinee, "user", examinee),  # if Examinee wraps auth.User
            examinee=examinee,
            person=None,
            exam=exam,
            started_at=started_at,
            completed_at=None if progress < 100 else timezone.now(),
            progress=float(progress),
            gender=getattr(examinee, "gender", "") or "",
            position=getattr(examinee, "position", "") or "",
            level=getattr(examinee, "level", "") or "",
            _pseudo=not has_attempt,
        ))
    return rows


# ===========================================================================
# DASHBOARD (HOME)
# ===========================================================================

def dashboard_home(request):
    """
    Minimal dashboard: 4 tiles (today, yesterday, last 7, last 30),
    counting UNIQUE examinees/users who have attempts in each range.
    The "View Details" buttons link to /clientadmin/reports/?quick=...
    """
    AttemptModel = _attempt_model()
    today = timezone.localtime()
    start_today = today.replace(hour=0, minute=0, second=0, microsecond=0)
    start_yesterday = start_today - timedelta(days=1)
    start_last7 = today - timedelta(days=7)
    start_last30 = today - timedelta(days=30)

    def _unique_people(qs):
        seen = set()
        for a in qs:
            if getattr(a, "user_id", None):
                key = ("u", a.user_id)
            elif getattr(a, "examinee_id", None):
                key = ("e", a.examinee_id)
            elif getattr(a, "person_id", None):
                key = ("p", a.person_id)
            else:
                key = ("anon", a.pk)
            seen.add(key)
        return len(seen)

    if AttemptModel:
        base = AttemptModel.objects.all()

        # if the model has a started_at or created_at field, use it
        date_field = "started_at"
        for f in ("started_at", "start_time", "created_at", "timestamp", "created"):
            try:
                AttemptModel._meta.get_field(f)
                date_field = f
                break
            except Exception:
                continue

        def f_between(start, end):
            return base.filter(**{f"{date_field}__gte": start, f"{date_field}__lt": end})

        count_today     = _unique_people(f_between(start_today, today))
        count_yesterday = _unique_people(f_between(start_yesterday, start_today))
        count_last7     = _unique_people(f_between(start_last7, today))
        count_last30    = _unique_people(f_between(start_last30, today))
    else:
        # Fallback (no ExamAttempt): best-effort using the rows builder you already have
        rows = _fallback_progress_queryset()

        def in_range(dt, start, end):
            return dt and start <= dt < end

        def uniq(start, end):
            seen = set()
            for r in rows:
                if in_range(r.started_at, start, end):
                    key = (getattr(r.user, "id", None)
                           or getattr(r.examinee, "id", None)
                           or ("anon", id(r)))
                    seen.add(key)
            return len(seen)

        count_today     = uniq(start_today, today)
        count_yesterday = uniq(start_yesterday, start_today)
        count_last7     = uniq(start_last7, today)
        count_last30    = uniq(start_last30, today)

    context = {
        "summary": {
            "today": count_today,
            "yesterday": count_yesterday,
            "last7": count_last7,
            "last30": count_last30,
        }
    }
    # render the simple tiles-only dashboard
    return render(request, "dashboard/dashboard_home.html", context)




# ===========================================================================
# REPORTS
# ===========================================================================

@admin_only
def reports(request):
    """Admin reports with filters, sorting, pagination, and single-user view."""
    AttemptModel = _attempt_model()

    # GET params
    position = request.GET.get("position", "").strip()
    level = request.GET.get("level", "").strip()
    gender = request.GET.get("gender", "").strip()
    progress_state = request.GET.get("progress", "").strip()  # completed/in_progress/"".
    quick = request.GET.get("quick", "").strip()
    date_start = request.GET.get("date_start", "").strip()
    date_end = request.GET.get("date_end", "").strip()
    search = request.GET.get("search", "").strip()
    examinee_param = request.GET.get("examinee")
    user_param = request.GET.get("user")
    show_latest = request.GET.get("latest") == "1"

    # Sorting
    SORT_MAP = {
        "started_at": "started_at",
        "completed_at": "completed_at",
        "fullname": "user__username",
        "gender": "gender",
        "position": "position",
        "level": "level",
        "progress": "progress",
    }
    sort = request.GET.get("sort") or "started_at"
    direction = request.GET.get("dir") or "desc"
    order_by = f"-{SORT_MAP.get(sort, 'started_at')}" if direction == "desc" else SORT_MAP.get(sort, "started_at")

    if AttemptModel:
        qs = AttemptModel.objects.all()
        rel_names = [f.name for f in AttemptModel._meta.fields if getattr(f, "is_relation", False)]
        if "user" in rel_names or "examinee" in rel_names or "exam" in rel_names:
            qs = qs.select_related(*(n for n in ("user", "examinee", "exam") if n in rel_names))

        # Filters
        if position:
            qs = qs.filter(Q(position__iexact=position) | Q(examinee__position__iexact=position))
        if level:
            qs = qs.filter(Q(level__iexact=level) | Q(examinee__level__iexact=level))
        if gender:
            qs = qs.filter(Q(gender__iexact=gender) | Q(examinee__gender__iexact=gender))

        if progress_state == "completed":
            qs = qs.filter(Q(progress__gte=100) | Q(status="completed"))
        elif progress_state == "in_progress":
            qs = qs.filter(Q(progress__lt=100) | Q(status="in_progress"))

        s, e = _range(quick) if quick else (None, None)
        if s and e:
            qs = qs.filter(started_at__gte=s, started_at__lt=e)
        else:
            if date_start:
                qs = qs.filter(started_at__date__gte=date_start)
            if date_end:
                qs = qs.filter(started_at__date__lte=date_end)

        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)  |
                Q(user__username__icontains=search)   |
                Q(examinee__first_name__icontains=search) |
                Q(examinee__last_name__icontains=search)  |
                Q(examinee__fullname__icontains=search)
            )

        if examinee_param and str(examinee_param).isdigit():
            qs = qs.filter(Q(examinee_id=int(examinee_param)) | Q(user_id=int(examinee_param)))
        elif user_param:
            qs = qs.filter(
                Q(user__username__icontains=user_param) |
                Q(user__first_name__icontains=user_param) |
                Q(user__last_name__icontains=user_param)  |
                Q(examinee__first_name__icontains=user_param) |
                Q(examinee__last_name__icontains=user_param)  |
                Q(examinee__fullname__icontains=user_param)
            )

        qs = qs.order_by(order_by)
        per_page = 1 if (show_latest and (examinee_param or user_param)) else 50
        paginator = Paginator(qs, per_page)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        
        return render(request, "dashboard/reports.html", {
            "page_obj": page_obj,
            "attempt_model_exists": True,
            "filters": {
                "position": position, "level": level, "gender": gender,
                "progress": progress_state, "quick": quick,
                "date_start": date_start, "date_end": date_end, "search": search,
            },
        })

    # ---- Fallback list (best-effort) – build rows from Answer
    rows = _fallback_progress_queryset()

    # Filter in Python for fallback
    def _row_ok(r):
        ok = True
        if position and (getattr(r, "position", "") or "").lower() != position.lower(): ok = False
        if level and (getattr(r, "level", "") or "").lower() != level.lower(): ok = False
        if gender and (getattr(r, "gender", "") or "").lower() != gender.lower(): ok = False
        if progress_state == "completed" and (r.progress or 0) < 100: ok = False
        if progress_state == "in_progress" and (r.progress or 0) >= 100: ok = False
        if search:
            u = r.user
            name = f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}".strip() or getattr(u, "username", "")
            if search.lower() not in (name or "").lower(): ok = False
        if examinee_param and str(getattr(r.examinee, "id", "")) != str(examinee_param): ok = False
        if user_param:
            u = r.user
            name = f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}".strip() or getattr(u, "username", "")
            if user_param.lower() not in (name or "").lower(): ok = False
        if quick:
            s, e = _range(quick)
            dt = r.started_at
            if s and e and not (dt and s <= dt < e): ok = False
        else:
            if date_start:
                dt = r.started_at
                if not (dt and dt.date() >= timezone.datetime.fromisoformat(date_start).date()): ok = False
            if date_end:
                dt = r.started_at
                if not (dt and dt.date() <= timezone.datetime.fromisoformat(date_end).date()): ok = False
        return ok

    filtered = [r for r in rows if _row_ok(r)]

    # Sorting (fallback)
    reverse = (direction == "desc")
    if sort == "fullname":
        def key_fn(r):
            u = r.user
            return (f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}".strip() or getattr(u, "username", "")).lower()
    else:
        key_fn = lambda r: getattr(r, sort, None)
    filtered.sort(key=key_fn, reverse=reverse)

    if show_latest and (examinee_param or user_param):
        filtered = filtered[:1]

    # Manual pagination
    per_page = 1 if (show_latest and (examinee_param or user_param)) else 50
    page = int(request.GET.get("page", 1))
    start = (page - 1) * per_page
    items = filtered[start:start + per_page]

    class SimplePage:
        object_list = items
        number = page
        has_previous = page > 1
        has_next = len(filtered) > start + per_page
        def previous_page_number(self): return self.number - 1
        def next_page_number(self): return self.number + 1

    page_obj = SimplePage()
    # in reports()
    return render(request, "dashboard/reports.html", {
        "page_obj": page_obj,
        "attempt_model_exists": False,
        "filters": {
            "position": position, "level": level, "gender": gender,
            "progress": progress_state, "quick": quick,
            "date_start": date_start, "date_end": date_end, "search": search,
        },
    })


# ===========================================================================
# EXPORTS & ACTIONS
# ===========================================================================

@admin_only
def reports_export_csv(request):
    """
    Export the same filters as `reports` in CSV.
    """
    AttemptModel = _attempt_model()

    # Collect params
    position = request.GET.get("position", "").strip()
    level = request.GET.get("level", "").strip()
    gender = request.GET.get("gender", "").strip()
    progress_state = request.GET.get("progress", "").strip()
    quick = request.GET.get("quick", "").strip()
    date_start = request.GET.get("date_start", "").strip()
    date_end = request.GET.get("date_end", "").strip()
    search = request.GET.get("search", "").strip()
    examinee_param = request.GET.get("examinee")
    user_param = request.GET.get("user")

    rows = []

    if AttemptModel:
        qs = AttemptModel.objects.all()
        rel_names = [f.name for f in AttemptModel._meta.fields if getattr(f, "is_relation", False)]
        if "user" in rel_names or "examinee" in rel_names or "exam" in rel_names:
            qs = qs.select_related(*(n for n in ("user", "examinee", "exam") if n in rel_names))

        if position:
            qs = qs.filter(Q(position__iexact=position) | Q(examinee__position__iexact=position))
        if level:
            qs = qs.filter(Q(level__iexact=level) | Q(examinee__level__iexact=level))
        if gender:
            qs = qs.filter(Q(gender__iexact=gender) | Q(examinee__gender__iexact=gender))

        if progress_state == "completed":
            qs = qs.filter(Q(progress__gte=100) | Q(status="completed"))
        elif progress_state == "in_progress":
            qs = qs.filter(Q(progress__lt=100) | Q(status="in_progress"))

        s, e = _range(quick) if quick else (None, None)
        if s and e:
            qs = qs.filter(started_at__gte=s, started_at__lt=e)
        else:
            if date_start:
                qs = qs.filter(started_at__date__gte=date_start)
            if date_end:
                qs = qs.filter(started_at__date__lte=date_end)

        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search)  |
                Q(user__username__icontains=search)   |
                Q(examinee__first_name__icontains=search) |
                Q(examinee__last_name__icontains=search)  |
                Q(examinee__fullname__icontains=search)
            )

        if examinee_param and str(examinee_param).isdigit():
            qs = qs.filter(Q(examinee_id=int(examinee_param)) | Q(user_id=int(examinee_param)))
        elif user_param:
            qs = qs.filter(
                Q(user__username__icontains=user_param) |
                Q(user__first_name__icontains=user_param) |
                Q(user__last_name__icontains=user_param)  |
                Q(examinee__first_name__icontains=user_param) |
                Q(examinee__last_name__icontains=user_param)  |
                Q(examinee__fullname__icontains=user_param)
            )

        for a in qs.order_by("-started_at")[:5000]:
            person = getattr(a, "user", None) or getattr(a, "examinee", None)
            if person and hasattr(person, "get_full_name") and person.get_full_name():
                fullname = person.get_full_name()
            else:
                fullname = (
                    getattr(person, "full_name", None)
                    or f"{getattr(person,'first_name','')} {getattr(person,'last_name','')}".strip()
                    or getattr(person, "username", "")
                    or getattr(person, "email", "")
                )
            rows.append([
                timezone.localtime(getattr(a, "started_at", None)).strftime("%Y-%m-%d %H:%M") if getattr(a, "started_at", None) else "",
                timezone.localtime(getattr(a, "completed_at", None)).strftime("%Y-%m-%d %H:%M") if getattr(a, "completed_at", None) else "",
                fullname,
                getattr(a, "gender", getattr(person, "gender", "")) or "",
                getattr(a, "position", getattr(person, "position", "")) or "",
                getattr(a, "level",    getattr(person, "level", "")) or "",
                int(round(float(getattr(a, "progress", 0) or 0))),
            ])

    else:
        # Fallback export from Answer (no Attempt model)
        rows_ns = _fallback_progress_queryset()
        for r in rows_ns[:5000]:
            u = r.user
            fullname = (
                getattr(u, "full_name", None)
                or f"{getattr(u,'first_name','')} {getattr(u,'last_name','')}".strip()
                or getattr(u, "username", "")
                or getattr(u, "email", "")
            )
            rows.append([
                timezone.localtime(r.started_at).strftime("%Y-%m-%d %H:%M") if r.started_at else "",
                "",  # no completed_at in fallback
                fullname,
                getattr(u, "gender", "") or getattr(r, "gender", ""),
                getattr(u, "position", "") or getattr(r, "position", ""),
                getattr(u, "level", "") or getattr(r, "level", ""),
                int(round(float(r.progress or 0))),
            ])

    out = StringIO()
    writer = csv.writer(out)
    writer.writerow(["Start", "End", "Fullname", "Gender", "Position", "Level", "Progress"])
    writer.writerows(rows)
    resp = HttpResponse(out.getvalue(), content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = "attachment; filename=reports.csv"
    return resp


@admin_only
def report_pdf(request, attempt_id):
    AttemptModel = _attempt_model()
    if not AttemptModel:
        return HttpResponseBadRequest("Attempt model not available")
    attempt = get_object_or_404(AttemptModel, pk=attempt_id)
    html = f"""
    <h1>{getattr(attempt.user, 'get_full_name', lambda: '')() or getattr(attempt.user, 'username', str(attempt.user))}</h1>
    <p>Exam: {_exam_display(getattr(attempt, 'exam', None))}</p>
    <p>Started: {getattr(attempt, 'started_at', '')}</p>
    <p>Completed: {getattr(attempt, 'completed_at', '-') or '-'}</p>
    <p>Progress: {int(round(float(getattr(attempt, 'progress', 0) or 0)))}%</p>
    """
    return HttpResponse(html, content_type="text/html")


@admin_only
def batch_report_pdf(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    AttemptModel = _attempt_model()
    if not AttemptModel:
        return HttpResponseBadRequest("Attempt model not available")
    ids = request.POST.getlist("attempt_ids[]")
    attempts = AttemptModel.objects.filter(id__in=ids)
    html = "<h1>Batch Report</h1>" + "".join(
        [f"<p>{a.user} - {_exam_display(getattr(a, 'exam', None))} - {int(round(float(getattr(a,'progress',0) or 0)))}%</p>" for a in attempts]
    )
    return HttpResponse(html, content_type="text/html")


@admin_only
def view_attempt_tests(request, attempt_id):
    AttemptModel = _attempt_model()
    if not AttemptModel:
        return HttpResponseBadRequest("Attempt model not available")
    attempt = get_object_or_404(AttemptModel, pk=attempt_id)
    # TODO: fetch per-test details from your models (e.g., AttemptItem/Answer)
    taken_tests = []
    return render(request, "dashboard/attempt_tests.html", {"attempt": attempt, "taken_tests": taken_tests})
