from django.db import models
from django.core.exceptions import ValidationError
# Create your models here.




class TestBattery(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Test Battery"
        verbose_name_plural = "Test Batteries"  # ✅ Fix plural


class Exam(models.Model):
   
    title = models.CharField(max_length=200)
    battery = models.ForeignKey(TestBattery, on_delete=models.CASCADE)

    time_limit_minutes = models.IntegerField(null=True, blank=True)

    sort_order = models.PositiveIntegerField(default=0)  # ✅ Add this line

    def __str__(self):
        return self.title
    

    class Meta:
        ordering = ['sort_order']

class EssayQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    text = models.TextField()
    image = models.ImageField(upload_to='question_images/', null=True, blank=True)
        
    explanation = models.TextField(blank=True, help_text="Optional explanation for evaluators or students.")  # ✅ New field

    def __str__(self):
        return f"{self.exam.title} - {self.text[:50]}"

    class Meta:
        verbose_name = "Essay Question"
        verbose_name_plural = "Essay Questions"




class MCQQuestion(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE)
    question_text = models.TextField()

    def __str__(self):
        return self.question_text


class MCQChoice(models.Model):
    exam = models.ForeignKey('Exam', on_delete=models.CASCADE)
    question_text = models.TextField()
    choice_text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    question = models.ForeignKey(
        'MCQQuestion',
        on_delete=models.CASCADE,
        related_name='choices',  # ✅ Add this line
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.choice_text} ({'✔' if self.is_correct else '✘'})"

class TrueFalseQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    question_text = models.TextField()

    def __str__(self):
        return self.question_text

class TFChoice(models.Model):
    question = models.ForeignKey(TrueFalseQuestion, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=10)  # "True" or "False"
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.choice_text} ({'✔' if self.is_correct else '✘'})"


class LikertScale(models.Model):
    name = models.CharField(max_length=100)  # e.g. "5-point scale"
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
class LikertOption(models.Model):
    scale = models.ForeignKey(LikertScale, on_delete=models.CASCADE, related_name="options")
    label = models.CharField(max_length=100)  # e.g. "Strongly Agree"
    value = models.IntegerField()             # e.g. 5

    def __str__(self):
        return f"{self.label} ({self.value})"    

class LikertQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    text = models.TextField()
    scale = models.ForeignKey(LikertScale, on_delete=models.CASCADE)

    def __str__(self):
        return self.text
    



