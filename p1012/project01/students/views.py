from django.shortcuts import render,redirect
from students.models import Students

# Create your views here.
#  학생상세보기
def sview(request,name):
    print(f"name데이터: {name}")
    qs = Students.objects.get(name=name)
    context = {'stu':qs}
    return render(request,'sview.html',context)

def slist(request):
    qs = Students.objects.all() # 전체 가져오기
    
    context = {'list':qs}
    return render(request,'slist.html',context) # return render(request,'slist.html',context)
    # db에서 전체리스트 가져오기
    # qs = Students.objects.get(name='홍길동') # 1개만
    # qs = Students.objects.filter(name__contains='홍') # 검색해서 여러개

def swrite(request):
    if request.method == "GET":
        return render(request, 'swrite.html')
    elif request.method == "POST":
        name = request.POST.get('name') 
        major = request.POST.get('major') # 데이터 없어도 에러가 안남
        # major = request.POST['major'] # 이렇게 작성해도 됨. 다만, 데이터가 없으면 에러가 발생
        age = request.POST.get('age')
        grade = request.POST.get('grade')
        gender = request.POST.get('gender')
        # 1.save()
        qs = Students(name=name, major=major,age=age,grade=grade,gender=gender)
        qs.save()
        # 2.create()
        #Students.objects.create(name=name,major=major,age=age,grade=grade,gender=gender)로도 저장가능
        print(f'확인: {name},{major},{age},{grade},{gender}')

        return redirect('/students/slist')