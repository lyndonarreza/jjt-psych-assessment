# responses/admin.py
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered, AlreadyRegistered, site
from django.http import HttpResponse
import csv

from .models import ExamAttempt, Answer


@admin.action(description="Export selected answers to CSV")
def export_answers_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="answers.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "ID","Attempt ID","Attempt #","Attempt Status","Exam","Examinee",
        "QType","Question ID","MCQ Choice ID","Likert Value","True/False",
        "Essay Text","Raw Value","Created At","Updated At",
    ])
    for a in queryset.select_related("attempt","exam","examinee"):
        writer.writerow([
            a.id,
            a.attempt_id,
            getattr(a.attempt, "attempt_number", ""),
            getattr(a.attempt, "status", ""),
            getattr(a.exam, "title", str(a.exam)),
            str(a.examinee),
            a.qtype,
            a.question_id,
            a.mcq_choice_id or "",
            a.likert_value if a.likert_value is not None else "",
            "" if a.truefalse_value is None else ("True" if a.truefalse_value else "False"),
            (a.essay_text or "").replace("\r", " ").replace("\n", " ").strip(),
            (a.raw_value or "").replace("\r", " ").replace("\n", " ").strip(),
            a.created_at, a.updated_at,
        ])
    return response


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = (
        "qtype","question_id","mcq_choice_id","likert_value",
        "truefalse_value","short_essay","raw_value","created_at",
    )
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def short_essay(self, obj):
        txt = obj.essay_text or ""
        return (txt[:80] + "…") if len(txt) > 80 else txt
    short_essay.short_description = "Essay (preview)"


class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id","examinee","exam","attempt_number","status",
        "started_at","submitted_at","duration_seconds",
    )
    list_filter = ("status","exam")
    search_fields = ("examinee__id","examinee__first_name","examinee__last_name","exam__title")
    date_hierarchy = "started_at"
    inlines = [AnswerInline]
    readonly_fields = ("started_at","submitted_at")


class AnswerAdmin(admin.ModelAdmin):
    list_display = ("id","attempt","exam","examinee","qtype","question_id","display_answer","created_at")
    list_filter = ("qtype","exam","attempt__status")
    search_fields = ("exam__title","examinee__first_name","examinee__last_name","examinee__id","question_id","raw_value")
    date_hierarchy = "created_at"
    actions = [export_answers_csv]

    def display_answer(self, obj):
        if obj.qtype == "mcqquestion":
            return f"MCQ choice #{obj.mcq_choice_id}" if obj.mcq_choice_id else "(none)"
        if obj.qtype == "likertquestion":
            return f"Likert: {obj.likert_value}" if obj.likert_value is not None else "(none)"
        if obj.qtype == "truefalsequestion":
            if obj.truefalse_value is None: return "(none)"
            return "True" if obj.truefalse_value else "False"
        if obj.qtype == "essayquestion":
            if not obj.essay_text: return "(none)"
            t = obj.essay_text.strip()
            return (t[:50] + "…") if len(t) > 50 else t
        return obj.raw_value or "(none)"
    display_answer.short_description = "Answer"


# Unregister if already registered (safe on reload)
for m in (Answer, ExamAttempt):
    try:
        site.unregister(m)
    except NotRegistered:
        pass

# Register (ignore double-register)
for model, admin_cls in ((ExamAttempt, ExamAttemptAdmin), (Answer, AnswerAdmin)):
    try:
        site.register(model, admin_cls)
    except AlreadyRegistered:
        pass
