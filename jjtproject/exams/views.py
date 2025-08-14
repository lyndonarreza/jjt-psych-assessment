# exams/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Max

from accounts.models import ExamineeAccount
from .models import Exam, MCQQuestion, LikertQuestion, EssayQuestion, TrueFalseQuestion

# ⬇️ responses models
from responses.models import ExamAttempt, Answer

import json


def _collect_questions(current_exam):
    """Gather all question types for the current exam and normalize .qtype and .text."""
    questions = []
    for model, qtype in [
        (LikertQuestion, "likertquestion"),
        (MCQQuestion, "mcqquestion"),
        (EssayQuestion, "essayquestion"),
        (TrueFalseQuestion, "truefalsequestion"),
    ]:
        qs = list(model.objects.filter(exam=current_exam))
        for q in qs:
            q.qtype = qtype
            if hasattr(q, "question_text"):
                q.text = q.question_text
            elif hasattr(q, "statement"):
                q.text = q.statement
            elif hasattr(q, "prompt"):
                q.text = q.prompt
            elif hasattr(q, "text"):
                q.text = q.text
            else:
                q.text = "Untitled"
        questions += qs
    questions.sort(key=lambda q: q.id)
    return questions


def _get_or_start_attempt(request, examinee, exam):
    """Reuse or start an attempt for (examinee, exam). Persist id in session."""
    key = f"attempt_exam_{exam.id}"
    attempt_id = request.session.get(key)
    attempt = None
    if attempt_id:
        attempt = ExamAttempt.objects.filter(id=attempt_id, examinee=examinee, exam=exam).first()

    if not attempt:
        last_num = (
            ExamAttempt.objects.filter(examinee=examinee, exam=exam)
            .aggregate(Max("attempt_number"))["attempt_number__max"] or 0
        )
        attempt = ExamAttempt.objects.create(
            examinee=examinee,
            exam=exam,
            attempt_number=last_num + 1,
            status="in_progress",
            started_at=timezone.now(),
        )
        request.session[key] = attempt.id
        request.session.modified = True

    return attempt


def _save_answers_for_exam(*, request, examinee, exam, questions, attempt):
    """
    Upsert each answered question from THIS POST (this page) into responses.Answer.
    Unique key is (attempt, qtype, question_id).
    """
    with transaction.atomic():
        for q in questions:
            raw = (request.POST.get(f"q_{q.id}", "") or "").strip()
            if not raw:
                continue  # unanswered on this page; leave untouched

            mcq_choice_id = None
            likert_value = None
            truefalse_value = None
            essay_text = None

            if q.qtype == "mcqquestion":
                try:
                    mcq_choice_id = int(raw)
                except ValueError:
                    mcq_choice_id = None
            elif q.qtype == "likertquestion":
                try:
                    likert_value = int(raw)
                except ValueError:
                    likert_value = None
            elif q.qtype == "truefalsequestion":
                truefalse_value = (raw == "True")
            elif q.qtype == "essayquestion":
                essay_text = raw

            Answer.objects.update_or_create(
                attempt=attempt,
                qtype=q.qtype,
                question_id=q.id,
                defaults={
                    "examinee": examinee,
                    "exam": exam,
                    "mcq_choice_id": mcq_choice_id,
                    "likert_value": likert_value,
                    "truefalse_value": truefalse_value,
                    "essay_text": essay_text,
                    "raw_value": raw,
                },
            )


def _finalize_attempt(attempt):
    """Mark attempt as submitted and stamp duration."""
    if attempt.status != "submitted":
        attempt.status = "submitted"
        attempt.submitted_at = timezone.now()
        if attempt.started_at:
            attempt.duration_seconds = int((attempt.submitted_at - attempt.started_at).total_seconds())
        attempt.save(update_fields=["status", "submitted_at", "duration_seconds"])


def list_exams_by_battery(request):
    # 1) Check examinee
    examinee_id = request.session.get("examinee_id")
    if not examinee_id:
        return redirect("examinee_login")
    examinee = get_object_or_404(ExamineeAccount, id=examinee_id)

    # 2) Locate current exam in battery
    exams = list(Exam.objects.filter(battery=examinee.test_battery).order_by("sort_order"))
    if not exams:
        return render(request, "exams/no_exams.html")

    exam_index = int(request.GET.get("exam", 0))
    if exam_index >= len(exams):
        return redirect("exam_complete")

    current_exam = exams[exam_index]

    # 3) Choices + questions
    LIKERT_CHOICES = [
        ("5", "Strongly Agree"),
        ("4", "Agree"),
        ("3", "Neutral"),
        ("2", "Disagree"),
        ("1", "Strongly Disagree"),
    ]
    questions = _collect_questions(current_exam)

    # 4) POST: accept page answers, gate on unanswered, then persist and advance
    if request.method == "POST":
        auto_submit = request.POST.get("auto_submit") == "1"
        unanswered = []

        # Keep answers in session for re-render retention if warning
        for q in questions:
            val = (request.POST.get(f"q_{q.id}", "") or "").strip()
            if not val:
                unanswered.append(q.id)
            else:
                request.session[f"answer_{q.id}"] = val
        request.session.modified = True

        # If manual click and there are unanswered, warn and stay on page
        if not auto_submit and unanswered:
            warning_msg = (
                "You have unanswered questions. Please complete them before continuing."
                if len(unanswered) < len(questions)
                else "Please answer all questions before continuing."
            )
            return render(
                request,
                "exams/take_exam_paginated.html",
                {
                    "questions": questions,
                    "current_exam": current_exam,
                    "exam_index": exam_index + 1,
                    "total_exams": len(exams),
                    "has_next": exam_index + 1 < len(exams),
                    "warning": warning_msg,
                    "progress_percent": int(((exam_index + 1) / len(exams)) * 100),
                    "likert_choices": LIKERT_CHOICES,
                },
            )

        # ✅ Allowed to proceed (all answered OR auto-submit): persist this page
        attempt = _get_or_start_attempt(request, examinee, current_exam)
        _save_answers_for_exam(
            request=request,
            examinee=examinee,
            exam=current_exam,
            questions=questions,
            attempt=attempt,
        )

        # Move to next exam or finalize
        if exam_index + 1 < len(exams):
            return redirect(f"{request.path}?exam={exam_index + 1}")
        else:
            _finalize_attempt(attempt)
            return redirect("exam_complete")

    # 5) GET: initial render / re-render after warning
    return render(
        request,
        "exams/take_exam_paginated.html",
        {
            "questions": questions,
            "current_exam": current_exam,
            "exam_index": exam_index + 1,
            "total_exams": len(exams),
            "has_next": exam_index + 1 < len(exams),
            "warning": "",
            "progress_percent": int(((exam_index + 1) / len(exams)) * 100),
            "likert_choices": LIKERT_CHOICES,
        },
    )


@csrf_exempt
def save_essay_answer(request):
    """Optional AJAX autosave for essays—keeps session in sync; final save happens on POST as well."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            qid = data.get("question_id")
            answer = data.get("answer")
            request.session[f"answer_{qid}"] = answer
            request.session.modified = True
            return JsonResponse({"status": "saved"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


def exam_complete(request):
    return render(request, "exams/exam_complete.html")
