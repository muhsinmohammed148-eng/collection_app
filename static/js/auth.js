// PayFlow - JWT Authentication Helper
//
// Manages JWT tokens in localStorage so the user stays authenticated
// across Vercel serverless function cold starts (where server-side
// sessions are lost). Every page load restores the tokens and attaches
// them to fetch() calls automatically.

(function () {
    'use strict';

    // ── Storage keys ────────────────────────────────────────────────
    var ACCESS_TOKEN_KEY = 'payflow_access_token';
    var REFRESH_TOKEN_KEY = 'payflow_refresh_token';
    var CURRENT_TENANT_KEY = 'payflow_current_tenant_id';

    // ── Token helpers ───────────────────────────────────────────────

    function getAccessToken() {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    }

    function setTokens(access, refresh) {
        localStorage.setItem(ACCESS_TOKEN_KEY, access);
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    }

    function clearTokens() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
    }

    // ── Tenant helpers ──────────────────────────────────────────────

    function getCurrentTenantId() {
        return localStorage.getItem(CURRENT_TENANT_KEY);
    }

    function setCurrentTenantId(tenantId) {
        if (tenantId) {
            localStorage.setItem(CURRENT_TENANT_KEY, String(tenantId));
        } else {
            localStorage.removeItem(CURRENT_TENANT_KEY);
        }
    }

    // ── CSRF token helper ───────────────────────────────────────────

    function getCsrfToken() {
        // Try to read the CSRF token from the cookie (set by Django)
        var name = 'csrftoken';
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        // Fallback: read from meta tag if present
        if (!cookieValue) {
            var meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) {
                cookieValue = meta.getAttribute('content');
            }
        }
        return cookieValue;
    }

    // ── JWT decode (no library needed) ──────────────────────────────

    function decodeJwt(token) {
        try {
            var parts = token.split('.');
            if (parts.length !== 3) return null;
            var payload = parts[1];
            // Base64url decode
            payload = payload.replace(/-/g, '+').replace(/_/g, '/');
            while (payload.length % 4) {
                payload += '=';
            }
            var json = decodeURIComponent(
                atob(payload).split('').map(function (c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join('')
            );
            return JSON.parse(json);
        } catch (e) {
            return null;
        }
    }

    // ── Token expiry check ──────────────────────────────────────────

    function isTokenExpired(token) {
        var payload = decodeJwt(token);
        if (!payload || !payload.exp) return true;
        return Date.now() >= (payload.exp * 1000) - 30000; // 30s buffer
    }

    // ── Refresh token via API ───────────────────────────────────────

    function refreshAccessToken() {
        var refreshToken = getRefreshToken();
        if (!refreshToken) return null;

        return fetch('/api/auth/token/refresh/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken })
        }).then(function (res) {
            if (res.ok) return res.json();
            throw new Error('Token refresh failed');
        });
    }

    // ── Authenticated fetch wrapper ─────────────────────────────────
    //
    // This replaces the global fetch() so all fetch calls automatically
    // include the Authorization header and the current tenant ID header.
    // If the access token is expired, it auto-refreshes before retrying.

    var originalFetch = window.fetch;

    window.fetch = function (url, options) {
        options = options || {};
        var headers = options.headers || {};

        // Skip auth headers for auth endpoints themselves
        var isAuthEndpoint = typeof url === 'string' && (
            url.indexOf('/api/auth/') === 0 ||
            url.indexOf('/accounts/') === 0
        );

        if (!isAuthEndpoint) {
            var accessToken = getAccessToken();
            if (accessToken) {
                // Set Authorization header
                if (typeof headers === 'object') {
                    headers['Authorization'] = 'Bearer ' + accessToken;
                } else {
                    headers = { 'Authorization': 'Bearer ' + accessToken };
                }

                // Set current tenant header for superadmin context
                var tenantId = getCurrentTenantId();
                if (tenantId) {
                    if (typeof headers === 'object') {
                        headers['X-Current-Tenant-Id'] = tenantId;
                    }
                }
            }
        }

        // Add CSRF token for non-GET requests to auth endpoints
        if (isAuthEndpoint && options.method && options.method.toUpperCase() !== 'GET') {
            var csrfToken = getCsrfToken();
            if (csrfToken && typeof headers === 'object') {
                headers['X-CSRFToken'] = csrfToken;
            }
        }

        options.headers = headers;

        // If we have an expired token, try to refresh first
        if (!isAuthEndpoint) {
            var token = getAccessToken();
            if (token && isTokenExpired(token)) {
                return refreshAccessToken().then(function (data) {
                    if (data && data.access) {
                        setTokens(data.access, getRefreshToken());
                        // Update the Authorization header with new token
                        if (typeof options.headers === 'object') {
                            options.headers['Authorization'] = 'Bearer ' + data.access;
                        }
                    }
                    return originalFetch(url, options);
                }).catch(function () {
                    // Refresh failed — redirect to login
                    window.location.href = '/accounts/login/';
                    throw new Error('Session expired');
                });
            }
        }

        return originalFetch(url, options);
    };

    // ── Expose public API ───────────────────────────────────────────

    window.PayFlowAuth = {
        getAccessToken: getAccessToken,
        getRefreshToken: getRefreshToken,
        setTokens: setTokens,
        clearTokens: clearTokens,
        getCurrentTenantId: getCurrentTenantId,
        setCurrentTenantId: setCurrentTenantId,
        isTokenExpired: isTokenExpired,
        decodeJwt: decodeJwt,

        // Check if user has a valid token
        isAuthenticated: function () {
            var token = getAccessToken();
            return token && !isTokenExpired(token);
        },

        // Logout via API (blacklists refresh token) then clears local storage
        logout: function () {
            var refreshToken = getRefreshToken();
            if (refreshToken) {
                fetch('/api/auth/logout/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({ refresh: refreshToken })
                }).catch(function () {
                    // Ignore errors — still clear tokens
                });
            }
            clearTokens();
        }
    };

    // ── On page load: ensure tenant header is set ───────────────────
    // If the server rendered the page with a tenant in the context,
    // sync it to localStorage so subsequent fetch calls carry it.

    document.addEventListener('DOMContentLoaded', function () {
        var tenantMeta = document.querySelector('meta[name="current-tenant-id"]');
        if (tenantMeta) {
            setCurrentTenantId(tenantMeta.getAttribute('content'));
        }
    });

})();
