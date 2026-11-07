from django.http import JsonResponse
from django.urls import path
from .urls import urlpatterns as application_urls


def test_identity(request):
    return JsonResponse({'environment': 'revival-local-sqlite-only'})

urlpatterns = [path('__revival_test__/identity/', test_identity)] + application_urls
