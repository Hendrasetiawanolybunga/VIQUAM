from django.contrib import admin
from django.urls import path
from django.conf import settings
# Impor fungsi static
from django.conf.urls.static import static 

urlpatterns = [
    path('admin/', admin.site.urls),
    # Tambahkan path lain di sini
]
# --- Konfigurasi File Media (Hanya digunakan saat DEBUG=True) ---
# Menambahkan konfigurasi untuk melayani file media saat mode debug aktif
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)