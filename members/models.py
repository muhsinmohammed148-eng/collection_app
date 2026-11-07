from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('Bank Transfer', 'Bank Transfer'),
    ('Credit Card', 'Credit Card'),
    ('Mobile Money', 'Mobile Money'),
    ('Other', 'Other'),
]


class Member(models.Model):
    """Represents a member who pays monthly dues, scoped to a tenant."""

    tenant = models.ForeignKey(
        'accounts.Tenant', on_delete=models.CASCADE, related_name='members'
    )
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='member',
        help_text='Login account for this member (optional).'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True)
    monthly_due = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"

    @property
    def total_paid(self):
        """Total amount paid by this member."""
        return self.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or 0

    @property
    def current_balance_owed(self):
        """Calculate the balance owed based on months since start date, including the current month."""
        from datetime import date
        today = date.today()
        months_since_start = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month) + 1
        if months_since_start < 0:
            months_since_start = 0
        expected = months_since_start * self.monthly_due
        paid = self.total_paid
        return max(0, expected - paid)

    @property
    def advance_balance(self):
        """Calculate any advance balance (overpayment)."""
        from datetime import date
        today = date.today()
        months_since_start = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month) + 1
        if months_since_start < 0:
            months_since_start = 0
        expected = months_since_start * self.monthly_due
        paid = self.total_paid
        return max(0, paid - expected)

    @property
    def status(self):
        """Overall payment status of the member."""
        paid = self.total_paid
        from datetime import date
        today = date.today()
        months_since_start = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month) + 1
        if months_since_start < 0:
            months_since_start = 0
        expected = months_since_start * self.monthly_due

        if expected == 0:
            return 'up-to-date'
        if paid >= expected:
            return 'advance' if paid > expected else 'up-to-date'
        if paid > 0:
            return 'behind'
        return 'unpaid'


class Payment(models.Model):
    """Records a payment made by a member."""
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name='payments'
    )
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='Bank Transfer')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.member.name} - {self.amount} ({self.date})"
