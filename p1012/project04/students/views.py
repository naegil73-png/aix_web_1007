from django.shortcuts import render


# Create your views here.
def swrite(request):
    if request.method == "GET":
        return render(request,'swrite.html')

    elif request.method == "POST":
        name = request.POST.get('name')

def slist(request):
    return render(request, 'slist.html')