# PayFlow - Payment Collection Management App

A Django-based web application for managing member dues, tracking payments, and generating collection reports.

## Features

- **Dashboard** — KPIs (total collected, expected, pending, collection rate), status distribution, monthly collection overview
- **Member Management** — Full CRUD for members with search and status filtering
- **Payment Recording** — Record payments with amount, date, method, and notes
- **Monthly Matrix** — 12-month grid showing paid/partial/overdue/unpaid status per member
- **Status Reports** — Members grouped by payment status (up-to-date, advance, behind, unpaid)
- **CSV Export** — Download collection reports as CSV
- **User Authentication** — Login, registration, and role-based profiles (admin, collector, viewer)
- **Django Admin** — Full admin panel for managing all data

## Tech Stack

- **Backend**: Django 5.2
- **Database**: SQLite (default)
- **Frontend**: Django templates with Bootstrap 5
- **Icons**: Bootstrap Icons

## Quick Start

### 1. Install Dependencies

```bash
pip install django
```

### 2. Run Migrations

```bash
python3 manage.py migrate
```

### 3. Create a Superuser

```bash
python3 manage.py createsuperuser
```

### 4. Run the Development Server

```bash
python3 manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`

### 5. Access the App

- **Login**: `http://127.0.0.1:8000/accounts/login/`
- **Register**: `http://127.0.0.1:8000/accounts/register/`
- **Admin Panel**: `http://127.0.0.1:8000/admin/`

## Project Structure

```
├── accounts/               # User authentication & profiles
├── members/                # Member & payment models, views, forms
├── payflow/                # Django project settings & URLs
├── reports/                # Dashboard, analytics, CSV export
├── static/                 # CSS & JavaScript
│   ├── css/style.css
│   └── js/main.js
├── templates/              # HTML templates
│   ├── base.html
│   ├── accounts/
│   ├── members/
│   └── reports/
└── manage.py
```

## Default Credentials

A default superuser is pre-created:
- **Username**: `admin`
- **Password**: `admin123`

## Apps

### Members
- `Member` model: name, email, phone, monthly due, start date, status tracking
- `Payment` model: member, date, amount, method, notes
- Smart ledger engine calculates advance payments, partial payments, and monthly allocation

### Accounts
- User registration and login
- Profile model with roles (admin, collector, viewer)

### Reports
- Dashboard with KPIs and monthly collection data
- Monthly payment matrix
- Status distribution report
- CSV export functionality
