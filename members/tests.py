from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import Tenant
from members.models import Member, Payment
from members.forms import MemberForm, PaymentForm


class MemberModelTest(TestCase):
    """Tests for the Member model and its computed properties."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='Member Test Corp')

    def _create_member(self, name='Test Member', monthly_due=1000, start_date=None, is_active=True):
        if start_date is None:
            start_date = date.today()
        return Member.objects.create(
            tenant=self.tenant,
            name=name,
            monthly_due=monthly_due,
            start_date=start_date,
            is_active=is_active,
        )

    def test_create_member(self):
        member = self._create_member()
        self.assertEqual(str(member), 'Test Member (Member Test Corp)')
        self.assertTrue(member.is_active)

    def test_member_ordering(self):
        self._create_member(name='Zebra')
        self._create_member(name='Alpha')
        self.assertEqual(
            list(Member.objects.filter(tenant=self.tenant).values_list('name', flat=True)),
            ['Alpha', 'Zebra']
        )

    def test_total_paid_no_payments(self):
        member = self._create_member()
        self.assertEqual(member.total_paid, 0)

    def test_total_paid_with_payments(self):
        member = self._create_member()
        Payment.objects.create(member=member, amount=500, date=date.today())
        Payment.objects.create(member=member, amount=300, date=date.today())
        self.assertEqual(member.total_paid, Decimal('800'))

    def test_current_balance_owed_fully_paid(self):
        # Start 2 months ago, due 1000/month = 3 months expected (including current month)
        start = date.today().replace(day=1) - timedelta(days=60)
        member = self._create_member(start_date=start)
        Payment.objects.create(member=member, amount=3000, date=start + timedelta(days=15))
        self.assertEqual(member.current_balance_owed, 0)

    def test_current_balance_owed_partial(self):
        start = date.today().replace(day=1) - timedelta(days=60)
        member = self._create_member(monthly_due=1000, start_date=start)
        Payment.objects.create(member=member, amount=1000, date=start + timedelta(days=15))
        # Expected ~2000, paid 1000, owed ~1000
        self.assertGreater(member.current_balance_owed, 0)

    def test_current_balance_owed_no_payments(self):
        start = date.today().replace(day=1) - timedelta(days=60)
        member = self._create_member(monthly_due=1000, start_date=start)
        self.assertGreater(member.current_balance_owed, 0)

    def test_advance_balance_overpayment(self):
        start = date.today().replace(day=1) - timedelta(days=30)
        member = self._create_member(monthly_due=1000, start_date=start)
        Payment.objects.create(member=member, amount=5000, date=start + timedelta(days=15))
        self.assertGreater(member.advance_balance, 0)

    def test_advance_balance_no_overpayment(self):
        # Member started today, 1 month expected (current month included) = 1000
        # Paid 1500, so advance = 1500 - 1000 = 500
        member = self._create_member()
        Payment.objects.create(member=member, amount=1500, date=date.today())
        self.assertEqual(member.advance_balance, Decimal('500'))

    def test_advance_balance_zero_when_no_payment(self):
        member = self._create_member()
        self.assertEqual(member.advance_balance, 0)

    def test_status_up_to_date(self):
        # Member just created, 1 month expected (current month included), paid in full
        member = self._create_member(start_date=date.today())
        Payment.objects.create(member=member, amount=1000, date=date.today())
        self.assertEqual(member.status, 'up-to-date')

    def test_status_unpaid(self):
        start = date.today().replace(day=1) - timedelta(days=60)
        member = self._create_member(start_date=start)
        self.assertEqual(member.status, 'unpaid')

    def test_status_behind(self):
        start = date.today().replace(day=1) - timedelta(days=60)
        member = self._create_member(monthly_due=1000, start_date=start)
        Payment.objects.create(member=member, amount=500, date=start + timedelta(days=15))
        self.assertEqual(member.status, 'behind')

    def test_status_advance(self):
        start = date.today().replace(day=1) - timedelta(days=30)
        member = self._create_member(monthly_due=1000, start_date=start)
        Payment.objects.create(member=member, amount=5000, date=start + timedelta(days=15))
        self.assertEqual(member.status, 'advance')

    def test_tenant_isolation(self):
        other_tenant = Tenant.objects.create(name='Other Corp')
        self._create_member(name='Tenant1 Member')
        Member.objects.create(tenant=other_tenant, name='Tenant2 Member', monthly_due=500)
        self.assertEqual(Member.objects.filter(tenant=self.tenant).count(), 1)
        self.assertEqual(Member.objects.filter(tenant=other_tenant).count(), 1)

    def test_inactive_member_excluded(self):
        self._create_member(name='Active')
        self._create_member(name='Inactive', is_active=False)
        self.assertEqual(Member.objects.filter(tenant=self.tenant, is_active=True).count(), 1)


class PaymentModelTest(TestCase):
    """Tests for the Payment model."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='Payment Corp')
        self.member = Member.objects.create(
            tenant=self.tenant, name='Pay Member', monthly_due=1000
        )

    def test_create_payment(self):
        payment = Payment.objects.create(
            member=self.member, amount=500, date=date.today(), method='Cash'
        )
        self.assertEqual(str(payment), 'Pay Member - 500 (2026-11-06)')

    def test_payment_ordering(self):
        Payment.objects.create(member=self.member, amount=100, date=date(2026, 1, 1))
        Payment.objects.create(member=self.member, amount=200, date=date(2026, 6, 1))
        payments = list(Payment.objects.filter(member=self.member))
        self.assertEqual(payments[0].amount, 200)  # Most recent first

    def test_payment_methods(self):
        for method in ['Cash', 'Bank Transfer', 'Credit Card', 'Mobile Money', 'Other']:
            payment = Payment.objects.create(member=self.member, amount=100, method=method)
            self.assertEqual(payment.method, method)


