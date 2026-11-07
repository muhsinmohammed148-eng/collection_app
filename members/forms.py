from django import forms
from .models import Member, Payment


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['name', 'email', 'phone', 'monthly_due', 'start_date', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control-custom', 'placeholder': 'Email Address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control-custom', 'placeholder': 'Phone Number'}),
            'monthly_due': forms.NumberInput(attrs={'class': 'form-control-custom', 'placeholder': 'Monthly Due Amount'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 3, 'placeholder': 'Additional Notes'}),
            'is_active': forms.CheckboxInput(),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['member', 'date', 'amount', 'method', 'note']
        widgets = {
            'member': forms.Select(attrs={'class': 'form-control-custom'}),
            'date': forms.DateInput(attrs={'class': 'form-control-custom', 'type': 'date'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control-custom', 'placeholder': 'Amount', 'step': '0.01'}),
            'method': forms.Select(attrs={'class': 'form-control-custom'}),
            'note': forms.Textarea(attrs={'class': 'form-control-custom', 'rows': 2, 'placeholder': 'Payment Note'}),
        }

    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        if tenant:
            # Only show members belonging to the same tenant
            self.fields['member'].queryset = Member.objects.filter(tenant=tenant, is_active=True)
