from .models import Tenant


def current_tenant(request):
    """Provide the current active tenant to all templates."""
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.profile
    except Exception:
        return {}

    if profile.is_superadmin:
        tenant_id = request.session.get('current_tenant_id')
        if tenant_id:
            try:
                tenant = Tenant.objects.get(pk=tenant_id, is_active=True)
                return {'current_tenant': tenant}
            except Tenant.DoesNotExist:
                pass
        return {'current_tenant': profile.tenant}

    return {'current_tenant': profile.tenant}
