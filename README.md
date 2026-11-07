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
- **Database**: SQLite (development), PostgreSQL (production)
- **Frontend**: Django templates with Bootstrap 5
- **Icons**: Bootstrap Icons
- **Static Files**: WhiteNoise
- **Deployment**: Vercel

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables (Optional for Development)

```bash
cp .env.example .env
```

Edit `.env` and set `DEBUG=True` for local development.

### 3. Run Migrations

```bash
python3 manage.py migrate
```

### 4. Create a Superuser

```bash
python3 manage.py createsuperuser
```

### 5. Run the Development Server

```bash
python3 manage.py runserver
```

The app will be available at `http://127.0.0.1:8000/`

### 6. Access the App

- **Login**: `http://127.0.0.1:8000/accounts/login/`
- **Register**: `http://127.0.0.1:8000/accounts/register/`
- **Admin Panel**: `http://127.0.0.1:8000/admin/`

## Deploy to Vercel

### Prerequisites

1. A [Vercel](https://vercel.com) account
2. A PostgreSQL database (e.g., [Neon](https://neon.tech), [Supabase](https://supabase.com), [Railway](https://railway.app), or any PostgreSQL provider)
3. [Vercel CLI](https://vercel.com/docs/cli) (optional, for local testing)

### Step 1: Set Up a PostgreSQL Database

Vercel's serverless environment has a read-only filesystem, so SQLite won't work. Create a PostgreSQL database and get the connection string (DATABASE_URL).

Example with [Neon](https://neon.tech) (free tier):
1. Sign up at neon.tech
2. Create a new project
3. Copy the connection string (format: `postgres://user:password@host:5432/dbname`)

### Step 2: Configure Environment Variables on Vercel

Go to your Vercel project settings → Environment Variables and add:

| Variable | Value | Example |
|----------|-------|---------|
| `SECRET_KEY` | Random secret key | Generate: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` | `False` |
| `ALLOWED_HOSTS` | Your Vercel domain | `your-app.vercel.app` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@host:5432/dbname` |
| `SECURE_SSL_REDIRECT` | `True` | `True` |

### Step 3: Deploy

**Option A — Via Vercel Dashboard (Recommended):**
1. Push your code to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your GitHub repository
4. Add the environment variables from Step 2
5. Click **Deploy** — Vercel detects the `vercel.json` and builds automatically

**Option B — Via Vercel CLI:**
```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel
```

### Step 4: Create a Superuser

After deployment, create a superuser via the Vercel CLI:
```bash
vercel exec --confirm python manage.py createsuperuser
```

Or connect to your database directly and create a user via Django shell.

### Project Files for Deployment

| File | Purpose |
|------|---------|
| `vercel.json` | Build and routing configuration |
| `build_files.sh` | Collects static files and runs migrations |
| `requirements.txt` | Python dependencies |
| `runtime.txt` | Python 3.12 runtime |
| `.gitignore` | Excludes sensitive files |
| `.env.example` | Template for environment variables |

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
