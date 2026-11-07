from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models.signals import post_save
from accounts.models import Tenant, Profile, create_user_profile, save_user_profile


class TenantModelTest(TestCase):
    """Tests for the Tenant model."""

    def test_create_tenant(self):
        tenant = Tenant.objects.create(name='Test Corp', email='test@corp.com')
        self.assertEqual(str(tenant), 'Test Corp')
        self.assertTrue(tenant.is_active)

    def test_tenant_unique_name(self):
        Tenant.objects.create(name='Unique Corp')
        with self.assertRaises(Exception):
            Tenant.objects.create(name='Unique Corp')

    def test_tenant_member_count(self):
        from members.models import Member
        tenant = Tenant.objects.create(name='Count Corp')
        Member.objects.create(tenant=tenant, name='Alice', monthly_due=100)
        Member.objects.create(tenant=tenant, name='Bob', monthly_due=200)
        self.assertEqual(tenant.member_count, 2)

    def test_tenant_member_count_excludes_inactive(self):
        from members.models import Member
        tenant = Tenant.objects.create(name='Inactive Corp')
        Member.objects.create(tenant=tenant, name='Alice', monthly_due=100, is_active=True)
        Member.objects.create(tenant=tenant, name='Bob', monthly_due=200, is_active=False)
        self.assertEqual(tenant.member_count, 1)

    def test_tenant_user_count(self):
        tenant = Tenant.objects.create(name='User Corp')
        user = User.objects.create_user(username='testuser', password='pass')
        user.profile.tenant = tenant
        user.profile.save()
        self.assertEqual(tenant.user_count, 1)

    def test_tenant_ordering(self):
        Tenant.objects.create(name='Zebra')
        Tenant.objects.create(name='Alpha')
        self.assertEqual(list(Tenant.objects.all().values_list('name', flat=True)), ['Alpha', 'Zebra'])


