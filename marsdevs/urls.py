"""
URL конфигурация для проекта Mars Devs.
"""
import os
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt


def health_check(request):
    """Health check endpoint for Render/Railway."""
    return JsonResponse({
        'status': 'ok',
        'service': 'Mars Devs API',
        'version': '1.0.0'
    })


@csrf_exempt
def setup_admin(request):
    """
    Create admin user via API (for initial setup on Render).
    Access: GET /setup-admin/?key=YOUR_SECRET_KEY
    """
    # Get secret key from environment or use default for setup
    setup_key = os.getenv('SETUP_KEY', 'marsdevs-setup-2024')
    provided_key = request.GET.get('key', '')
    
    if provided_key != setup_key:
        return JsonResponse({'error': 'Invalid setup key'}, status=403)
    
    User = get_user_model()
    
    results = []
    
    # Create admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@marsdevs.local',
            password='admin123',
            first_name='Admin',
            last_name='System',
            role='ADMIN'
        )
        results.append('Admin created: admin / admin123')
    else:
        results.append('Admin already exists')
    
    # Create teacher
    if not User.objects.filter(username='teacher').exists():
        teacher = User.objects.create_user(
            username='teacher',
            email='teacher@marsdevs.local',
            password='teacher123',
            first_name='Teacher',
            last_name='User',
            role='TEACHER'
        )
        results.append('Teacher created: teacher / teacher123')
    else:
        results.append('Teacher already exists')
    
    return JsonResponse({
        'status': 'ok',
        'results': results
    })


urlpatterns = [
    # Health check endpoint (for Render/Railway)
    path('', health_check, name='health-check'),
    path('health/', health_check, name='health'),
    
    # Setup endpoint (for initial admin creation)
    path('setup-admin/', setup_admin, name='setup-admin'),
    
    # Admin and API
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

# Раздача media файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
