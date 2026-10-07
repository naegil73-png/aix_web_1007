from django.shortcuts import render # render는 파이썬 코드와 html파일을 합쳐 웹페이지 만들어주는 명령어

def swrite(request): # 사용자가 브라우저 클릭, 입력할 때 발생하는 사용자 정보를 request가 받음. 즉, 사용자가 웹페이지에 접속하면.. 이라는 뜻
    return render(request,'swrite.html') # swrite.html파일을 웹브라우저로 형태로 전송하라. django는 기본적으로 templates에 있는 파일을 찾아 실행함
# 