from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import now
from django.http import JsonResponse

from .forms import PasswordChangeForm, ExamineeRegistrationForm, ExamineeAccountUpdateForm
from .models import ExamineeAccount, ExamineeConsent
from exams.models import Exam


def examinee_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            examinee = ExamineeAccount.objects.get(username=username, password=password)
            request.session["examinee_id"] = examinee.id
            return redirect("examinee_consent")
        except ExamineeAccount.DoesNotExist:
            messages.error(request, "Invalid username or password.")

    return render(request, "accounts/examinee_login.html")


def examinee_consent(request):
    examinee_id = request.session.get("examinee_id")
    if not examinee_id:
        return redirect("examinee_login")

    examinee = get_object_or_404(ExamineeAccount, id=examinee_id)

    if request.method == "POST":
        if 'agree' in request.POST:
            consent, _ = ExamineeConsent.objects.get_or_create(examinee=examinee)
            consent.consented = True
            consent.consented_at = now()
            consent.save()
            return redirect('examinee_registration')
        else:
            request.session.flush()  # This is okay ONLY if declining
            return redirect('examinee_login')

    return render(request, 'accounts/consent.html', {'examinee': examinee})



def examinee_registration(request):
    examinee_id = request.session.get('examinee_id')
    if not examinee_id:
        return redirect('examinee_login')

    examinee = get_object_or_404(ExamineeAccount, pk=examinee_id)

    if request.method == 'POST':
        form = ExamineeAccountUpdateForm(request.POST, instance=examinee)
        if form.is_valid():
            form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('exam_instructions')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors})

    else:
        form = ExamineeAccountUpdateForm(instance=examinee)

    return render(request, 'accounts/registration.html', {'form': form})




def exam_instructions(request):
    examinee_id = request.session.get('examinee_id')
    if not examinee_id:
        return redirect('examinee_login')

    if request.method == 'POST':
        return redirect('list_exams_by_battery')  # 👈 Redirect to exam list based on battery

    return render(request, 'accounts/exam_instructions.html')


def check_examinee_exists(request):
    if request.method == "POST":
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        gender = request.POST.get('gender')
        birthdate = request.POST.get('birthdate')

        exists = ExamineeAccount.objects.filter(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            gender=gender,
            birthdate=birthdate
        ).exists()

        return JsonResponse({'exists': exists})


def start_exam(request):
    examinee_id = request.session.get('examinee_id')
    if not examinee_id:
        return redirect('examinee_login')

    try:
        exam = Exam.objects.first()  # Or filter for active exams
        return redirect('exam_questions', exam_id=exam.id)
    except Exam.DoesNotExist:
        return render(request, "accounts/no_exam_available.html")


def change_password(request):
    examinee_id = request.session.get('examinee_id')
    if not examinee_id:
        return redirect('examinee_login')

    examinee = get_object_or_404(ExamineeAccount, pk=examinee_id)

    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            if examinee.password != form.cleaned_data['current_password']:
                messages.error(request, "Incorrect current password.")
            else:
                examinee.password = form.cleaned_data['new_password']
                examinee.save()
                messages.success(request, "Password updated.")
                return redirect('examinee_consent')
    else:
        form = PasswordChangeForm()

    return render(request, 'accounts/change_password.html', {'form': form})







def update_account_view(request, username):
    examinee = get_object_or_404(ExamineeAccount, username=username)

    if request.method == 'POST':
        form = ExamineeAccountUpdateForm(request.POST, instance=examinee)
        if form.is_valid():
            form.save()
            return redirect('consent_page')  # replace with your next step
    else:
        form = ExamineeAccountUpdateForm(instance=examinee)

    return render(request, 'accounts/update_account.html', {'form': form})