from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from accounts.models import ExamineeAccount
from .models import Exam, MCQQuestion, LikertQuestion, EssayQuestion, TrueFalseQuestion
import json

def list_exams_by_battery(request):
    examinee_id = request.session.get("examinee_id")
    if not examinee_id:
        return redirect("examinee_login")

    examinee = get_object_or_404(ExamineeAccount, id=examinee_id)
    exams = list(Exam.objects.filter(battery=examinee.test_battery).order_by("sort_order"))

    if not exams:
        return render(request, "exams/no_exams.html")

    exam_index = int(request.GET.get("exam", 0))
    if exam_index >= len(exams):
        return redirect("exam_complete")

    current_exam = exams[exam_index]

    # Define Likert options
    LIKERT_CHOICES = [
        ("5", "Strongly Agree"),
        ("4", "Agree"),
        ("3", "Neutral"),
        ("2", "Disagree"),
        ("1", "Strongly Disagree"),
    ]

    # Collect and annotate questions
    questions = []
    for model, qtype in [
        (LikertQuestion, "likertquestion"),
        (MCQQuestion, "mcqquestion"),
        (EssayQuestion, "essayquestion"),
        (TrueFalseQuestion, "truefalsequestion")
    ]:
        qs = list(model.objects.filter(exam=current_exam))

        if qtype in ["mcqquestion", "truefalsequestion"]:
            for q in qs:
                q.choices_set = q.choices.all()

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

    # Handle POST form submission
    if request.method == "POST":
        auto_submit = request.POST.get("auto_submit") == "1"
        unanswered = []

        for q in questions:
            
            ans = request.POST.get(f"q_{q.id}", "").strip()
            if not ans:
                unanswered.append(q.id)
            else:
                request.session[f"answer_{q.id}"] = ans  # Save all answers to session

        request.session.modified = True  # ✅ Force save

        # ✅ Print answers saved to session
        print("========== SESSION DEBUG ==========")
        for key in request.session.keys():
            if key.startswith("answer_"):
                print(f"{key}: {request.session[key]}")
        print("===================================")



        total_questions = len(questions)
        total_unanswered = len(unanswered)

        # If not auto-submitted and there are unanswered questions
        if not auto_submit and unanswered:
            if total_unanswered < total_questions:
                warning_msg = "You have unanswered questions. Please complete them before continuing."
            else:
                warning_msg = "Please answer all questions before continuing."

            return render(request, "exams/take_exam_paginated.html", {
                "questions": questions,
                "current_exam": current_exam,
                "exam_index": exam_index + 1,
                "total_exams": len(exams),
                "has_next": exam_index + 1 < len(exams),
                "warning": warning_msg,
                "progress_percent": int(((exam_index + 1) / len(exams)) * 100),
                "likert_choices": LIKERT_CHOICES,
            })

        # All good — move to next exam
        return redirect(f"{request.path}?exam={exam_index + 1}")

    # First-time GET or re-render after warning
    return render(request, "exams/take_exam_paginated.html", {
        "questions": questions,
        "current_exam": current_exam,
        "exam_index": exam_index + 1,
        "total_exams": len(exams),
        "has_next": exam_index + 1 < len(exams),
        "warning": "",
        "progress_percent": int(((exam_index + 1) / len(exams)) * 100),
        "likert_choices": LIKERT_CHOICES,
    })


@csrf_exempt
def save_essay_answer(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            qid = data.get("question_id")
            answer = data.get("answer")
            request.session[f"answer_{qid}"] = answer  # Store with same session key as others
            return JsonResponse({"status": "saved"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)


def exam_complete(request):
    return render(request, "exams/exam_complete.html")
