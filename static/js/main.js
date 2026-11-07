// PayFlow - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const menuToggle = document.getElementById('menuToggle');
    const mobileNav = document.getElementById('mobileNav');
    const menuIcon = document.getElementById('menuIcon');

    if (menuToggle && mobileNav) {
        menuToggle.addEventListener('click', function() {
            mobileNav.classList.toggle('show');
            if (menuIcon) {
                if (mobileNav.classList.contains('show')) {
                    menuIcon.className = 'bi bi-x-lg';
                } else {
                    menuIcon.className = 'bi bi-list';
                }
            }
        });

        // Close mobile nav when clicking outside
        document.addEventListener('click', function(e) {
            if (window.innerWidth < 992) {
                if (!mobileNav.contains(e.target) && !menuToggle.contains(e.target)) {
                    mobileNav.classList.remove('show');
                    if (menuIcon) {
                        menuIcon.className = 'bi bi-list';
                    }
                }
            }
        });

        // Close mobile nav on resize to desktop
        window.addEventListener('resize', function() {
            if (window.innerWidth >= 992) {
                mobileNav.classList.remove('show');
                if (menuIcon) {
                    menuIcon.className = 'bi bi-list';
                }
            }
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-custom');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            if (alert.parentElement) {
                alert.style.transition = 'opacity 0.3s';
                alert.style.opacity = '0';
                setTimeout(function() {
                    if (alert.parentElement) {
                        alert.remove();
                    }
                }, 300);
            }
        }, 5000);
    });
});
