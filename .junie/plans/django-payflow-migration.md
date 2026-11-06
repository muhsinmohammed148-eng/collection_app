---
sessionId: session-261106-154251-1ela
---

# Testing

### Validation Approach
After implementation, verify each feature by:
1. Starting the Django development server
2. Creating test users with different roles
3. Testing each view and action as different user roles
4. Verifying database persistence across server restarts

### Key Scenarios
- **Authentication**: Login with valid/invalid credentials, logout, password change
- **Role enforcement**: Admin can delete members, collector cannot, viewer is read-only
- **Member CRUD**: Add member → verify in DB → edit → verify changes → delete → verify removed
- **Payment recording**: Record payment → verify auto-allocation → check member status updated
- **Dashboard metrics**: Verify totals match sum of member data
- **Monthly matrix**: Verify each cell shows correct status based on payment allocation
- **CSV export**: Download and verify CSV content matches member list
- **Mobile responsiveness**: Test on narrow viewport (320px) — hamburger menu works, cards stack, table scrolls

### Edge Cases
- Payment amount exceeds monthly due (advance payment)
- Partial payment covering multiple months
- Member with no payments (unpaid status)
- Empty member list (no results state)
- Search with no matches
- Concurrent login from different browsers
- Password reset email flow

### Test Changes
- Django `manage.py test` with test cases for:
  - `accounts/tests.py`: Login, role checks, user creation
  - `members/tests.py`: Member CRUD, payment recording, ledger calculation
  - `reports/tests.py`: Dashboard metrics, matrix data, CSV export

# Delivery Steps

### * Step 1: Set up Django project with PostgreSQL and custom user model
Initialize the Django project structure with all apps, database configuration, and authentication foundation.
- Create Django project `payflow` with apps: `accounts`, `members`, `reports`
- Configure PostgreSQL in `settings.py` (DATABASES, static files, templates)
- Create `CustomUser` model extending `AbstractUser` with `role` field (admin/collector/viewer) and `full_name`
- Create `accounts/forms.py` with `CustomUserCreationForm` and `LoginForm`
- Create `accounts/views.py` with login, logout, and registration views
- Create `accounts/urls.py` with URL patterns
- Create `templates/base.html` with header, desktop nav, mobile hamburger menu, and footer
- Create `static/css/base.css` with CSS reset, typography, and color variables
- Create `requirements.txt` with Django and psycopg2
- Run initial migrations

###   Step 2: Implement Member and Payment models with business logic
Build the core data models and the payment allocation engine that powers the entire app.
- Create `Member` model (name, email, phone, monthly_due, start_date, created_by)
- Create `Payment` model (member FK, date, amount, method, note, recorded_by)
- Implement `calculate_ledger()` in `members/services.py` — port of React's `calculateMemberLedger()` with month-by-month allocation
- Implement `auto_allocate_payment()` helper for the allocation engine
- Create `MemberForm` and `PaymentForm` in `members/forms.py`
- Create member CRUD views (list, add, edit, delete) in `members/views.py` with `@role_required` decorators
- Create `members/urls.py`
- Create templates: `members/member_list.html`, `members/member_form.html`, `members/payment_form.html`
- Run migrations for member models

###   Step 3: Build dashboard with metrics and monthly matrix
Implement the analytics dashboard and the monthly payment breakdown matrix view.
- Create `reports/services.py` with `aggregate_metrics()` — total collected, collection rate, pending dues, overdue count
- Implement `monthly_chart_data()` for trend data
- Create `dashboard` view in `reports/views.py` passing metrics to template
- Create `matrix` view with per-member per-month status data
- Create `csv_export` view with streaming CSV response
- Create `reports/urls.py`
- Create `templates/reports/dashboard.html` with metric cards, overdue list, and HTML/CSS bar charts
- Create `templates/reports/matrix.html` with responsive table (horizontal scroll on mobile, sticky first column)
- Wire all URLs in project-level `urls.py`

###   Step 4: Implement custom CSS with mobile-responsive design
Create the complete custom CSS stylesheet for a polished, mobile-first responsive design.
- Create `static/css/layout.css` — header sticky positioning, desktop nav, mobile hamburger menu with toggle, main container with max-width
- Create `static/css/components.css` — metric cards, member cards grid, status badges (paid/advance/overdue), buttons, forms, modals, table styles
- Create `static/css/responsive.css` — mobile-first breakpoints (320px base, 768px tablet, 1024px desktop), card grid columns, hamburger menu visibility, table horizontal scroll
- Create `static/js/app.js` — mobile menu toggle, modal open/close
- Update `templates/base.html` to include all CSS and JS
- Style login page: `templates/accounts/login.html`
- Test responsive design on multiple viewport sizes

###   Step 5: Add Django admin panel and finalize integration
Configure Django admin, add password management, and perform final integration testing.
- Register `CustomUser`, `Member`, and `Payment` in `admin.py` with custom admin classes
- Configure `accounts/admin.py` with role-based filtering and search
- Add password change and password reset views (Django built-in)
- Create `templates/accounts/password_change.html` and related templates
- Add Django messages framework for success/error feedback
- Create superuser and test all roles:
  - Admin: full CRUD on members, user management, dashboard access
  - Collector: record payments, view members and dashboard, no delete
  - Viewer: read-only dashboard and member list
- Verify CSV export functionality
- Final mobile responsiveness check on all pages
- Create `README.md` with setup instructions