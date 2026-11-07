import csv
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django import forms
from .models import ReportService, Expense, EXPENSE_CATEGORIES
from members.models import Member


def _get_current_tenant(request):
    """
    Return the active tenant for the current request.
    - Superadmins: use the session-stored tenant (switchable).
    - Everyone else: use their profile's default tenant.
    """
    from accounts.models import Tenant
    profile = request.user.profile
    if profile.is_superadmin:
        tenant_id = request.session.get('current_tenant_id')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(pk=tenant_id, is_active=True)
                return tenant
            except Tenant.DoesNotExist:
                pass
        return profile.tenant
    return profile.tenant


@login_required
def dashboard(request):
    """Main dashboard with KPIs and charts — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    metrics = ReportService.get_dashboard_metrics(tenant)
    chart_data = ReportService.get_monthly_chart_data(tenant)
    status_dist = ReportService.get_status_distribution(tenant)

    # Overdue members for action-required section
    overdue_members = Member.objects.filter(tenant=tenant, is_active=True).order_by('-created_at')

    context = {
        'metrics': metrics,
        'chart_data': chart_data,
        'status_distribution': status_dist,
        'overdue_members': overdue_members,
        'tenant': tenant,
    }
    return render(request, 'reports/dashboard.html', context)


@login_required
def monthly_matrix(request):
    """Monthly payment matrix view — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    members = Member.objects.filter(tenant=tenant, is_active=True)
    matrix = []

    for member in members:
        ledger = ReportService.get_member_ledger(member)
        matrix.append({
            'member': member,
            'ledger': ledger,
        })

    return render(request, 'reports/monthly_matrix.html', {'matrix': matrix, 'tenant': tenant})


@login_required
def status_report(request):
    """Status distribution report — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    status_dist = ReportService.get_status_distribution(tenant)
    members = Member.objects.filter(tenant=tenant, is_active=True)

    grouped = {
        'up_to_date': [],
        'advance': [],
        'behind': [],
        'unpaid': [],
    }

    for member in members:
        status = member.status
        if status == 'up-to-date':
            grouped['up_to_date'].append(member)
        elif status in grouped:
            grouped[status].append(member)

    context = {
        'status_distribution': status_dist,
        'grouped_members': grouped,
        'tenant': tenant,
    }
    return render(request, 'reports/status_report.html', context)


@login_required
def export_csv(request):
    """
    Export comprehensive member report as CSV — scoped to user's tenant.
    Includes member info (total due up to current month, total paid, status)
    plus monthly matrix columns (months as columns, members as rows).
    """
    tenant = _get_current_tenant(request)
    data = ReportService.get_csv_export_data(tenant)

    response = HttpResponse(content_type='text/csv')
    from datetime import date
    today = date.today().isoformat()
    response['Content-Disposition'] = f'attachment; filename={tenant.name}_Member_Report_{today}.csv'

    writer = csv.writer(response)

    # Build headers: member info + monthly matrix columns
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    headers = [
        'Member Name', 'Email', 'Monthly Due (₹)', 'Total Due (₹)',
        'Total Paid (₹)', 'Balance Owed (₹)', 'Status'
    ]
    for m in months:
        headers.append(f'{m} (₹)')
        headers.append(f'{m} Status')
    writer.writerow(headers)

    # Data rows: member info + monthly matrix
    for row in data:
        writer.writerow([
            row['name'],
            row['email'],
            f"₹{row['monthly_due']:.2f}",
            f"₹{row['total_due']:.2f}",
            f"₹{row['total_paid']:.2f}",
            f"₹{row['balance_owed']:.2f}",
            row['status'],
        ] + [
            f"₹{row.get(f'{m}_allocated', 0):.2f}" if row.get(f'{m}_allocated', 0) > 0 else ''
            for m in months
        ] + [
            row.get(f'{m}_status', '')
            for m in months
        ])

    return response


@login_required
def export_monthly_matrix_csv(request):
    """Export monthly payment matrix as CSV — scoped to user's tenant."""
    from django.shortcuts import redirect
    from django.contrib import messages
    from datetime import date

    tenant = _get_current_tenant(request)
    data = ReportService.get_monthly_matrix_csv(tenant)

    if not data:
        messages.info(request, 'No data to export. Add members first.')
        return redirect('reports:monthly_matrix')

    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    today = date.today().isoformat()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={tenant.name}_Monthly_Matrix_{today}.csv'
    writer = csv.writer(response)

    # Header row: member info + 12 months of allocated amounts and statuses
    headers = ['Member Name', 'Email', 'Monthly Due (₹)', 'Total Paid (₹)', 'Balance Owed (₹)', 'Status']
    for m in months:
        headers.append(f'{m} Allocated (₹)')
        headers.append(f'{m} Status')
    writer.writerow(headers)

    # Data rows
    for row in data:
        writer.writerow([
            row['name'],
            row['email'],
            f"₹{row['monthly_due']:.2f}",
            f"₹{row['total_paid']:.2f}",
            f"₹{row['balance_owed']:.2f}",
            row['status'],
        ] + [
            f"₹{row.get(f'{m}_allocated', 0):.2f}" if row.get(f'{m}_allocated', 0) > 0 else ''
            for m in months
        ] + [
            row.get(f'{m}_status', '')
            for m in months
        ])

    return response


