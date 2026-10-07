from django.urls import path,include
from . import views

app_name = 'students'
urlpatterns = [
    path('swrite/', views.swrite, name='swrite'),    # url에 swrite가 들어오면, views파일에서 swrite함수를 찾아라
]