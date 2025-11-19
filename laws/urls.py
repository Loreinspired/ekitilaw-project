from django.urls import path
from . import views

app_name = "laws"

urlpatterns = [
    path("", views.search, name="home"),
    path("search/", views.search, name="search"),
    path("search/laws/<slug:law_slug>/", views.law_detail, name="law_detail"),
]
