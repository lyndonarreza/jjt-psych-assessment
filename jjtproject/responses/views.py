from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ExamineeProfileForm
from .models import ExamineeProfile

@login_required
def register_profile(request):
    try:
        profile = ExamineeProfile.objects.get(user=request.user)
        form = ExamineeProfileForm(instance=profile)
    except ExamineeProfile.DoesNotExist:
        form = ExamineeProfileForm()

    if request.method == 'POST':
        if 'update' in request.POST:
            form = ExamineeProfileForm(request.POST, instance=profile)
        else:
            form = ExamineeProfileForm(request.POST)

        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            return redirect('/exam-instructions/')  # redirect to next step

    return render(request, 'responses/register.html', {'form': form})
