from django import forms
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from .models import Tenant, Profile


def register(request):
    """User registration view with company/tenant selection."""
    if request.user.is_authenticated:
        return redirect('reports:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created successfully! You are registered under "{user.profile.tenant.name}".')
            return redirect('reports:dashboard')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    """User login view."""
    if request.user.is_authenticated:
        return redirect('reports:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # For superadmins, set the session tenant to their default
            if user.profile.is_superadmin:
                request.session['current_tenant_id'] = user.profile.tenant_id
            messages.success(request, f'Welcome back, {user.username}! ({user.profile.tenant.name})')
            # Redirect member-role users to their personal dashboard
            if user.profile.role == 'member':
                return redirect('members:my_dashboard')
            return redirect('reports:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def user_logout(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# ------------------------------------------------------------------ #
#  Tenant management views (superadmin only)                          #
# ------------------------------------------------------------------ #

def _get_current_tenant(request):
    """
    Return the active tenant for the current request.
    - Superadmins: check X-Current-Tenant-Id header first (set by auth.js from
      localStorage), then fall back to session, then to profile default.
    - Everyone else: use their profile's default tenant.
    """
    profile = request.user.profile
    if profile.is_superadmin:
        # Check HTTP header first (set by frontend auth.js from localStorage)
        tenant_id = request.headers.get('X-Current-Tenant-Id')
        if not tenant_id:
            tenant_id = request.session.get('current_tenant_id')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(pk=tenant_id, is_active=True)
                return tenant
            except Tenant.DoesNotExist:
                pass
        # Fallback to default tenant
        return profile.tenant
    return profile.tenant


@login_required
def tenant_list(request):
    """List all tenants with their user counts and member counts (superadmin)."""
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can manage tenants.')
        return redirect('reports:dashboard')

    tenants = Tenant.objects.all().prefetch_related('users', 'members')
    current_tenant = _get_current_tenant(request)

    context = {
        'tenants': tenants,
        'current_tenant': current_tenant,
    }
    return render(request, 'accounts/tenant_list.html', context)


@login_required
def tenant_detail(request, pk):
    """View a tenant's details including its users and summary (superadmin)."""
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can view tenant details.')
        return redirect('reports:dashboard')

    tenant = get_object_or_404(Tenant, pk=pk)
    users = User.objects.filter(profile__tenant=tenant).select_related('profile')

    # Quick metrics
    from members.models import Member, Payment
    members = Member.objects.filter(tenant=tenant, is_active=True)
    total_members = members.count()
    total_expected = sum(m.monthly_due for m in members)
    total_collected = Payment.objects.filter(member__tenant=tenant).aggregate(
        total=models.Sum('amount')
    )['total'] or 0

    context = {
        'tenant': tenant,
        'users': users,
        'total_members': total_members,
        'total_expected': total_expected,
        'total_collected': total_collected,
        'current_tenant': _get_current_tenant(request),
    }
    return render(request, 'accounts/tenant_detail.html', context)


@login_required
def tenant_switch(request):
    """Switch the current tenant view (superadmin only).

    Supports both traditional form POST (sets session) and AJAX requests
    that carry the tenant ID in the X-Current-Tenant-Id header (set by
    auth.js from localStorage). The session is still updated as a fallback
    for non-JWT requests.
    """
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can switch tenants.')
        return redirect('reports:dashboard')

    # Accept tenant_id from POST (form) or from the header (JWT flow)
    tenant_id = request.POST.get('tenant_id') or request.headers.get('X-Current-Tenant-Id')
    if tenant_id:
        try:
            tenant = Tenant.objects.get(pk=tenant_id, is_active=True)
            # Still write to session as fallback for non-JWT requests
            request.session['current_tenant_id'] = tenant.pk
            messages.success(request, f'Switched to "{tenant.name}".')
        except Tenant.DoesNotExist:
            messages.error(request, 'Selected tenant does not exist or is inactive.')

    next_url = request.GET.get('next', reverse('reports:dashboard'))
    return redirect(next_url)


@login_required
def tenant_user_form(request, tenant_pk, user_pk=None):
    """Add or edit a user's assignment to a tenant (superadmin)."""
    from django.db.models import Q
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can manage tenant users.')
        return redirect('reports:dashboard')

    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    instance = None
    if user_pk:
        instance = get_object_or_404(User, pk=user_pk)

    if request.method == 'POST':
        form = TenantUserForm(request.POST, instance=instance, tenant=tenant)
        if form.is_valid():
            user = form.save()
            if instance:
                messages.success(request, f'Updated {user.username} for "{tenant.name}".')
            else:
                messages.success(request, f'Added {user.username} to "{tenant.name}".')
            return redirect('accounts:tenant_detail', pk=tenant.pk)
    else:
        initial = {'tenant': tenant}
        if instance:
            initial.update({
                'username': instance.username,
                'email': instance.email,
                'role': instance.profile.role,
            })
        form = TenantUserForm(initial=initial, instance=instance, tenant=tenant)

    context = {
        'form': form,
        'tenant': tenant,
        'title': f'Edit {instance.username}' if instance else f'Add User to {tenant.name}',
        'current_tenant': _get_current_tenant(request),
    }
    return render(request, 'accounts/tenant_user_form.html', context)


@login_required
def tenant_user_remove(request, tenant_pk, user_pk):
    """Remove a user from a tenant by reassigning them to the default tenant (superadmin)."""
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can manage tenant users.')
        return redirect('reports:dashboard')

    tenant = get_object_or_404(Tenant, pk=tenant_pk)
    user = get_object_or_404(User, pk=user_pk, profile__tenant=tenant)

    # Reassign to default tenant
    default_tenant, _ = Tenant.objects.get_or_create(name='Default Company')
    user.profile.tenant = default_tenant
    user.profile.save()
    messages.info(request, f'{user.username} removed from "{tenant.name}".')
    return redirect('accounts:tenant_detail', pk=tenant.pk)


# ------------------------------------------------------------------ #
#  Forms                                                              #
# ------------------------------------------------------------------ #

class TenantUserForm(forms.Form):
    """Form for adding/editing a user within a tenant context."""
    username = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control-custom'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control-custom'}))
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control-custom'})
    )
    password1 = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control-custom', 'placeholder': 'Password (leave blank to keep)'}))

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        if not self.instance:
            # Username and password required for new users
            self.fields['username'].required = True
            self.fields['password1'].required = True
            self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control-custom', 'placeholder': 'Password'})

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and not self.instance:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError(f'Username "{username}" already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance:
            username = cleaned_data.get('username')
            if not username:
                self.add_error('username', 'Username is required for new users.')
        return cleaned_data

    def save(self):
        if self.instance:
            # Update existing user
            user = self.instance
            if self.cleaned_data.get('email'):
                user.email = self.cleaned_data['email']
            user.save()
            user.profile.role = self.cleaned_data['role']
            user.profile.tenant = self.tenant
            user.profile.save()
            password = self.cleaned_data.get('password1')
            if password:
                user.set_password(password)
                user.save()
        else:
            # Create new user
            username = self.cleaned_data['username']
            user = User.objects.create_user(
                username=username,
                email=self.cleaned_data.get('email', ''),
                password=self.cleaned_data.get('password1')
            )
            # The signal creates a Profile with default tenant; update it
            user.profile.tenant = self.tenant
            user.profile.role = self.cleaned_data['role']
            user.profile.save()
        return user


# ------------------------------------------------------------------ #
#  Tenant CRUD views (superadmin only)                               #
# ------------------------------------------------------------------ #

class TenantForm(forms.ModelForm):
    """Form for creating a new tenant."""

    class Meta:
        model = Tenant
        fields = ['name', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Company Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control-custom', 'placeholder': 'Company Email'}),
            'phone': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Phone Number'}),
            'address': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3, 'placeholder': 'Address'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Company name is required.')
        return name


@login_required
def tenant_create(request):
    """Create a new tenant (superadmin only)."""
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can create tenants.')
        return redirect('reports:dashboard')

    if request.method == 'POST':
        form = TenantForm(request.POST)
        if form.is_valid():
            tenant = form.save()
            messages.success(request, f'Tenant "{tenant.name}" created successfully!')
            return redirect('accounts:tenant_detail', pk=tenant.pk)
    else:
        form = TenantForm()

    context = {
        'form': form,
        'title': 'Create New Tenant',
        'current_tenant': _get_current_tenant(request),
    }
    return render(request, 'accounts/tenant_form.html', context)


@login_required
def tenant_delete(request, pk):
    """Delete a tenant and all related data (superadmin only).
    
    Cascades deletion to:
    - All members (and their payments via CASCADE)
    - All users assigned to this tenant (deleted from User table)
    - The tenant itself
    """
    profile = request.user.profile
    if not profile.is_superadmin:
        messages.error(request, 'Only superadmins can delete tenants.')
        return redirect('reports:dashboard')

    tenant = get_object_or_404(Tenant, pk=pk)

    # Prevent deleting the user's own default tenant
    if tenant.pk == profile.tenant.pk:
        messages.error(request, f'Cannot delete your own default tenant "{tenant.name}".')
        return redirect('accounts:tenant_list')

    # Prevent deleting the currently active tenant (session-based)
    current_tenant = _get_current_tenant(request)
    if tenant.pk == current_tenant.pk:
        messages.error(request, f'Cannot delete the currently active tenant "{tenant.name}". Switch to another tenant first.')
        return redirect('accounts:tenant_list')

    # Count related objects for the confirmation page
    user_count = User.objects.filter(profile__tenant=tenant).count()
    from members.models import Member
    member_count = Member.objects.filter(tenant=tenant).count()

    if request.method == 'POST':
        # Confirm deletion — cascade delete everything related to this tenant
        tenant_name = tenant.name

        # 1. Delete all users belonging to this tenant
        tenant_users = User.objects.filter(profile__tenant=tenant)
        for user in tenant_users:
            # Clear session tenant if it points to this tenant
            if request.session.get('current_tenant_id') == tenant.pk:
                del request.session['current_tenant_id']
            user.delete()

        # 2. Delete all members (payments are CASCADE deleted automatically)
        Member.objects.filter(tenant=tenant).delete()

        # 3. Delete the tenant itself
        tenant.delete()

        messages.success(request, f'Tenant "{tenant_name}" and all related data ({user_count} user(s), {member_count} member(s)) deleted successfully!')
        return redirect('accounts:tenant_list')

    # GET request — show confirmation page
    context = {
        'tenant': tenant,
        'user_count': user_count,
        'member_count': member_count,
        'current_tenant': _get_current_tenant(request),
    }
    return render(request, 'accounts/tenant_confirm_delete.html', context)


class MemberCredentialsForm(forms.Form):
    """Form for admins to create login credentials for a member."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Username (e.g., john.doe)'
        }),
        help_text='Username the member will use to log in.'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Password'
        }),
        help_text='At least 8 characters.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Confirm Password'
        }),
    )

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        if len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned_data


class RegistrationForm(UserCreationForm):
    """Extended registration form that includes company/tenant selection or creation."""

    company_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Company / Organization Name'
        }),
        help_text='Enter your company name. If it already exists, you will join it.'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget = forms.TextInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Username'
        })
        self.fields['email'].widget = forms.EmailInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Email Address'
        })
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Confirm Password'
        })

    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name', '').strip()
        if not company_name:
            raise forms.ValidationError('Company name is required.')
        return company_name

    def save(self, commit=True):
        user = super().save(commit=False)
        company_name = self.cleaned_data.get('company_name', '').strip()

        # Get or create the tenant (company)
        tenant, created = Tenant.objects.get_or_create(
            name=company_name,
            defaults={'is_active': True}
        )

        if commit:
            user.save()
            # The signal creates a Profile with default tenant; update it
            user.profile.tenant = tenant
            user.profile.role = 'admin'
            user.profile.save()

        return user


@login_required
def member_credentials(request, member_pk):
    """Create or update login credentials for a member (admin only)."""
    from members.models import Member

    tenant = _get_current_tenant(request)
    member = get_object_or_404(Member, pk=member_pk, tenant=tenant)

    # Check if member already has a user account
    existing_user = member.user

    if request.method == 'POST':
        form = MemberCredentialsForm(request.POST)
        if form.is_valid():
            if existing_user:
                # Update existing user's password
                existing_user.set_password(form.cleaned_data['password1'])
                existing_user.save()
                messages.success(request, f'Password updated for {member.name}!')
            else:
                # Create new user account
                username = form.cleaned_data['username']
                password = form.cleaned_data['password1']
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=member.email or ''
                )
                # Link user to member
                member.user = user
                member.save()
                # Set profile role to member
                user.profile.role = 'member'
                user.profile.tenant = tenant
                user.profile.save()
                messages.success(request, f'Login credentials created for {member.name}! Username: {username}')
            return redirect('members:detail', pk=member.pk)
    else:
        form = MemberCredentialsForm(initial={
            'username': existing_user.username if existing_user else (member.name.lower().replace(' ', '.')[:30] or 'member'),
        })

    context = {
        'form': form,
        'member': member,
        'existing_user': existing_user,
        'tenant': tenant,
    }
    return render(request, 'accounts/member_credentials.html', context)


