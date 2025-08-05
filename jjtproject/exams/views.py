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

    LIKERT_CHOICES = [
        ("5", "Strongly Agree"),
        ("4", "Agree"),
        ("3", "Neutral"),
        ("2", "Disagree"),
        ("1", "Strongly Disagree"),
    ]

         # Collect questions
    questions = []
    for model, qtype in [
        (LikertQuestion, "likertquestion"),
        (MCQQuestion, "mcqquestion"),
        (EssayQuestion, "essayquestion"),
        (TrueFalseQuestion, "truefalsequestion")
    ]:
        qs = list(model.objects.filter(exam=current_exam))
        
        # For MCQ and True/False, attach choices
        if qtype in ["mcqquestion", "truefalsequestion"]:
            for q in qs:
                q.choices_set = q.choices.all()
        
        # Set qtype and .text field uniformly
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
    

    if request.method == "POST":
        auto_submit = request.POST.get("auto_submit") == "1"
        unanswered = []

        for q in questions:
            ans = request.POST.get(f"q_{q.id}", "").strip()
            if not ans:
                unanswered.append(q.id)
            else:
                request.session[f"answer_{q.id}"] = ans

        # 🚨 If not auto-submit and unanswered questions exist, show warning
        if not auto_submit and unanswered:
            return render(request, "exams/take_exam_paginated.html", {
                "questions": questions,
                "current_exam": current_exam,
                "exam_index": exam_index + 1,
                "total_exams": len(exams),
                "has_next": exam_index + 1 < len(exams),
                "warning": "Please answer all questions before continuing.",
                "progress_percent": int(((exam_index + 1) / len(exams)) * 100),
                "likert_choices": LIKERT_CHOICES,
            })

        return redirect(f"{request.path}?exam={exam_index + 1}")













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
            request.session[f"essay_{qid}"] = answer
            return JsonResponse({"status": "saved"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)

def exam_complete(request):
    return render(request, "exams/exam_complete.html")
