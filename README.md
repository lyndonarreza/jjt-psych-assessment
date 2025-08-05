# JJT Psychometric Assessment System

This is a Django-based web application for conducting psychometric assessments, including:

- Likert scale questions
- MCQ (Multiple Choice Questions)
- True/False questions
- Essay questions

### Features

- Timer-based auto-submit
- Per-question progress tracking
- Essay autosave via AJAX
- Responsive exam UI styled like Vanguard

### Setup

1. Clone the repo
2. Run migrations
3. Create superuser
4. Start the server

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
