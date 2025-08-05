# accounts/forms.py
from django import forms
from .models import ExamineeAccount

class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput)
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("new_password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("New passwords do not match.")
        return cleaned_data



class ExamineeAccountUpdateForm(forms.ModelForm):
    class Meta:
        model = ExamineeAccount
        fields = [
            'first_name', 'middle_name', 'last_name', 'gender', 'birthdate',
            'civil_status', 'contact_number', 'email',
            'country', 'street_name', 'city', 'province', 'zip_code',
            'highest_education_level', 'course', 'school',
            'position', 'level',
        ]
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }


class ExamineeRegistrationForm(forms.ModelForm):
    class Meta:
        model = ExamineeAccount
        fields = [
            'first_name', 'middle_name', 'last_name', 'gender', 'birthdate',
            'civil_status', 'contact_number', 'email',
            'country', 'street_name', 'city', 'province', 'zip_code',
            'highest_education_level', 'course', 'school',
            'position', 'level',
        ]
        widgets = {
            'birthdate': forms.DateInput(attrs={'type': 'date'}),
        }