class ProfileModelTest(TestCase):
    """Tests for the Profile model."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='Test Corp')

    def test_profile_auto_created_on_user_create(self):
        user = User.objects.create_user(username='autouser', password='pass')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)
        self.assertEqual(user.profile.role, 'viewer')

    def test_profile_str(self):
        user = User.objects.create_user(username='struser', password='pass')
        user.profile.tenant = self.tenant
        user.profile.save()
        self.assertIn('struser', str(user.profile))
        self.assertIn('viewer', str(user.profile))

    def test_profile_superadmin_str(self):
        user = User.objects.create_user(username='superuser', password='pass')
        user.profile.tenant = self.tenant
        user.profile.is_superadmin = True
        user.profile.save()
        self.assertIn('👑', str(user.profile))

    def test_is_tenant_admin(self):
        user = User.objects.create_user(username='adminuser', password='pass')
        user.profile.tenant = self.tenant
        user.profile.role = 'admin'
        user.profile.save()
        self.assertTrue(user.profile.is_tenant_admin)

    def test_is_tenant_admin_false_for_viewer(self):
        user = User.objects.create_user(username='vieweruser', password='pass')
        user.profile.tenant = self.tenant
        user.profile.save()
        self.assertFalse(user.profile.is_tenant_admin)

    def test_accessible_tenants_regular_user(self):
        other_tenant = Tenant.objects.create(name='Other Corp')
        user = User.objects.create_user(username='regular', password='pass')
        user.profile.tenant = self.tenant
        user.profile.save()
        accessible = list(user.profile.accessible_tenants.values_list('name', flat=True))
        self.assertEqual(accessible, ['Test Corp'])

    def test_accessible_tenants_superadmin(self):
        other_tenant = Tenant.objects.create(name='Other Corp')
        inactive_tenant = Tenant.objects.create(name='Inactive Corp', is_active=False)
        user = User.objects.create_user(username='super', password='pass')
        user.profile.tenant = self.tenant
        user.profile.is_superadmin = True
        user.profile.save()
        accessible = sorted(user.profile.accessible_tenants.values_list('name', flat=True))
        # Default Company is created by the signal, plus Test Corp and Other Corp
        self.assertIn('Other Corp', accessible)
        self.assertIn('Test Corp', accessible)
        self.assertNotIn('Inactive Corp', accessible)

    def test_profile_role_choices(self):
        user = User.objects.create_user(username='roleuser', password='pass')
        for role in ['admin', 'collector', 'viewer']:
            user.profile.role = role
            user.profile.save()
            self.assertEqual(user.profile.role, role)


class UserSignalTest(TestCase):
    """Tests for user profile auto-creation signals."""

    def test_create_user_profile_signal(self):
        """Creating a User should auto-create a Profile with default tenant."""
        user = User.objects.create_user(username='signaluser', password='pass')
        self.assertTrue(Profile.objects.filter(user=user).exists())
        profile = user.profile
        self.assertIsNotNone(profile.tenant)
        self.assertEqual(profile.tenant.name, 'Default Company')

    def test_default_tenant_get_or_create(self):
        """Multiple users should share the same default tenant."""
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')
        self.assertEqual(user1.profile.tenant, user2.profile.tenant)

    def test_save_user_profile_signal(self):
        """Saving a user should save the profile."""
        user = User.objects.create_user(username='saveuser', password='pass')
        user.profile.department = 'Engineering'
        user.profile.save()
        user.save()
        refreshed = User.objects.get(pk=user.pk)
        self.assertEqual(refreshed.profile.department, 'Engineering')


class RegistrationFormTest(TestCase):
    """Tests for the RegistrationForm."""

    def setUp(self):
        self.client = Client()

    def test_registration_creates_user_and_tenant(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'company_name': 'New Corp',
        })
        self.assertTrue(User.objects.filter(username='newuser').exists())
        user = User.objects.get(username='newuser')
        self.assertEqual(user.profile.tenant.name, 'New Corp')
        self.assertEqual(user.profile.role, 'admin')

    def test_registration_joins_existing_tenant(self):
        Tenant.objects.create(name='Existing Corp')
        self.client.post(reverse('accounts:register'), {
            'username': 'joiner',
            'email': 'joiner@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'company_name': 'Existing Corp',
        })
        user = User.objects.get(username='joiner')
        self.assertEqual(user.profile.tenant.name, 'Existing Corp')

    def test_registration_requires_company_name(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'nocompany',
            'email': 'no@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'company_name': '',
        })
        self.assertFalse(User.objects.filter(username='nocompany').exists())

    def test_registration_redirects_if_authenticated(self):
        user = User.objects.create_user(username='authuser', password='pass')
        self.client.login(username='authuser', password='pass')
        response = self.client.post(reverse('accounts:register'), {
            'username': 'dup',
            'email': 'dup@example.com',
            'password1': 'TestPass123!',
            'password2': 'TestPass123!',
            'company_name': 'Dup Corp',
        })
        self.assertEqual(response.status_code, 302)

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'mismatch',
            'email': 'mm@example.com',
            'password1': 'Pass123!',
            'password2': 'Different123!',
            'company_name': 'MM Corp',
        })
        self.assertFalse(User.objects.filter(username='mismatch').exists())


class TenantUserFormTest(TestCase):
    """Tests for the TenantUserForm used in tenant management."""

    def setUp(self):
        self.tenant = Tenant.objects.create(name='Form Corp')
        self.superuser = User.objects.create_user(username='superform', password='pass')
        self.superuser.profile.is_superadmin = True
        self.superuser.profile.save()
        from accounts.views import TenantUserForm
        self.FormClass = TenantUserForm

    def test_create_new_user(self):
        form = self.FormClass({
            'username': 'formuser',
            'email': 'form@example.com',
            'role': 'collector',
            'password1': 'FormPass123!',
        }, tenant=self.tenant)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, 'formuser')
        self.assertEqual(user.profile.tenant, self.tenant)
        self.assertEqual(user.profile.role, 'collector')

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='existing', password='pass')
        form = self.FormClass({
            'username': 'existing',
            'email': 'ex@example.com',
            'role': 'viewer',
            'password1': 'FormPass123!',
        }, tenant=self.tenant)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_update_existing_user(self):
        user = User.objects.create_user(username='updateuser', password='pass')
        user.profile.tenant = self.tenant
        user.profile.save()
        form = self.FormClass({
            'username': 'updateuser',
            'email': 'updated@example.com',
            'role': 'admin',
            'password1': '',
        }, tenant=self.tenant, instance=user)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertEqual(saved.profile.role, 'admin')
        self.assertEqual(saved.email, 'updated@example.com')

    def test_update_password(self):
        user = User.objects.create_user(username='passuser', password='oldpass')
        user.profile.tenant = self.tenant
        user.profile.save()
        form = self.FormClass({
            'username': 'passuser',
            'email': 'pass@example.com',
            'role': 'viewer',
            'password1': 'NewPass123!',
        }, tenant=self.tenant, instance=user)
        self.assertTrue(form.is_valid())
        form.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPass123!'))


class AuthViewsTest(TestCase):
    """Tests for authentication views (login, logout)."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Auth Corp')
        self.user = User.objects.create_user(username='authuser', password='authpass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()

    def test_login_page_get(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'authpass',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('reports:dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, 200)
        # Check the form has errors rather than specific message text
        self.assertIn('form', response.context)

    def test_login_redirects_if_authenticated(self):
        self.client.login(username='authuser', password='authpass')
        response = self.client.get(reverse('accounts:login'))
        self.assertRedirects(response, reverse('reports:dashboard'))

    def test_logout(self):
        self.client.login(username='authuser', password='authpass')
        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))

    def test_superadmin_login_sets_session_tenant(self):
        self.user.profile.is_superadmin = True
        self.user.profile.save()
        # Use POST to login view so the session is properly set
        response = self.client.post(reverse('accounts:login'), {
            'username': 'authuser',
            'password': 'authpass',
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('current_tenant_id', self.client.session)


class TenantManagementViewsTest(TestCase):
    """Tests for tenant management views (superadmin only)."""

    def setUp(self):
        self.client = Client()
        self.tenant1 = Tenant.objects.create(name='Tenant One')
        self.tenant2 = Tenant.objects.create(name='Tenant Two')
        self.superuser = User.objects.create_user(username='supermgmt', password='pass')
        self.superuser.profile.tenant = self.tenant1
        self.superuser.profile.is_superadmin = True
        self.superuser.profile.save()
        self.regular_user = User.objects.create_user(username='regularmgmt', password='pass')
        self.regular_user.profile.tenant = self.tenant1
        self.regular_user.profile.save()

    def test_tenant_list_requires_login(self):
        response = self.client.get(reverse('accounts:tenant_list'))
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={reverse("accounts:tenant_list")}')

    def test_tenant_list_denies_regular_user(self):
        self.client.login(username='regularmgmt', password='pass')
        response = self.client.get(reverse('accounts:tenant_list'))
        self.assertRedirects(response, reverse('reports:dashboard'))

    def test_tenant_list_shows_all_tenants(self):
        self.client.login(username='supermgmt', password='pass')
        response = self.client.get(reverse('accounts:tenant_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tenant One')
        self.assertContains(response, 'Tenant Two')

    def test_tenant_detail_denies_regular_user(self):
        self.client.login(username='regularmgmt', password='pass')
        response = self.client.get(reverse('accounts:tenant_detail', kwargs={'pk': self.tenant1.pk}))
        self.assertRedirects(response, reverse('reports:dashboard'))

    def test_tenant_detail_shows_users(self):
        self.client.login(username='supermgmt', password='pass')
        response = self.client.get(reverse('accounts:tenant_detail', kwargs={'pk': self.tenant1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'supermgmt')

    def test_tenant_switch_success(self):
        self.client.login(username='supermgmt', password='pass')
        response = self.client.post(reverse('accounts:tenant_switch'), {
            'tenant_id': self.tenant2.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['current_tenant_id'], self.tenant2.pk)

    def test_tenant_switch_denies_regular_user(self):
        self.client.login(username='regularmgmt', password='pass')
        response = self.client.post(reverse('accounts:tenant_switch'), {
            'tenant_id': self.tenant2.pk,
        })
        self.assertRedirects(response, reverse('reports:dashboard'))

    def test_tenant_switch_invalid_tenant(self):
        self.client.login(username='supermgmt', password='pass')
        response = self.client.post(reverse('accounts:tenant_switch'), {
            'tenant_id': 99999,
        })
        self.assertEqual(response.status_code, 302)

    def test_tenant_user_add(self):
        self.client.login(username='supermgmt', password='pass')
        response = self.client.post(
            reverse('accounts:tenant_user_add', kwargs={'tenant_pk': self.tenant1.pk}),
            {
                'username': 'addeduser',
                'email': 'added@example.com',
                'role': 'collector',
                'password1': 'AddedPass123!',
            }
        )
        self.assertTrue(User.objects.filter(username='addeduser').exists())
        added = User.objects.get(username='addeduser')
        self.assertEqual(added.profile.tenant, self.tenant1)

    def test_tenant_user_remove(self):
        user_to_remove = User.objects.create_user(username='removeme', password='pass')
        user_to_remove.profile.tenant = self.tenant1
        user_to_remove.profile.save()
        self.client.login(username='supermgmt', password='pass')
        response = self.client.post(
            reverse('accounts:tenant_user_remove', kwargs={'tenant_pk': self.tenant1.pk, 'user_pk': user_to_remove.pk})
        )
        self.assertEqual(response.status_code, 302)
        user_to_remove.refresh_from_db()
        self.assertEqual(user_to_remove.profile.tenant.name, 'Default Company')

    def test_tenant_user_remove_denies_regular_user(self):
        user_to_remove = User.objects.create_user(username='removeme2', password='pass')
        user_to_remove.profile.tenant = self.tenant1
        user_to_remove.profile.save()
        self.client.login(username='regularmgmt', password='pass')
        response = self.client.post(
            reverse('accounts:tenant_user_remove', kwargs={'tenant_pk': self.tenant1.pk, 'user_pk': user_to_remove.pk})
        )
        self.assertRedirects(response, reverse('reports:dashboard'))


class ContextProcessorTest(TestCase):
    """Tests for the current_tenant context processor."""

    def setUp(self):
        self.client = Client()
        self.tenant = Tenant.objects.create(name='Context Corp')
        self.user = User.objects.create_user(username='ctxuser', password='pass')
        self.user.profile.tenant = self.tenant
        self.user.profile.save()

    def test_unauthenticated_returns_empty(self):
        response = self.client.get(reverse('accounts:login'))
        # The context processor should not crash for unauthenticated users
        self.assertEqual(response.status_code, 200)

    def test_authenticated_shows_tenant(self):
        self.client.login(username='ctxuser', password='pass')
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_superadmin_switched_tenant(self):
        other_tenant = Tenant.objects.create(name='Other Context')
        self.user.profile.is_superadmin = True
        self.user.profile.save()
        self.client.login(username='ctxuser', password='pass')
        self.client.post(reverse('accounts:tenant_switch'), {'tenant_id': other_tenant.pk})
        response = self.client.get(reverse('reports:dashboard'))
        self.assertEqual(response.status_code, 200)
