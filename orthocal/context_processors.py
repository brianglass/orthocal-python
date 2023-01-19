from django.conf import settings

def globals(request):
    return {
            'PUBLIC_URL': settings.ORTHOCAL_PUBLIC_URL,
    }
