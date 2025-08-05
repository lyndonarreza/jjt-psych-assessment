from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.admin.widgets import AdminDateWidget
from django.urls import path
from django.shortcuts import render, redirect
from django import forms
import random
import string
from datetime import date
from django.utils.crypto import get_random_string
import csv
from django.http import HttpResponse
import os
from django.conf import settings
from django.utils.html import format_html

from .models import User, ExamineeAccount, School, Course, DownloadLog
from exams.models import TestBattery


# --- USER ADMIN ---
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Additional Info", {
            "fields": ("role", "has_consented"),
        }),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')

admin.site.register(User, UserAdmin)


# --- ACCOUNT CREATION FORM ---
class AccountCreationForm(forms.Form):
    test_battery = forms.ModelChoiceField(queryset=TestBattery.objects.all())
    number_of_accounts = forms.IntegerField(min_value=1, max_value=100)
    expiration_from = forms.DateField(initial=date.today)
    expiration_to = forms.DateField()
    school = forms.ModelChoiceField(queryset=School.objects.all(), required=False)
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False)


class BulkAccountCreationForm(forms.Form):
    battery = forms.ModelChoiceField(queryset=TestBattery.objects.all())
    number_of_accounts = forms.IntegerField(min_value=1)
    username_prefix = forms.CharField(required=False)
    expiration_from = forms.DateField()
    expiration_to = forms.DateField()
    school = forms.ModelChoiceField(queryset=School.objects.all(), required=False)
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=False)

# Place this function above or below the ExamineeAccountAdmin class
@admin.action(description="Download selected examinee accounts as CSV")
def download_selected_as_csv(modeladmin, request, queryset):
    from django.http import HttpResponse
    import csv

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="selected_accounts.csv"'
    writer = csv.writer(response)

    writer.writerow(['Username', 'password','Test Battery', 'School', 'Course', 'Expiration From', 'Expiration To', 'Created At'])

    for account in queryset:
        writer.writerow([
            account.username,
            account.password,
            account.test_battery.name if account.test_battery else '',
            account.school.name if account.school else '',
            account.course.name if account.course else '',
            account.expiration_from,
            account.expiration_to,
            account.created_at,
        ])

    return response

# --- EXAMINEE ACCOUNT ADMIN ---
class ExamineeAccountAdmin(admin.ModelAdmin):
    actions = [download_selected_as_csv]
    change_list_template = "admin/accounts/examineeaccount/change_list.html"
    list_display = ['username', 'test_battery', 'school', 'course', 'expiration_from', 'expiration_to', 'created_at']
    search_fields = ['first_name', 'middle_name', 'last_name', 'username', 'email']
    readonly_fields = ('created_at',) 
    
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('create-accounts/', self.admin_site.admin_view(self.create_accounts), name='accounts_examineeaccount_create'),
            path('bulk-create/', self.admin_site.admin_view(self.bulk_create_view), name='accounts_examineeaccount_bulk_create'),
        ]
        return custom_urls + urls

    def create_accounts(self, request):
        if request.method == "POST":
            form = AccountCreationForm(request.POST)
            if form.is_valid():
                accounts = []
                for _ in range(form.cleaned_data['number_of_accounts']):
                    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                    accounts.append(ExamineeAccount(
                        username=username,
                        password=password,
                        test_battery=form.cleaned_data['test_battery'],
                        school=form.cleaned_data.get('school'),
                        course=form.cleaned_data.get('course'),
                        expiration_from=form.cleaned_data['expiration_from'],
                        expiration_to=form.cleaned_data['expiration_to'],
                    ))
                ExamineeAccount.objects.bulk_create(accounts)
                self.message_user(request, f"{len(accounts)} accounts created.", messages.SUCCESS)
                return redirect("..")
        else:
            form = AccountCreationForm()

        return render(request, "admin/accounts/examineeaccount/create_accounts.html", {'form': form})

    def bulk_create_view(self, request):
        if request.method == "POST":
            form = BulkAccountCreationForm(request.POST)
            if form.is_valid():
                accounts = []
                passwords = []
                prefix = form.cleaned_data['username_prefix'] or 'user'
                existing_usernames = set(ExamineeAccount.objects.values_list('username', flat=True))

                for i in range(form.cleaned_data['number_of_accounts']):
                    username = f"{prefix}{i + 1:03d}"
                    while username in existing_usernames:
                        username = f"{prefix}{i + 1:03d}_{get_random_string(3)}"
                    existing_usernames.add(username)

                    password = get_random_string(8)
                    passwords.append(password)

                    account = ExamineeAccount(
                        username=username,
                        password=password,
                        test_battery=form.cleaned_data['battery'],
                        expiration_from=form.cleaned_data['expiration_from'],
                        expiration_to=form.cleaned_data['expiration_to'],
                        school=form.cleaned_data.get('school'),
                        course=form.cleaned_data.get('course'),
                    )
                    accounts.append(account)

                ExamineeAccount.objects.bulk_create(accounts)

                # Save CSV to media/exports/
                export_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
                os.makedirs(export_dir, exist_ok=True)
                filepath = os.path.join(export_dir, 'bulk_accounts.csv')

                with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Username', 'Password', 'Test Battery', 'School', 'Course', 'Expiration From', 'Expiration To'])
                    for i, account in enumerate(accounts):
                        writer.writerow([
                            account.username,
                            passwords[i],
                            account.test_battery.name if account.test_battery else '',
                            account.school.name if account.school else '',
                            account.course.name if account.course else '',
                            account.expiration_from,
                            account.expiration_to,
                        ])

                # Show download link
                csv_url = os.path.join(settings.MEDIA_URL, 'exports/bulk_accounts.csv')
                self.message_user(
                    request,
                    format_html(
                        '{} accounts created. <a href="{}" target="_blank">Download CSV</a>',
                        len(accounts),
                        csv_url
                    ),
                    messages.SUCCESS
                )

                DownloadLog.objects.create(
                    filename='bulk_accounts.csv',
                    downloaded_by=request.user,
                    number_of_accounts=len(accounts)
            )
                return redirect("..")
        else:
            form = BulkAccountCreationForm()

        return render(request, "admin/accounts/examineeaccount/bulk_create.html", {'form': form})
    



@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ['filename', 'downloaded_by', 'downloaded_at', 'number_of_accounts']
    readonly_fields = ['filename', 'downloaded_by', 'downloaded_at', 'number_of_accounts']



admin.site.register(ExamineeAccount, ExamineeAccountAdmin)
admin.site.register(School)
admin.site.register(Course)
