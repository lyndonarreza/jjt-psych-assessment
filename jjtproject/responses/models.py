from django.db import models
from django.utils import timezone
from django.db.models import Max
from accounts.models import ExamineeAccount
from exams.models import Exam


class ExamAttempt(models.Model):
    STATUS_CHOICES = [
        ("in_progress", "In progress"),
        ("submitted", "Submitted"),
        ("expired", "Expired"),
        ("abandoned", "Abandoned"),
    ]

    examinee = models.ForeignKey(
        ExamineeAccount, on_delete=models.CASCADE, related_name="exam_attempts"
    )
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")

    # If you allow multiple tries per exam, increment attempt_number per examinee+exam
    attempt_number = models.PositiveIntegerField(default=1)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="in_progress")
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Optional scoring fields (fill later during scoring)
    raw_score = models.FloatField(null=True, blank=True)
    scaled_score = models.FloatField(null=True, blank=True)

    # Cached duration in seconds (set when submitted)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Freeform metadata (e.g., browser, IP, flags)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["examinee", "exam"]),
            models.Index(fields=["exam", "status"]),
        ]
        unique_together = (("examinee", "exam", "attempt_number"),)

    def __str__(self):
        return f"Attempt #{self.attempt_number} — {self.examinee} — {self.exam}"

    @property
    def is_submitted(self):
        return self.status == "submitted"

    @classmethod
    def start_or_get(cls, examinee: ExamineeAccount, exam: Exam):
        """Convenience helper to start a new attempt if none is in session."""
        last_num = cls.objects.filter(examinee=examinee, exam=exam).aggregate(
            Max("attempt_number")
        )["attempt_number__max"] or 0
        return cls.objects.create(
            examinee=examinee,
            exam=exam,
            attempt_number=last_num + 1,
            status="in_progress",
            started_at=timezone.now(),
        )

    def finalize(self):
        if not self.is_submitted:
            self.status = "submitted"
            self.submitted_at = timezone.now()
            if self.started_at:
                self.duration_seconds = int((self.submitted_at - self.started_at).total_seconds())
            self.save(update_fields=["status", "submitted_at", "duration_seconds"])


class Answer(models.Model):
    """
    Unified answer model for all question types.
    We store the question's integer ID (from its source table) and a qtype string.
    Values are kept both in normalized fields and raw_value for safety.
    """
    QTYPE_CHOICES = [
        ("mcqquestion", "MCQ"),
        ("likertquestion", "Likert"),
        ("truefalsequestion", "True/False"),
        ("essayquestion", "Essay"),
    ]

    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="answers")
    examinee = models.ForeignKey(ExamineeAccount, on_delete=models.CASCADE, related_name="answers")
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="answers")

    question_id = models.IntegerField()                 # ID from the source question table
    qtype = models.CharField(max_length=32, choices=QTYPE_CHOICES)

    # Normalized slots (use the one that applies; others stay null)
    mcq_choice_id = models.IntegerField(null=True, blank=True)     # choice PK for MCQ
    likert_value = models.IntegerField(null=True, blank=True)      # typically 1..5
    truefalse_value = models.BooleanField(null=True, blank=True)   # True/False
    essay_text = models.TextField(null=True, blank=True)

    # Always keep the raw submission string for auditing/debug (what the user sent)
    raw_value = models.TextField()

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



    class Meta:
            indexes = [
                models.Index(fields=["attempt", "question_id"]),
                models.Index(fields=["examinee", "exam"]),
                models.Index(fields=["qtype"]),
                models.Index(fields=["attempt", "qtype", "question_id"]),
            ]
            unique_together = (
                ("attempt", "qtype", "question_id"),  # <-- THIS must be present
            )        

    def __str__(self):
        return f"Answer q{self.question_id} ({self.qtype}) by {self.examinee}"
