# responses/forms.py
from django import forms
from .models import Answer, ExamAttempt

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["attempt", "examinee", "exam", "question_id", "qtype",
                  "mcq_choice_id", "likert_value", "truefalse_value", "essay_text", "raw_value"]

class ExamAttemptForm(forms.ModelForm):
    class Meta:
        model = ExamAttempt
        fields = ["examinee", "exam", "attempt_number", "status", "started_at", "submitted_at",
                  "raw_score", "scaled_score", "duration_seconds", "metadata"]
