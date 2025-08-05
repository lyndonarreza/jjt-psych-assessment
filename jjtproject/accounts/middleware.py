from django.shortcuts import redirect
from accounts.models import ExamineeConsent

class ConsentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip middleware for admin or non-examinee users
        if (
            request.path.startswith('/admin/') or
            request.user.is_superuser or
            request.user.is_staff or
            not request.user.is_authenticated or
            getattr(request.user, 'role', None) != 'examinee'
        ):
            return self.get_response(request)

        # Handle examinee consent check
        try:
            consent = ExamineeConsent.objects.get(examinee=request.user)
            if not consent.consented and not request.path.startswith('/accounts/consent'):
                return redirect('examinee_consent')
        except ExamineeConsent.DoesNotExist:
            return redirect('examinee_consent')

        return self.get_response(request)
