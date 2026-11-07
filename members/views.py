from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum
from .models import Member, Payment
from .forms import MemberForm, PaymentForm


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
def member_list(request):
    """List all members with search and filter — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', 'all')

    members = Member.objects.filter(tenant=tenant, is_active=True)

    if search_query:
        members = members.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    if status_filter != 'all':
        filtered = []
        for m in members:
            if m.status == status_filter:
                filtered.append(m)
        members = Member.objects.filter(pk__in=[m.pk for m in filtered])

    context = {
        'members': members,
        'search_query': search_query,
        'status_filter': status_filter,
        'tenant': tenant,
    }
    return render(request, 'members/member_list.html', context)


@login_required
def member_detail(request, pk):
    """View member details and payment history — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    member = get_object_or_404(Member, pk=pk, tenant=tenant)
    payments = member.payments.all()

    from reports.models import ReportService
    ledger = ReportService.get_member_ledger(member)

    context = {
        'member': member,
        'payments': payments,
        'ledger': ledger,
        'tenant': tenant,
    }
    return render(request, 'members/member_detail.html', context)


@login_required
def member_create(request):
    """Create a new member — auto-assigned to user's tenant."""
    tenant = _get_current_tenant(request)
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.tenant = tenant
            member.save()
            messages.success(request, 'Member added successfully!')
            return redirect('members:list')
    else:
        form = MemberForm()

    return render(request, 'members/member_form.html', {'form': form, 'title': 'Add Member', 'tenant': tenant})


@login_required
def member_update(request, pk):
    """Update an existing member — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    member = get_object_or_404(Member, pk=pk, tenant=tenant)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, 'Member updated successfully!')
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)

    return render(request, 'members/member_form.html', {'form': form, 'title': 'Edit Member', 'member': member, 'tenant': tenant})


@login_required
def member_delete(request, pk):
    """Delete (deactivate) a member — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    member = get_object_or_404(Member, pk=pk, tenant=tenant)
    member.is_active = False
    member.save()
    messages.info(request, f'Member {member.name} has been deactivated.')
    return redirect('members:list')


@login_required
def payment_record(request, pk=None):
    """Record a payment for a member — scoped to user's tenant."""
    tenant = _get_current_tenant(request)
    member = None
    if pk:
        member = get_object_or_404(Member, pk=pk, tenant=tenant)

    if request.method == 'POST':
        form = PaymentForm(request.POST, tenant=tenant)
        if form.is_valid():
            payment = form.save()
            messages.success(request, f'Payment of {payment.amount} recorded for {payment.member.name}!')
            return redirect('members:detail', pk=payment.member.pk)
    else:
        initial = {'member': member} if member else {}
        form = PaymentForm(initial=initial, tenant=tenant)

    context = {
        'form': form,
        'member': member,
        'title': f'Record Payment for {member.name}' if member else 'Record Payment',
        'tenant': tenant,
    }
    return render(request, 'members/payment_form.html', context)


@login_required
def my_dashboard(request):
    """Personal dashboard for member-role users — shows only their own data."""
    profile = request.user.profile
    if profile.role != 'member':
        messages.error(request, 'Access denied. This page is for members only.')
        return redirect('reports:dashboard')

    # Get the member record linked to this user
    try:
        member = Member.objects.get(user=request.user)
    except Member.DoesNotExist:
        messages.error(request, 'No member record found for your account. Please contact your administrator.')
        return redirect('reports:dashboard')

    payments = member.payments.all()

    from reports.models import ReportService
    ledger = ReportService.get_member_ledger(member)

    # Calculate current month info
    from datetime import date
    today = date.today()
    current_month_payments = payments.filter(date__year=today.year, date__month=today.month)
    current_month_paid = sum(p.amount for p in current_month_payments)
    current_month_status = 'paid' if current_month_paid >= member.monthly_due else ('partial' if current_month_paid > 0 else 'unpaid')

    context = {
        'member': member,
        'payments': payments[:20],  # Last 20 payments
        'ledger': ledger,
        'current_month_paid': current_month_paid,
        'current_month_status': current_month_status,
        'today': today,
    }
    return render(request, 'members/my_dashboard.html', context)
