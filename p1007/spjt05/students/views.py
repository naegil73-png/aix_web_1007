from django.shortcuts import render

# 학생성적입력페이지


# Create your views here.
def swrite(request):
    return render(request,'swrite.html')

def slist(request):
    return render(request,'slist.html')