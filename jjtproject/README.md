# JJT Project

This is the Django-based **JJT Exam and Psychometric Testing System**.  
It allows examinees to take MCQs, Likert scale questions, True/False, and Essay-based tests with timer support and answer tracking.

---

## 🚀 Features

- Examinee Login with Session Tracking
- Multiple Question Types:
  - MCQ (Multiple Choice)
  - Likert Scale (Horizontal Layout)
  - Essay (with auto-save)
  - True / False
- Per-Exam Timer with Auto-Submission
- Highlight Unanswered Questions
- Progress Bar and Exam Navigation
- Styled similar to Vanguard’s testing UI
- Admin: Create Exams, Questions, and Track Progress

---

## 🛠️ Tech Stack

- Python 3.x
- Django 5.x
- Bootstrap 5
- FontAwesome
- HTML / JavaScript

---

## 📁 Folder Structure

jjtproj/
├── accounts/ # Examinee models and login
├── exams/ # Exams, questions, logic
├── templates/ # HTML templates
├── static/css/ # Custom exam CSS
├── manage.py
└── db.sqlite3

---

## 📦 Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/lyndonarreza/jjt-psych-assessment.git
   cd jjtproject

2. Create virtual environment:
 
    python -m venv env
    source env/bin/activate   # or env\Scripts\activate on Windows

3. Install dependencies:

   pip install -r requirements.txt


4. Run Migrations

   python manage.py migrate

5. Start server

   python manage.py runserver

6. Admin Access

   python manage.py createsuperuser



