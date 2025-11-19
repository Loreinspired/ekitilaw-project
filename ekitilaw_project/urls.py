# ekitilaw_project/urls.py

from django.contrib import admin
from django.urls import path, include  # <-- 1. IMPORT 'include'

# --- (These 2 lines are for your PDF uploads) ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- 2. ADD THIS NEW LINE ---
    # This tells Django: "If the URL starts with 'search/',
    # send it to the 'laws.urls' file for instructions."
    path('', include('laws.urls')),
]

# --- (This part is for your PDF uploads) ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)