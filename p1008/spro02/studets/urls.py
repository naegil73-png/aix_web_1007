from django.urls import path,include
from . import views

app_name="studets"
urlpatterns = [
    path('swrite/', 'views.swrite'),
]
