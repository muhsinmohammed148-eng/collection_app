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
        # Priority for tenant ID:
        # 1. X-Current-Tenant-Id header (fetch/XHR calls with auth.js)
        # 2. payflow_tenant cookie (regular page navigations)
        # 3. Session (fallback for non-JWT requests)
        # 4. Profile default tenant
        tenant_id = request.headers.get('X-Current-Tenant-Id')
        if not tenant_id:
            tenant_id = request.COOKIES.get('payflow_tenant')
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
