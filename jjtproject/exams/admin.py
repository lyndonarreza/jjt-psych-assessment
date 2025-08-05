from django.contrib import admin
from django.utils.html import format_html
from django.forms import BaseInlineFormSet, ValidationError
from django.utils.crypto import get_random_string
from django import forms
from datetime import date
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import TestBattery, Exam, LikertQuestion, EssayQuestion, MCQQuestion, TrueFalseQuestion





from .models import (
    TestBattery, Exam, EssayQuestion,
    MCQQuestion, MCQChoice, TFChoice,
    TrueFalseQuestion, LikertQuestion, LikertScale, LikertOption
)

# ----------------- TRUE/FALSE ------------------
class TFChoiceInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        # Optional validation logic
        pass

class TFChoiceInline(admin.TabularInline):
    model = TFChoice
    formset = TFChoiceInlineFormSet
    extra = 0
    max_num = 2
    fields = ['choice_text', 'is_correct']

@admin.register(TrueFalseQuestion)
class TrueFalseQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'exam', 'get_correct_answer']
    inlines = [TFChoiceInline]

    def get_correct_answer(self, obj):
        correct = obj.choices.filter(is_correct=True).first()
        return correct.choice_text if correct else "❌ Not Set"
    get_correct_answer.short_description = 'Correct Answer'

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new and not obj.choices.exists():
            TFChoice.objects.bulk_create([
                TFChoice(question=obj, choice_text='True'),
                TFChoice(question=obj, choice_text='False'),
            ])


# ----------------- MCQ ------------------
class MCQChoiceInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        total_choices = 0
        correct_count = 0
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                total_choices += 1
                if form.cleaned_data.get('is_correct'):
                    correct_count += 1
        if total_choices < 1:
            raise ValidationError("Each question must have at least one choice.")
        if correct_count < 1:
            raise ValidationError("At least one choice must be marked as correct.")

class MCQChoiceInline(admin.TabularInline):
    model = MCQChoice
    formset = MCQChoiceInlineFormSet
    extra = 4
    fields = ['choice_text', 'is_correct']

@admin.register(MCQQuestion)
class MCQQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'exam']
    list_filter = ['exam']
    inlines = [MCQChoiceInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        question = form.instance
        
        for obj in instances:
            obj.exam = question.exam
            obj.question_text = question.question_text
            obj.question = question
            obj.save()
        formset.save_m2m()


# ----------------- ESSAY ------------------
@admin.register(EssayQuestion)
class EssayQuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'exam']
    fields = ['exam', 'text', 'image', 'explanation']


# ----------------- EXAM ------------------
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['title', 'battery', 'time_limit_minutes', 'total_questions', 'sort_order']
    list_editable = ('sort_order',)
    readonly_fields = ['question_summary']
    
    def total_questions(self, obj):
        return (
            LikertQuestion.objects.filter(exam=obj).count() +
            MCQQuestion.objects.filter(exam=obj).count() +
            EssayQuestion.objects.filter(exam=obj).count() +
            TrueFalseQuestion.objects.filter(exam=obj).count()
        )
    total_questions.short_description = "Total Questions"

    def question_summary(self, obj):
        likerts = LikertQuestion.objects.filter(exam=obj)
        mcqs = MCQQuestion.objects.filter(exam=obj)
        essays = EssayQuestion.objects.filter(exam=obj)
        tfqs = TrueFalseQuestion.objects.filter(exam=obj)

        html = "<h3>Questions in this Exam:</h3>"

        if likerts.exists():
            html += "<strong>Likert Questions:</strong><ul>"
            for q in likerts:
                html += f"<li>{q.text}</li>"
            html += "</ul>"

        if mcqs.exists():
            html += "<strong>MCQ Questions:</strong><ul>"
            for q in mcqs:
                html += f"<li>{q.question_text}</li>"
            html += "</ul>"

        if essays.exists():
            html += "<strong>Essay Questions:</strong><ul>"
            for q in essays:
                html += f"<li>{q.text}</li>"
            html += "</ul>"

        if tfqs.exists():
            html += "<strong>True/False Questions:</strong><ul>"
            for q in tfqs:
                html += f"<li>{q.question_text}</li>"
            html += "</ul>"

        return format_html(html)

    question_summary.short_description = "Questions"




# ----------------- TEST BATTERY ------------------
class ExamInline(admin.TabularInline):
    model = Exam
    extra = 0
    ordering = ['sort_order']  # ✅ Sort exams by this field
    fields = ('title', 'time_limit_minutes', 'sort_order')  # Show sort order in inline



# ✅ Define the admin class first
class TestBatteryAdmin(admin.ModelAdmin):
    list_display = ['name']
    readonly_fields = ['exams_in_battery']
    fields = ['name', 'exams_in_battery']
    inlines = [ExamInline]

    def exams_in_battery(self, obj):
        exams = Exam.objects.filter(battery=obj)
        if not exams.exists():
            return "No exams in this battery."

        html = "<h4>Exams in this Battery:</h4><ul>"
        for exam in exams:
            likert_count = LikertQuestion.objects.filter(exam=exam).count()
            essay_count = EssayQuestion.objects.filter(exam=exam).count()
            mcq_count = MCQQuestion.objects.filter(exam=exam).count()
            tf_count = TrueFalseQuestion.objects.filter(exam=exam).count()
            total = likert_count + essay_count + mcq_count + tf_count

            html += (
                f"<li><strong>{exam.title}</strong> ({exam.time_limit_minutes} min) — "
                f"Questions: {total} "
                f"[Likert: {likert_count}, MCQ: {mcq_count}, TF: {tf_count}, Essay: {essay_count}]</li>"
            )
        html += "</ul>"
        return mark_safe(html)

    exams_in_battery.short_description = "Exams in this Battery"
    
admin.site.register(TestBattery, TestBatteryAdmin)



# ----------------- LIKERT ------------------
class LikertOptionInline(admin.TabularInline):
    model = LikertOption
    extra = 0

@admin.register(LikertScale)
class LikertScaleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    inlines = [LikertOptionInline]

@admin.register(LikertQuestion)
class LikertQuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'exam', 'scale']
    list_filter = ['exam']
    search_fields = ['text']


# ----------------- (Optional) Account Form Stubs ------------------
class BulkAccountCreationForm(forms.Form):
    battery = forms.ModelChoiceField(queryset=TestBattery.objects.all())
    number_of_accounts = forms.IntegerField(min_value=1)
    username_prefix = forms.CharField(required=False)
    expiration_date = forms.DateField(required=False)

class AccountCreationForm(forms.Form):
    test_battery = forms.ModelChoiceField(queryset=TestBattery.objects.all())
    number_of_accounts = forms.IntegerField(min_value=1, max_value=100)
    expiration_from = forms.DateField(initial=date.today)
    expiration_to = forms.DateField()




