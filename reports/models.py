from django.db import models
from django.utils import timezone
from members.models import Member, Payment
from datetime import date


EXPENSE_CATEGORIES = [
    ('rent', 'Rent'),
    ('utilities', 'Utilities'),
    ('salaries', 'Salaries'),
    ('supplies', 'Supplies'),
    ('maintenance', 'Maintenance'),
    ('insurance', 'Insurance'),
    ('taxes', 'Taxes'),
    ('transport', 'Transport'),
    ('food', 'Food'),
    ('other', 'Other'),
]


class Expense(models.Model):
    """Expense record for a tenant — deducted from earnings."""
    tenant = models.ForeignKey(
        'accounts.Tenant', on_delete=models.CASCADE, related_name='expenses'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, choices=EXPENSE_CATEGORIES, default='other')
    date = models.DateField(default=date.today)
    description = models.TextField(blank=True, help_text='Details about this expense')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"₹{self.amount} - {self.get_category_display()} ({self.date})"


class ReportService:
    """Service class for generating reports and analytics — all methods scoped by tenant."""

    @staticmethod
    def get_dashboard_metrics(tenant):
        """Calculate dashboard KPIs for a specific tenant, including expense data."""
        today = date.today()
        members = Member.objects.filter(tenant=tenant, is_active=True)

        total_expected_ytd = 0
        total_collected = 0
        pending_dues = 0
        overdue_count = 0

        for member in members:
            months_since_start = (today.year - member.start_date.year) * 12 + (today.month - member.start_date.month) + 1
            if months_since_start < 0:
                months_since_start = 0
            expected = months_since_start * member.monthly_due
            total_expected_ytd += expected
            paid = member.total_paid
            total_collected += paid
            balance = max(0, expected - paid)
            pending_dues += balance
            if member.status in ('unpaid', 'behind'):
                overdue_count += 1

        collection_rate = 0
        if total_expected_ytd > 0:
            collection_rate = min(100, round((total_collected / total_expected_ytd) * 100))

        # Expense totals
        total_expenses = Expense.objects.filter(tenant=tenant).aggregate(total=models.Sum('amount'))['total'] or 0
        net_earnings = total_collected - total_expenses

        return {
            'total_expected_ytd': total_expected_ytd,
            'total_collected': total_collected,
            'pending_dues': pending_dues,
            'collection_rate': collection_rate,
            'overdue_count': overdue_count,
            'total_members': members.count(),
            'total_expenses': total_expenses,
            'net_earnings': net_earnings,
        }

    @staticmethod
    def get_monthly_chart_data(tenant, year=None):
        """Generate monthly chart data for a specific tenant."""
        if year is None:
            year = date.today().year

        months = [
            ('Jan', 1), ('Feb', 2), ('Mar', 3), ('Apr', 4),
            ('May', 5), ('Jun', 6), ('Jul', 7), ('Aug', 8),
            ('Sep', 9), ('Oct', 10), ('Nov', 11), ('Dec', 12),
        ]

        members = Member.objects.filter(tenant=tenant, is_active=True)
        chart_data = []

        today = date.today()
        current_month = today.month if year == today.year else 12

        for month_name, month_num in months:
            expected = 0
            collected = 0

            # Only count expected dues up to the current month
            if month_num <= current_month:
                for member in members:
                    # Check if member had started by this month
                    if member.start_date.year < year or (member.start_date.year == year and member.start_date.month <= month_num):
                        expected += member.monthly_due
                    month_payments = Payment.objects.filter(
                        member=member,
                        date__year=year,
                        date__month=month_num
                    ).aggregate(total=models.Sum('amount'))['total'] or 0
                    collected += month_payments

            chart_data.append({
                'month': month_name,
                'expected': expected,
                'collected': collected,
            })

        return chart_data

    @staticmethod
    def get_status_distribution(tenant):
        """Get member count by payment status for a specific tenant."""
        members = Member.objects.filter(tenant=tenant, is_active=True)
        distribution = {
            'up_to_date': 0,
            'advance': 0,
            'behind': 0,
            'unpaid': 0,
        }

        for member in members:
            status = member.status
            if status == 'up-to-date':
                distribution['up_to_date'] += 1
            elif status == 'advance':
                distribution['advance'] += 1
            elif status == 'behind':
                distribution['behind'] += 1
            elif status == 'unpaid':
                distribution['unpaid'] += 1

        return distribution

    @staticmethod
    def get_member_ledger(member):
        """Calculate monthly breakdown for a single member."""
        from datetime import date
        today = date.today()
        total_paid = member.total_paid
        remaining_pool = total_paid

        months = [
            ('Jan', 1), ('Feb', 2), ('Mar', 3), ('Apr', 4),
            ('May', 5), ('Jun', 6), ('Jul', 7), ('Aug', 8),
            ('Sep', 9), ('Oct', 10), ('Nov', 11), ('Dec', 12),
        ]

        current_month_idx = today.month - 1
        monthly_breakdown = []

        for month_name, month_num in months:
            due = member.monthly_due
            allocated = 0
            status = 'unpaid'

            start_year = member.start_date.year
            start_month = member.start_date.month
            if today.year == start_year and month_num < start_month:
                monthly_breakdown.append({
                    'month': month_name,
                    'due': due,
                    'allocated': 0,
                    'balance': 0,
                    'status': 'n/a',
                })
                continue

            if remaining_pool >= due:
                allocated = due
                remaining_pool -= due
                status = 'paid'
            elif remaining_pool > 0:
                allocated = remaining_pool
                remaining_pool = 0
                status = 'partial'
            else:
                allocated = 0
                status = 'overdue' if (today.year * 12 + month_num) <= (today.year * 12 + today.month) else 'unpaid'

            monthly_breakdown.append({
                'month': month_name,
                'due': due,
                'allocated': allocated,
                'balance': due - allocated,
                'status': status,
            })

        return {
            'total_paid': total_paid,
            'monthly_breakdown': monthly_breakdown,
            'current_balance_owed': member.current_balance_owed,
            'advance_balance': member.advance_balance,
            'overall_status': member.status,
        }

    @staticmethod
    def get_csv_export_data(tenant):
        """
        Generate comprehensive CSV export data for members of a specific tenant.
        Includes member info (total due up to current month, total paid, status)
        plus monthly matrix columns (months as columns, members as rows).
        """
        members = Member.objects.filter(tenant=tenant, is_active=True)
        rows = []
        for member in members:
            ledger = ReportService.get_member_ledger(member)
            row = {
                'name': member.name,
                'email': member.email or '',
                'monthly_due': member.monthly_due,
                'total_due': member.monthly_due * max(0, (date.today().year - member.start_date.year) * 12 + (date.today().month - member.start_date.month) + 1),
                'total_paid': member.total_paid,
                'balance_owed': member.current_balance_owed,
                'status': member.status,
            }
            # Add monthly matrix columns: each month's allocated amount and status
            for month in ledger['monthly_breakdown']:
                row[f'{month["month"]}_allocated'] = month['allocated']
                row[f'{month["month"]}_status'] = month['status']
            rows.append(row)
        return rows

    @staticmethod
    def get_monthly_matrix_csv(tenant):
        """Generate CSV export data for the monthly payment matrix of a specific tenant."""
        members = Member.objects.filter(tenant=tenant, is_active=True)
        rows = []
        for member in members:
            ledger = ReportService.get_member_ledger(member)
            row = {
                'name': member.name,
                'email': member.email or '',
                'monthly_due': member.monthly_due,
                'total_paid': member.total_paid,
                'balance_owed': member.current_balance_owed,
                'status': member.status,
            }
            for month in ledger['monthly_breakdown']:
                row[f'{month["month"]}_allocated'] = month['allocated']
                row[f'{month["month"]}_status'] = month['status']
            rows.append(row)
        return rows

    @staticmethod
    def get_member_yearly_history(member):
        """
        Get a member's full payment history grouped by year.
        Returns a list of year blocks, each containing monthly breakdown and year totals.
        """
        from collections import defaultdict

        months_label = [
            ('Jan', 1), ('Feb', 2), ('Mar', 3), ('Apr', 4),
            ('May', 5), ('Jun', 6), ('Jul', 7), ('Aug', 8),
            ('Sep', 9), ('Oct', 10), ('Nov', 11), ('Dec', 12),
        ]

        # Fetch all payments ordered by date
        all_payments = Payment.objects.filter(member=member).order_by('date')

        # Group payments by year
        payments_by_year = defaultdict(list)
        for p in all_payments:
            payments_by_year[p.date.year].append(p)

        # Determine the range of years to display
        start_year = member.start_date.year
        end_year = date.today().year
        # Also consider the latest payment year
        if all_payments:
            end_year = max(end_year, all_payments.last().date.year)

        years = []
        for year in range(start_year, end_year + 1):
            year_payments = payments_by_year.get(year, [])
            year_collected = sum(p.amount for p in year_payments)

            # Build monthly breakdown for this year
            monthly = []
            start_month = member.start_date.month
            for month_name, month_num in months_label:
                # Check if this month is before the member's start date
                if year == start_year and month_num < start_month:
                    monthly.append({
                        'month': month_name,
                        'month_num': month_num,
                        'due': 0,
                        'collected': 0,
                        'status': 'n/a',
                    })
                    continue

                due = member.monthly_due
                # Sum payments in this specific month/year
                collected = sum(
                    p.amount for p in year_payments
                    if p.date.month == month_num
                )

                if collected >= due:
                    status = 'paid'
                elif collected > 0:
                    status = 'partial'
                else:
                    status = 'unpaid'

                monthly.append({
                    'month': month_name,
                    'month_num': month_num,
                    'due': due,
                    'collected': collected,
                    'status': status,
                })

            # Calculate expected for this year — only up to the current month for the current year
            if year == start_year:
                months_active = 12 - member.start_date.month + 1
                year_expected = months_active * member.monthly_due
            elif year == date.today().year:
                # Current year: count only up to the current month
                if member.start_date.year == date.today().year:
                    # Started this year: from start_month to current month
                    months_active = date.today().month - member.start_date.month + 1
                else:
                    months_active = date.today().month
                year_expected = max(0, months_active) * member.monthly_due
            else:
                year_expected = 12 * member.monthly_due

            # Count statuses for this year
            paid_count = sum(1 for m in monthly if m['status'] == 'paid')
            partial_count = sum(1 for m in monthly if m['status'] == 'partial')
            unpaid_count = sum(1 for m in monthly if m['status'] == 'unpaid')

            # Get payment records for this year
            year_payment_records = [
                {'date': p.date, 'amount': p.amount, 'method': p.get_method_display(), 'note': p.note}
                for p in year_payments
            ]

            years.append({
                'year': year,
                'monthly': monthly,
                'year_expected': year_expected,
                'year_collected': year_collected,
                'year_balance': max(0, year_expected - year_collected),
                'paid_count': paid_count,
                'partial_count': partial_count,
                'unpaid_count': unpaid_count,
                'payment_records': year_payment_records,
            })

        return years

    @staticmethod
    def get_yearly_report(tenant, year):
        """
        Generate a comprehensive yearly report for all members of a tenant for a given year.
        Returns annual KPIs, monthly breakdown across all members, per-member data, and payment records.
        """
        from collections import defaultdict

        months_label = [
            ('Jan', 1), ('Feb', 2), ('Mar', 3), ('Apr', 4),
            ('May', 5), ('Jun', 6), ('Jul', 7), ('Aug', 8),
            ('Sep', 9), ('Oct', 10), ('Nov', 11), ('Dec', 12),
        ]

        members = Member.objects.filter(tenant=tenant, is_active=True)

        # Aggregate data for the year
        total_expected = 0
        total_collected = 0
        member_data_list = []
        all_payment_records = []

        for member in members:
            # Check if member was active during this year
            if member.start_date.year > year:
                continue

            # Calculate expected for this member in this year
            if member.start_date.year == year:
                # Started this year: from start_month to Dec (or current month if current year)
                if year == date.today().year:
                    months_active = max(0, date.today().month - member.start_date.month + 1)
                else:
                    months_active = 12 - member.start_date.month + 1
            else:
                # Was active all year (or at least the full year if past)
                if year == date.today().year:
                    months_active = date.today().month
                else:
                    months_active = 12

            member_expected = months_active * member.monthly_due
            total_expected += member_expected

            # Get payments for this member in this year
            year_payments = Payment.objects.filter(
                member=member,
                date__year=year
            ).order_by('date')

            member_collected = sum(p.amount for p in year_payments)
            total_collected += member_collected

            # Build monthly breakdown for this member
            monthly = []
            for month_name, month_num in months_label:
                if member.start_date.year == year and month_num < member.start_date.month:
                    monthly.append({
                        'month': month_name,
                        'month_num': month_num,
                        'due': 0,
                        'collected': 0,
                        'status': 'n/a',
                    })
                    continue

                due = member.monthly_due
                collected = sum(p.amount for p in year_payments if p.date.month == month_num)

                if collected >= due:
                    status = 'paid'
                elif collected > 0:
                    status = 'partial'
                else:
                    status = 'unpaid'

                monthly.append({
                    'month': month_name,
                    'month_num': month_num,
                    'due': due,
                    'collected': collected,
                    'status': status,
                })

            # Payment records for this member
            payment_records = [
                {'date': p.date, 'amount': p.amount, 'method': p.get_method_display(), 'note': p.note}
                for p in year_payments
            ]
            all_payment_records.extend([
                {
                    'member': member.name,
                    'date': p.date,
                    'amount': p.amount,
                    'method': p.get_method_display(),
                    'note': p.note,
                }
                for p in year_payments
            ])

            member_data_list.append({
                'member': member,
                'expected': member_expected,
                'collected': member_collected,
                'balance': max(0, member_expected - member_collected),
                'monthly': monthly,
                'payment_records': payment_records,
                'paid_months': sum(1 for m in monthly if m['status'] == 'paid'),
                'partial_months': sum(1 for m in monthly if m['status'] == 'partial'),
                'unpaid_months': sum(1 for m in monthly if m['status'] == 'unpaid'),
            })

        # Sort members by name
        member_data_list.sort(key=lambda x: x['member'].name.lower())

        # Sort all payment records by date
        all_payment_records.sort(key=lambda x: x['date'])

        # Monthly aggregation across all members
        monthly_summary = []
        for month_name, month_num in months_label:
            month_expected = sum(
                m['monthly'][month_num - 1]['due'] for m in member_data_list
            )
            month_collected = sum(
                m['monthly'][month_num - 1]['collected'] for m in member_data_list
            )
            monthly_summary.append({
                'month': month_name,
                'expected': month_expected,
                'collected': month_collected,
                'balance': max(0, month_expected - month_collected),
            })

        # Count statuses across all members
        total_paid_months = sum(m['paid_months'] for m in member_data_list)
        total_partial_months = sum(m['partial_months'] for m in member_data_list)
        total_unpaid_months = sum(m['unpaid_months'] for m in member_data_list)

        # Determine available years for navigation
        start_year = date.today().year
        end_year = date.today().year
        if members.exists():
            earliest = members.earliest('start_date').start_date.year
            start_year = min(start_year, earliest)
            # Also check payment dates
            earliest_payment = Payment.objects.filter(member__tenant=tenant).earliest('date')
            if earliest_payment:
                start_year = min(start_year, earliest_payment.date.year)

        available_years = list(range(start_year, end_year + 1))

        return {
            'year': year,
            'available_years': sorted(available_years, reverse=True),
            'total_members': len(member_data_list),
            'total_expected': total_expected,
            'total_collected': total_collected,
            'total_balance': max(0, total_expected - total_collected),
            'collection_rate': min(100, round((total_collected / total_expected) * 100)) if total_expected > 0 else 0,
            'monthly_summary': monthly_summary,
            'member_data': member_data_list,
            'all_payment_records': all_payment_records,
            'total_paid_months': total_paid_months,
            'total_partial_months': total_partial_months,
            'total_unpaid_months': total_unpaid_months,
        }
