from django.contrib import admin
from django.urls import path, include
from django.conf import settings
# Impor fungsi static
from django.conf.urls.static import static 
from core.admin import custom_admin_site

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('', include('core.urls')),
]

# --- Konfigurasi File Media (Hanya digunakan saat DEBUG=True) ---
# Menambahkan konfigurasi untuk melayani file media saat mode debug aktif
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])