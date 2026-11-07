from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Tenant
from members.models import Member, Payment
from reports.models import ReportService


class ReportServiceTest(TestCase):
    """Tests for the ReportService class methods."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='Report Corp')
        self.other_tenant = Tenant.objects.create(name='Other Report Corp')
        # Member started 2 months ago, due 1000/month
        self.start_date = date.today().replace(day=1) - timedelta(days=60)
        self.member1 = Member.objects.create(
            tenant=self.tenant, name='Paid Member', monthly_due=1000, start_date=self.start_date
        )
        # Paid 3000 for 3 months (including current month)
        Payment.objects.create(member=self.member1, amount=3000, date=self.start_date + timedelta(days=15))

        self.member2 = Member.objects.create(
            tenant=self.tenant, name='Unpaid Member', monthly_due=1000, start_date=self.start_date
        )

        self.member3 = Member.objects.create(
            tenant=self.tenant, name='Partial Member', monthly_due=1000, start_date=self.start_date
        )
        Payment.objects.create(member=self.member3, amount=500, date=self.start_date + timedelta(days=15))

        # Member in another tenant
        self.other_member = Member.objects.create(
            tenant=self.other_tenant, name='Other Member', monthly_due=500, start_date=self.start_date
        )

    def test_get_dashboard_metrics(self):
        metrics = ReportService.get_dashboard_metrics(self.tenant)
        self.assertIn('total_expected_ytd', metrics)
        self.assertIn('total_collected', metrics)
        self.assertIn('pending_dues', metrics)
        self.assertIn('collection_rate', metrics)
        self.assertIn('overdue_count', metrics)
        self.assertIn('total_members', metrics)
        self.assertEqual(metrics['total_members'], 3)

    def test_dashboard_metrics_total_collected(self):
        metrics = ReportService.get_dashboard_metrics(self.tenant)
        # member1 paid 3000, member3 paid 500 = 3500
        self.assertEqual(metrics['total_collected'], Decimal('3500'))

    def test_dashboard_metrics_overdue_count(self):
        metrics = ReportService.get_dashboard_metrics(self.tenant)
        # unpaid + behind = 2 (member2 unpaid, member3 behind)
        # member1 is up-to-date (paid 3000 for 3 months)
        self.assertEqual(metrics['overdue_count'], 2)

    def test_dashboard_metrics_collection_rate(self):
        metrics = ReportService.get_dashboard_metrics(self.tenant)
        self.assertIsInstance(metrics['collection_rate'], int)
        self.assertGreaterEqual(metrics['collection_rate'], 0)
        self.assertLessEqual(metrics['collection_rate'], 100)

    def test_dashboard_metrics_empty_tenant(self):
        empty_tenant = Tenant.objects.create(name='Empty Corp')
        metrics = ReportService.get_dashboard_metrics(empty_tenant)
        self.assertEqual(metrics['total_members'], 0)
        self.assertEqual(metrics['total_collected'], 0)
        self.assertEqual(metrics['collection_rate'], 0)

    def test_dashboard_metrics_tenant_isolation(self):
        metrics = ReportService.get_dashboard_metrics(self.tenant)
        other_metrics = ReportService.get_dashboard_metrics(self.other_tenant)
        self.assertEqual(metrics['total_members'], 3)
        self.assertEqual(other_metrics['total_members'], 1)

    def test_get_monthly_chart_data(self):
        chart_data = ReportService.get_monthly_chart_data(self.tenant)
        self.assertEqual(len(chart_data), 12)
        self.assertEqual(chart_data[0]['month'], 'Jan')
        self.assertEqual(chart_data[11]['month'], 'Dec')

    def test_monthly_chart_data_structure(self):
        chart_data = ReportService.get_monthly_chart_data(self.tenant)
        for entry in chart_data:
            self.assertIn('month', entry)
            self.assertIn('expected', entry)
            self.assertIn('collected', entry)

    def test_monthly_chart_data_with_payments(self):
        # Create a payment in a specific month
        Payment.objects.create(member=self.member1, amount=1000, date=date(2026, 5, 15))
        chart_data = ReportService.get_monthly_chart_data(self.tenant, year=2026)
        may_data = [d for d in chart_data if d['month'] == 'May'][0]
        self.assertGreater(may_data['collected'], 0)

    def test_get_status_distribution(self):
        dist = ReportService.get_status_distribution(self.tenant)
        self.assertIn('up_to_date', dist)
        self.assertIn('advance', dist)
        self.assertIn('behind', dist)
        self.assertIn('unpaid', dist)
        total = dist['up_to_date'] + dist['advance'] + dist['behind'] + dist['unpaid']
        self.assertEqual(total, 3)

    def test_status_distribution_values(self):
        dist = ReportService.get_status_distribution(self.tenant)
        # member1: up-to-date (paid 3000 for 3 months), member2: unpaid, member3: behind
        self.assertGreater(dist['up_to_date'], 0)
        self.assertGreater(dist['unpaid'], 0)
        self.assertGreater(dist['behind'], 0)

    def test_status_distribution_empty_tenant(self):
        empty_tenant = Tenant.objects.create(name='Empty Dist Corp')
        dist = ReportService.get_status_distribution(empty_tenant)
        self.assertEqual(dist['up_to_date'], 0)
        self.assertEqual(dist['advance'], 0)
        self.assertEqual(dist['behind'], 0)
        self.assertEqual(dist['unpaid'], 0)

    def test_get_member_ledger(self):
        ledger = ReportService.get_member_ledger(self.member1)
        self.assertIn('total_paid', ledger)
        self.assertIn('monthly_breakdown', ledger)
        self.assertIn('current_balance_owed', ledger)
        self.assertIn('advance_balance', ledger)
        self.assertIn('overall_status', ledger)
        self.assertEqual(len(ledger['monthly_breakdown']), 12)

    def test_member_ledger_breakdown_structure(self):
        ledger = ReportService.get_member_ledger(self.member1)
        for entry in ledger['monthly_breakdown']:
            self.assertIn('month', entry)
            self.assertIn('due', entry)
            self.assertIn('allocated', entry)
            self.assertIn('balance', entry)
            self.assertIn('status', entry)

    def test_member_ledger_paid_status(self):
        ledger = ReportService.get_member_ledger(self.member1)
        # member1 paid 3000 for 3 months (including current month) = up-to-date
        self.assertEqual(ledger['overall_status'], 'up-to-date')

    def test_member_ledger_unpaid_status(self):
        ledger = ReportService.get_member_ledger(self.member2)
        self.assertEqual(ledger['overall_status'], 'unpaid')

    def test_get_csv_export_data(self):
        data = ReportService.get_csv_export_data(self.tenant)
        self.assertEqual(len(data), 3)
        for row in data:
            self.assertIn('name', row)
            self.assertIn('email', row)
            self.assertIn('monthly_due', row)
            self.assertIn('total_due', row)
            self.assertIn('total_paid', row)
            self.assertIn('balance_owed', row)
            self.assertIn('status', row)
            # Verify monthly matrix columns are present
            self.assertIn('Jan_allocated', row)
            self.assertIn('Jan_status', row)
            self.assertIn('Dec_allocated', row)
            self.assertIn('Dec_status', row)

    def test_csv_export_tenant_isolation(self):
        data = ReportService.get_csv_export_data(self.tenant)
        other_data = ReportService.get_csv_export_data(self.other_tenant)
        self.assertEqual(len(data), 3)
        self.assertEqual(len(other_data), 1)
        names = [row['name'] for row in data]
        self.assertNotIn('Other Member', names)

    def test_csv_export_excludes_inactive(self):
        self.member2.is_active = False
        self.member2.save()
        data = ReportService.get_csv_export_data(self.tenant)
        names = [row['name'] for row in data]
        self.assertNotIn('Unpaid Member', names)


class DashboardViewTest(TestCase):
    """Tests for the dashboard report view."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Dashboard Corp')
        self.user = User.objects.create_user(username='dashuser', password='pass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()
        self.member = Member.objects.create(
            tenant=self.tenant, name='Dash Member', monthly_due=1000
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('reports:dashboard'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("reports:dashboard")}')

    def test_dashboard_shows_metrics(self):
        self.client.login(username='dashuser', password='pass')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('metrics', response.context)
        self.assertIn('chart_data', response.context)
        self.assertIn('status_distribution', response.context)

    def test_dashboard_shows_tenant_name(self):
        self.client.login(username='dashuser', password='pass')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertContains(response, 'Dashboard Corp')


class MonthlyMatrixViewTest(TestCase):
    """Tests for the monthly matrix view."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Matrix Corp')
        self.user = User.objects.create_user(username='matrixuser', password='pass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()
        self.member = Member.objects.create(
            tenant=self.tenant, name='Matrix Member', monthly_due=1000
        )

    def test_monthly_matrix_requires_login(self):
        response = self.client.get(reverse('reports:monthly_matrix'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("reports:monthly_matrix")}')

    def test_monthly_matrix_shows_members(self):
        self.client.login(username='matrixuser', password='pass')
        response = self.client.get(reverse('reports:monthly_matrix'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('matrix', response.context)

    def test_monthly_matrix_tenant_isolation(self):
        other_tenant = Tenant.objects.create(name='Other Matrix')
        other_member = Member.objects.create(tenant=other_tenant, name='Other Member', monthly_due=500)
        self.client.login(username='matrixuser', password='pass')
        response = self.client.get(reverse('reports:monthly_matrix'))
        matrix = response.context['matrix']
        member_names = [entry['member'].name for entry in matrix]
        self.assertIn('Matrix Member', member_names)
        self.assertNotIn('Other Member', member_names)


class StatusReportViewTest(TestCase):
    """Tests for the status report view."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Status Corp')
        self.user = User.objects.create_user(username='statususer', password='pass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()
        self.member = Member.objects.create(
            tenant=self.tenant, name='Status Member', monthly_due=1000
        )

    def test_status_report_requires_login(self):
        response = self.client.get(reverse('reports:status_report'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("reports:status_report")}')

    def test_status_report_shows_distribution(self):
        self.client.login(username='statususer', password='pass')
        response = self.client.get(reverse('reports:status_report'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('status_distribution', response.context)
        self.assertIn('grouped_members', response.context)

    def test_status_report_groups_members(self):
        self.client.login(username='statususer', password='pass')
        response = self.client.get(reverse('reports:status_report'))
        grouped = response.context['grouped_members']
        self.assertIn('up_to_date', grouped)
        self.assertIn('advance', grouped)
        self.assertIn('behind', grouped)
        self.assertIn('unpaid', grouped)


class CsvExportViewTest(TestCase):
    """Tests for the CSV export view."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Export Corp')
        self.user = User.objects.create_user(username='exportuser', password='pass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()
        self.member = Member.objects.create(
            tenant=self.tenant, name='Export Member', monthly_due=1000
        )

    def test_export_requires_login(self):
        response = self.client.get(reverse('reports:export_csv'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("reports:export_csv")}')

    def test_export_returns_csv(self):
        self.client.login(username='exportuser', password='pass')
        response = self.client.get(reverse('reports:export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_export_content_disposition(self):
        self.client.login(username='exportuser', password='pass')
        response = self.client.get(reverse('reports:export_csv'))
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertIn('Export Corp', response['Content-Disposition'])

    def test_export_csv_headers(self):
        self.client.login(username='exportuser', password='pass')
        response = self.client.get(reverse('reports:export_csv'))
        content = response.content.decode('utf-8')
        self.assertIn('Member Name', content)
        self.assertIn('Monthly Due', content)
        self.assertIn('Total Due', content)
        self.assertIn('Total Paid', content)
        self.assertIn('Balance Owed', content)
        self.assertIn('Status', content)
        # Monthly matrix columns should be present
        self.assertIn('Jan', content)
        self.assertIn('Dec', content)

    def test_export_csv_data(self):
        self.client.login(username='exportuser', password='pass')
        response = self.client.get(reverse('reports:export_csv'))
        content = response.content.decode('utf-8')
        self.assertIn('Export Member', content)

    def test_export_tenant_isolation(self):
        other_tenant = Tenant.objects.create(name='Other Export')
        other_member = Member.objects.create(tenant=other_tenant, name='Other Export Member', monthly_due=500)
        self.client.login(username='exportuser', password='pass')
        response = self.client.get(reverse('reports:export_csv'))
        content = response.content.decode('utf-8')
        self.assertIn('Export Member', content)
        self.assertNotIn('Other Export Member', content)


class SuperadminReportViewsTest(TestCase):
    """Tests that report views respect superadmin tenant switching."""

    def setUp(self):
        self.client = Client()
        self.tenant1 = Tenant.objects.create(name='Report Switch T1')
        self.tenant2 = Tenant.objects.create(name='Report Switch T2')
        self.superuser = User.objects.create_user(username='reportsuper', password='pass')
        self.superuser.profile.tenant = self.tenant1
        self.superuser.profile.is_superadmin = True
        self.superuser.profile.save()
        self.member1 = Member.objects.create(tenant=self.tenant1, name='Report M1', monthly_due=1000)
        self.member2 = Member.objects.create(tenant=self.tenant2, name='Report M2', monthly_due=500)

    def test_dashboard_default_tenant(self):
        self.client.login(username='reportsuper', password='pass')
        response = self.client.get(reverse('reports:dashboard'))
        metrics = response.context['metrics']
        self.assertEqual(metrics['total_members'], 1)

    def test_dashboard_after_switch(self):
        self.client.login(username='reportsuper', password='pass')
        # Switch tenant via POST
        self.client.post(reverse('accounts:tenant_switch'), {'tenant_id': self.tenant2.pk})
        response = self.client.get(reverse('reports:dashboard'))
        metrics = response.context['metrics']
        self.assertEqual(metrics['total_members'], 1)
        # Should show tenant2's member
        self.assertContains(response, 'Report M2')

    def test_csv_export_after_switch(self):
        # Use client with session to persist the tenant switch
        self.client.login(username='reportsuper', password='pass')
        # Switch tenant via POST
        self.client.post(reverse('accounts:tenant_switch'), {'tenant_id': self.tenant2.pk})
        response = self.client.get(reverse('reports:export_csv'))
        content = response.content.decode('utf-8')
        # After switching to tenant2, should only see tenant2's member
        self.assertIn('Report M2', content)
        self.assertNotIn('Report M1', content)
