from django.contrib import admin
from .models import ExamAttempt, Answer


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id", "examinee", "exam", "attempt_number", "status",
        "started_at", "submitted_at", "duration_seconds",
    )
    list_filter = ("status", "exam")
    search_fields = ("examinee__id", "examinee__user__username", "exam__title")
    ordering = ("-started_at",)
    readonly_fields = ("started_at", "submitted_at", "duration_seconds")


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = (
        "id", "attempt", "exam", "examinee", "qtype", "question_id",
        "mcq_choice_id", "likert_value", "truefalse_value",
        "created_at",
    )
    list_filter = ("qtype", "exam")
    search_fields = ("examinee__id", "examinee__user__username", "question_id")
    ordering = ("attempt", "question_id")
    readonly_fields = ("created_at", "updated_at")
