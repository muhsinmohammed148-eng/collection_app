from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Tenant(models.Model):
    """Represents a company/organization (multi-tenant isolation)."""

    name = models.CharField(max_length=200, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tenant (Company)'
        verbose_name_plural = 'Tenants (Companies)'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        from members.models import Member
        return Member.objects.filter(tenant=self, is_active=True).count()

    @property
    def user_count(self):
        return self.users.filter(user__is_active=True).count()


class Profile(models.Model):
    """Extended user profile with role, tenant assignment, and additional info."""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('collector', 'Collector'),
        ('viewer', 'Viewer'),
        ('member', 'Member'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='users',
        help_text='The default company/tenant this user belongs to.'
    )
    is_superadmin = models.BooleanField(
        default=False,
        help_text='Superadmins can view and switch between all tenants.'
    )
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)

    def __str__(self):
        prefix = '👑 ' if self.is_superadmin else ''
        return f"{prefix}{self.user.username} ({self.role}) — {self.tenant.name}"

    @property
    def is_tenant_admin(self):
        """Check if user is an admin for their tenant."""
        return self.role == 'admin'

    @property
    def accessible_tenants(self):
        """Return all tenants this user can access."""
        if self.is_superadmin:
            return Tenant.objects.filter(is_active=True)
        return Tenant.objects.filter(pk=self.tenant_id, is_active=True)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Create a default tenant if none exists yet
        default_tenant, _ = Tenant.objects.get_or_create(
            name='Default Company',
            defaults={'name': 'Default Company'}
        )
        # Determine role and superadmin status from Django's is_superuser flag
        is_superadmin = instance.is_superuser
        role = 'admin' if instance.is_superuser else 'viewer'
        # Use get_or_create to avoid IntegrityError if profile already exists
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                'tenant': default_tenant,
                'role': role,
                'is_superadmin': is_superadmin,
            }
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        pass
