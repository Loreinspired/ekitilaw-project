# laws/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # This is your existing search page URL
    # (It's path('', ...) if you made it the homepage)
    path('', views.search, name='search'), 
    
    # --- ADD THIS NEW LINE ---
    # This creates a URL like /laws/criminal-law-2011/
    # The <slug:law_slug> part captures the URL-friendly name
    # and passes it to our view as the 'law_slug' argument.
    path('laws/<slug:law_slug>/', views.law_detail, name='law_detail'),
]