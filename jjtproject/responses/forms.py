from django import forms
from .models import ExamineeProfile

class ExamineeProfileForm(forms.ModelForm):
    class Meta:
        model = ExamineeProfile
        fields = ['fullname', 'gender', 'birthdate', 'civil_status', 'education', 'position', 'company']
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }
