from django.shortcuts import render
from django.http import HttpResponse
from django.views.generic import View

# Create your views here.

class RegisterView(View):

    def get(self, request):
        """提供注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """处理注册逻辑"""
        return HttpResponse("处理注册逻辑！")

# def register(request):
#     """函数视图"""
#
#     if request.method == 'GET':
#         """提供注册页面"""
#         return render(request, 'register.html')
#     if request.method == 'POST':
#         """处理注册逻辑，保存注册信息"""
#         return HttpResponse("注册逻辑处理")