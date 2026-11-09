from .models import Tenant


def current_tenant(request):
    """Provide the current active tenant to all templates.

    Priority for superadmin tenant selection:
    1. X-Current-Tenant-Id header (set by auth.js from localStorage) —
       this is the primary source on Vercel where sessions are unreliable.
    2. Session-stored tenant_id (fallback for non-JWT requests).
    3. Profile's default tenant.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        profile = request.user.profile
    except Exception:
        return {}

    if profile.is_superadmin:
        # Check HTTP header first (set by frontend auth.js from localStorage)
        # This is the primary source on Vercel where sessions are lost between cold starts
        tenant_id = request.headers.get('X-Current-Tenant-Id')
        if not tenant_id:
            tenant_id = request.session.get('current_tenant_id')

        if tenant_id:
            try:
                tenant = Tenant.objects.get(pk=tenant_id, is_active=True)
                return {'current_tenant': tenant}
            except Tenant.DoesNotExist:
                pass
        return {'current_tenant': profile.tenant}

    return {'current_tenant': profile.tenant}
