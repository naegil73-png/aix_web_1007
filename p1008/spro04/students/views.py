from django.shortcuts import render
from students.models import Stu

def swrite(request):
    if request.method == "GET":
        print("GET페이지가 로딩되었습니다.")
        return render(request, 'swrite.html')
    elif request.method == "POST":
        name = request.POST.get("name")
        major = request.POST.get("major")
        age = request.POST.get("age")
        grade = request.POST.get("grade")
        gender = request.POST.get("gender")

        qs = Stu(name=name,major=major,age=age,grade=grade,gender=gender)
        qs.save()

    print(name,major,age,grade,gender)
    return render('/')

def slist(request):
    return render(request, 'slist.html')