@login_required
def yearly_history(request, member_pk):
    """View a member's full year-by-year payment history — read-only."""
    from django.shortcuts import get_object_or_404
    from django.contrib import messages

    tenant = _get_current_tenant(request)
    member = get_object_or_404(Member, pk=member_pk, tenant=tenant)

    years = ReportService.get_member_yearly_history(member)

    # Calculate grand totals across all years
    grand_expected = sum(y['year_expected'] for y in years)
    grand_collected = sum(y['year_collected'] for y in years)
    grand_balance = max(0, grand_expected - grand_collected)

    context = {
        'member': member,
        'years': years,
        'grand_expected': grand_expected,
        'grand_collected': grand_collected,
        'grand_balance': grand_balance,
        'tenant': tenant,
    }
    return render(request, 'reports/yearly_history.html', context)


@login_required
def yearly_report(request, year=None):
    """View a comprehensive yearly report for all members — tenant-scoped."""
    from datetime import date

    tenant = _get_current_tenant(request)
    if year is None:
        year = date.today().year

    try:
        year = int(year)
    except (ValueError, TypeError):
        year = date.today().year

    report = ReportService.get_yearly_report(tenant, year)

    context = {
        'report': report,
        'tenant': tenant,
    }
    return render(request, 'reports/yearly_report.html', context)


@login_required
def export_yearly_report_csv(request, year=None):
    """Export yearly report as CSV — tenant-scoped."""
    from datetime import date
    from django.shortcuts import redirect
    from django.contrib import messages

    tenant = _get_current_tenant(request)
    if year is None:
        year = date.today().year

    try:
        year = int(year)
    except (ValueError, TypeError):
        year = date.today().year

    report = ReportService.get_yearly_report(tenant, year)

    if not report['member_data']:
        messages.info(request, f'No data for year {year}.')
        return redirect('reports:yearly_report', year=year)

    today = date.today().isoformat()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={tenant.name}_Yearly_Report_{year}_{today}.csv'

    writer = csv.writer(response)

    # Header: member info + 12 months + totals
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    headers = ['Member Name', 'Monthly Due (₹)', 'Expected (₹)', 'Collected (₹)', 'Balance (₹)', 'Paid Months', 'Partial Months', 'Unpaid Months']
    for m in months:
        headers.append(f'{m} (₹)')
        headers.append(f'{m} Status')
    writer.writerow(headers)

    # Data rows
    for item in report['member_data']:
        writer.writerow([
            item['member'].name,
            f"₹{item['member'].monthly_due:.2f}",
            f"₹{item['expected']:.2f}",
            f"₹{item['collected']:.2f}",
            f"₹{item['balance']:.2f}",
            item['paid_months'],
            item['partial_months'],
            item['unpaid_months'],
        ] + [
            f"₹{item['monthly'][i]['collected']:.2f}" if item['monthly'][i]['collected'] > 0 else ''
            for i in range(12)
        ] + [
            item['monthly'][i]['status']
            for i in range(12)
        ])

    return response


class ExpenseForm(forms.ModelForm):
    """Form for booking expenses."""
    class Meta:
        model = Expense
        fields = ['amount', 'category', 'date', 'description']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control-custom',
                'placeholder': 'Enter amount',
                'step': '0.01',
                'min': '0.01',
            }),
            'category': forms.Select(attrs={'class': 'form-control-custom'}),
            'date': forms.DateInput(attrs={
                'class': 'form-control-custom',
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control-custom',
                'rows': 3,
                'placeholder': 'Details about this expense...',
            }),
        }


@login_required
def expense_list(request):
    """List all expenses for the current tenant."""
    tenant = _get_current_tenant(request)
    expenses = Expense.objects.filter(tenant=tenant).order_by('-date', '-created_at')

    # Filter by category if provided
    category = request.GET.get('category', '')
    if category:
        expenses = expenses.filter(category=category)

    # Filter by year if provided
    year = request.GET.get('year', '')
    if year:
        expenses = expenses.filter(date__year=year)

    # Calculate totals
    total_expenses = Expense.objects.filter(tenant=tenant).aggregate(total=models.Sum('amount'))['total'] or 0
    if category:
        filtered_total = expenses.aggregate(total=models.Sum('amount'))['total'] or 0
    else:
        filtered_total = total_expenses

    # Group by category for summary
    category_summary = {}
    for exp in Expense.objects.filter(tenant=tenant):
        cat = exp.category
        if cat not in category_summary:
            category_summary[cat] = 0
        category_summary[cat] += exp.amount

    # Dashboard metrics for net earnings display
    metrics = ReportService.get_dashboard_metrics(tenant)

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'filtered_total': filtered_total,
        'category_summary': category_summary,
        'EXPENSE_CATEGORIES': EXPENSE_CATEGORIES,
        'selected_category': category,
        'selected_year': year,
        'metrics': metrics,
        'tenant': tenant,
    }
    return render(request, 'reports/expense_list.html', context)


@login_required
def expense_create(request):
    """Create a new expense record."""
    tenant = _get_current_tenant(request)

    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.tenant = tenant
            expense.save()
            messages.success(request, f'Expense of ₹{expense.amount} ({expense.get_category_display()}) recorded!')
            return redirect('reports:expense_list')
    else:
        form = ExpenseForm()

    context = {
        'form': form,
        'tenant': tenant,
    }
    return render(request, 'reports/expense_form.html', context)


@login_required
def expense_delete(request, expense_pk):
    """Delete an expense record."""
    tenant = _get_current_tenant(request)
    expense = get_object_or_404(Expense, pk=expense_pk, tenant=tenant)

    if request.method == 'POST':
        amount = expense.amount
        expense.delete()
        messages.success(request, f'Expense of ₹{amount} deleted!')
        return redirect('reports:expense_list')

    context = {
        'expense': expense,
        'tenant': tenant,
    }
    return render(request, 'reports/expense_confirm_delete.html', context)
