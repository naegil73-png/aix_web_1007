from django.urls import path
from django.urls import include
from . import views # 현재 자기 폴더는 .에 views.py를 들고와라

urlpatterns = [
    path('s_write/', views.s_write), # students app안에 urls를 찾아감.
]