class MemberFormTest(TestCase):
    """Tests for the MemberForm."""

    def test_valid_form(self):
        form = MemberForm({
            'name': 'Form Member',
            'email': 'form@example.com',
            'phone': '123456',
            'monthly_due': '500.00',
            'start_date': '2026-01-01',
            'notes': 'Test note',
            'is_active': True,
        })
        self.assertTrue(form.is_valid())

    def test_form_requires_name(self):
        form = MemberForm({
            'name': '',
            'monthly_due': '500.00',
            'start_date': '2026-01-01',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_form_requires_monthly_due(self):
        form = MemberForm({
            'name': 'No Due',
            'monthly_due': '',
            'start_date': '2026-01-01',
            'is_active': True,
        })
        self.assertFalse(form.is_valid())


class PaymentFormTest(TestCase):
    """Tests for the PaymentForm with tenant filtering."""

    def setUp(self):
        self.tenant1 = Tenant.objects.create(name='Form Tenant 1')
        self.tenant2 = Tenant.objects.create(name='Form Tenant 2')
        self.member1 = Member.objects.create(tenant=self.tenant1, name='Member 1', monthly_due=1000)
        self.member2 = Member.objects.create(tenant=self.tenant2, name='Member 2', monthly_due=500)

    def test_form_filters_members_by_tenant(self):
        form = PaymentForm(tenant=self.tenant1)
        member_ids = list(form.fields['member'].queryset.values_list('pk', flat=True))
        self.assertIn(self.member1.pk, member_ids)
        self.assertNotIn(self.member2.pk, member_ids)

    def test_valid_payment_form(self):
        form = PaymentForm({
            'member': self.member1.pk,
            'date': '2026-01-15',
            'amount': '500.00',
            'method': 'Cash',
            'note': 'Partial payment',
        }, tenant=self.tenant1)
        self.assertTrue(form.is_valid())

    def test_payment_form_requires_amount(self):
        form = PaymentForm({
            'member': self.member1.pk,
            'date': '2026-01-15',
            'amount': '',
            'method': 'Cash',
        }, tenant=self.tenant1)
        self.assertFalse(form.is_valid())


class MemberViewsTest(TestCase):
    """Tests for member CRUD views with tenant isolation."""

    def setUp(self):
        self.client = Client()
        self.tenant1 = Tenant.objects.create(name='View Tenant 1')
        self.tenant2 = Tenant.objects.create(name='View Tenant 2')
        self.user1 = User.objects.create_user(username='viewuser1', password='pass')
        self.user1.profile.tenant = self.tenant1
        self.user1.profile.save()
        self.user2 = User.objects.create_user(username='viewuser2', password='pass')
        self.user2.profile.tenant = self.tenant2
        self.user2.profile.save()
        self.member1 = Member.objects.create(tenant=self.tenant1, name='Member A', monthly_due=1000)
        self.member2 = Member.objects.create(tenant=self.tenant2, name='Member B', monthly_due=500)

    def test_member_list_requires_login(self):
        response = self.client.get(reverse('members:list'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("members:list")}')

    def test_member_list_shows_only_tenant_members(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:list'))
        self.assertContains(response, 'Member A')
        self.assertNotContains(response, 'Member B')

    def test_member_list_search(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:list'), {'search': 'Member A'})
        self.assertContains(response, 'Member A')

    def test_member_list_status_filter(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:list'), {'status': 'unpaid'})
        self.assertEqual(response.status_code, 200)

    def test_member_detail_cross_tenant_denied(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:detail', kwargs={'pk': self.member2.pk}))
        self.assertEqual(response.status_code, 404)

    def test_member_detail_same_tenant(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:detail', kwargs={'pk': self.member1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Member A')

    def test_member_create(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.post(reverse('members:create'), {
            'name': 'New Member',
            'monthly_due': '750.00',
            'start_date': '2026-01-01',
            'is_active': True,
        })
        self.assertTrue(Member.objects.filter(name='New Member', tenant=self.tenant1).exists())
        new_member = Member.objects.get(name='New Member')
        self.assertEqual(new_member.tenant, self.tenant1)

    def test_member_update(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.post(reverse('members:update', kwargs={'pk': self.member1.pk}), {
            'name': 'Updated Member A',
            'monthly_due': '1500.00',
            'start_date': self.member1.start_date.strftime('%Y-%m-%d'),
            'is_active': True,
        })
        self.member1.refresh_from_db()
        self.assertEqual(self.member1.name, 'Updated Member A')

    def test_member_update_cross_tenant_denied(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.post(reverse('members:update', kwargs={'pk': self.member2.pk}), {
            'name': 'Hacked',
            'monthly_due': '9999',
            'start_date': '2026-01-01',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 404)

    def test_member_delete_deactivates(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.post(reverse('members:delete', kwargs={'pk': self.member1.pk}))
        self.member1.refresh_from_db()
        self.assertFalse(self.member1.is_active)

    def test_payment_record(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.post(reverse('members:payment_record'), {
            'member': self.member1.pk,
            'date': '2026-01-15',
            'amount': '500.00',
            'method': 'Cash',
            'note': 'Test payment',
        })
        self.assertTrue(Payment.objects.filter(member=self.member1, amount=500).exists())

    def test_payment_record_for_member(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:payment_record_for', kwargs={'pk': self.member1.pk}))
        self.assertEqual(response.status_code, 200)

    def test_payment_record_cross_tenant_denied(self):
        self.client.login(username='viewuser1', password='pass')
        response = self.client.get(reverse('members:payment_record_for', kwargs={'pk': self.member2.pk}))
        self.assertEqual(response.status_code, 404)


class SuperadminTenantSwitchViewsTest(TestCase):
    """Tests that member views respect superadmin tenant switching."""

    def setUp(self):
        self.client = Client()
        self.tenant1 = Tenant.objects.create(name='Switch T1')
        self.tenant2 = Tenant.objects.create(name='Switch T2')
        self.superuser = User.objects.create_user(username='switchsuper', password='pass')
        self.superuser.profile.tenant = self.tenant1
        self.superuser.profile.is_superadmin = True
        self.superuser.profile.save()
        self.member1 = Member.objects.create(tenant=self.tenant1, name='Switch Member 1', monthly_due=1000)
        self.member2 = Member.objects.create(tenant=self.tenant2, name='Switch Member 2', monthly_due=500)

    def test_member_list_default_tenant(self):
        self.client.login(username='switchsuper', password='pass')
        response = self.client.get(reverse('members:list'))
        self.assertContains(response, 'Switch Member 1')
        self.assertNotContains(response, 'Switch Member 2')

    def test_member_list_after_switch(self):
        self.client.login(username='switchsuper', password='pass')
        # Switch tenant via POST
        self.client.post(reverse('accounts:tenant_switch'), {'tenant_id': self.tenant2.pk})
        response = self.client.get(reverse('members:list'))
        self.assertNotContains(response, 'Switch Member 1')
        self.assertContains(response, 'Switch Member 2')
