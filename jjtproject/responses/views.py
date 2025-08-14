from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import transaction
import json

from accounts.models import ExamineeAccount
from exams.models import Exam
from .models import ExamAttempt, Answer


def ping(request):
    return HttpResponse("responses ok")


@csrf_exempt
def start_attempt(request, exam_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    examinee_id = request.session.get("examinee_id")
    if not examinee_id:
        return HttpResponseBadRequest("No examinee in session")

    examinee = get_object_or_404(ExamineeAccount, id=examinee_id)
    exam = get_object_or_404(Exam, id=exam_id)

    attempt = ExamAttempt.start_or_get(examinee, exam)
    # store in session for current exam flow
    request.session[f"attempt_exam_{exam.id}"] = attempt.id
    request.session.modified = True

    return JsonResponse({"attempt_id": attempt.id})


@csrf_exempt
def save_answer(request):
    """
    Unified upsert endpoint for MCQ/Likert/TF/Essay.
    Body JSON:
    {
      "attempt_id": int,
      "exam_id": int,
      "question_id": int,
      "qtype": "mcqquestion"|"likertquestion"|"truefalsequestion"|"essayquestion",
      "value": "raw string value"  # choice id / "True"/"False" / "1"-"5" / essay text
    }
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    required = ("attempt_id", "exam_id", "question_id", "qtype", "value")
    if not all(k in data for k in required):
        return HttpResponseBadRequest("Missing fields")

    attempt = get_object_or_404(ExamAttempt, id=data["attempt_id"])
    exam = get_object_or_404(Exam, id=data["exam_id"])

    # auth sanity (tie to session examinee)
    examinee_id = request.session.get("examinee_id")
    if not examinee_id or attempt.examinee_id != examinee_id:
        return HttpResponseBadRequest("Invalid examinee context")

    qtype = data["qtype"]
    raw = str(data["value"])

    mcq_choice_id = None
    likert_value = None
    truefalse_value = None
    essay_text = None

    if qtype == "mcqquestion":
        mcq_choice_id = int(raw) if raw.isdigit() else None
    elif qtype == "likertquestion":
        try:
            likert_value = int(raw)
        except ValueError:
            likert_value = None
    elif qtype == "truefalsequestion":
        truefalse_value = (raw == "True")
    elif qtype == "essayquestion":
        essay_text = raw

    with transaction.atomic():
        # Upsert per (attempt, question_id)
        obj, _created = Answer.objects.update_or_create(
            attempt=attempt,
            question_id=int(data["question_id"]),
            defaults={
                "examinee_id": attempt.examinee_id,
                "exam_id": exam.id,
                "qtype": qtype,
                "mcq_choice_id": mcq_choice_id,
                "likert_value": likert_value,
                "truefalse_value": truefalse_value,
                "essay_text": essay_text,
                "raw_value": raw,
            },
        )

    return JsonResponse({"status": "saved", "answer_id": obj.id})


@csrf_exempt
def submit_attempt(request, attempt_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    attempt = get_object_or_404(ExamAttempt, id=attempt_id)

    # Security sanity: ensure session examinee matches attempt
    examinee_id = request.session.get("examinee_id")
    if not examinee_id or examinee_id != attempt.examinee_id:
        return HttpResponseBadRequest("Invalid examinee context")

    attempt.finalize()
    return JsonResponse({"status": "submitted", "attempt_id": attempt.id})
