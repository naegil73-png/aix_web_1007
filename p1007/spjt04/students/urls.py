from django.urls import path
from django.urls import include
from . import views # 현재 자기 폴더는 .(students)에 views.py를 들고와라

app_name='students'
urlpatterns = [
    path('swrite/', views.swrite,name='swrite'), # students app안에 url을 찾아가라는 명령어
]
