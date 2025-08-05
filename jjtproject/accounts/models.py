from django.contrib.auth.models import AbstractUser
from django.db import models
from exams.models import TestBattery

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('psychologist', 'Psychologist'),
        ('client', 'Client'),
        ('examinee', 'Examinee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='examinee')
    has_consented = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"


class School(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class ExamineeAccount(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=50)

    test_battery = models.ForeignKey(TestBattery, on_delete=models.CASCADE, related_name="accounts")
    expiration_from = models.DateField()
    expiration_to = models.DateField()
    
    # Personal Information
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female')])
    birthdate = models.DateField(default='2000-01-01')
    civil_status = models.CharField(max_length=20, choices=[
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
    ], blank=True, null=True)

    # Contact Info
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    # Address Info
    country = models.CharField(max_length=50, default='Philippines')
    street_name = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)

    # Educational Background
    highest_education_level = models.CharField(
        max_length=50,
        choices=[
            ("High School", "High School"),
            ("Bachelor's Degree", "Bachelor's Degree"),
            ("Master's Degree", "Master's Degree"),
            ("Doctorate", "Doctorate"),
        ],
        blank=True,
        null=True
    )
    course = models.CharField(max_length=100, blank=True, null=True)
    school = models.CharField(max_length=100, blank=True, null=True)

    # Target Position/Level
    position = models.CharField(max_length=100, blank=True, null=True)
    level = models.CharField(
        max_length=50,
        choices=[
            ('Rank and File', 'Rank and File'),
            ('Supervisory', 'Supervisory'),
            ('Managerial', 'Managerial')
        ],
        blank=True,
        null=True
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username


class ExamineeConsent(models.Model):
    examinee = models.OneToOneField(ExamineeAccount, on_delete=models.CASCADE)
    consented = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)


class DownloadLog(models.Model):
    filename = models.CharField(max_length=255)
    downloaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    number_of_accounts = models.IntegerField()
    
    def __str__(self):
        return f"{self.filename} by {self.downloaded_by} at {self.downloaded_at}"


    def __str__(self):
        return self.username
    

class ExamineeConsent(models.Model):
    examinee = models.OneToOneField(ExamineeAccount, on_delete=models.CASCADE)
    consented = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)


class DownloadLog(models.Model):
    filename = models.CharField(max_length=255)
    downloaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    number_of_accounts = models.IntegerField()
    
    def __str__(self):
        return f"{self.filename} by {self.downloaded_by} at {self.downloaded_at}"