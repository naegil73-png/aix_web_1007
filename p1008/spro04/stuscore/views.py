from django.shortcuts import render

# Create your views here.
def score_write(request):
    return render(request, 'score_write.html')