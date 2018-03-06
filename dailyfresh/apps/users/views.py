from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic import View
from django.core.urlresolvers import reverse
import re
from users.models import User, Address
from django import db
from celery_tasks.tasks import send_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import SignatureExpired
from django.contrib.auth import authenticate, login, logout
from utils.views import LoginRequiredMixin
from django_redis import get_redis_connection
from goods.models import GoodsSKU
import json


class UserInfoView(LoginRequiredMixin, View):
    """用户信息处理"""
    def get(self, request):
        """获取用户信息页面，查询用户信息，浏览记录，并渲染模板"""
        user = request.user
        # 查询基本信息：用户名\地址信息（地址、电话）
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None

        # 查询浏览记录
        # 创建一个连接到redis的连接对象
        redis_conn = get_redis_connection('default')
        sku_ids = redis_conn.lrange('history_%s' % user.id,0,4)
        sku_goods = []
        for sku_id in sku_ids:
            sku_good = GoodsSKU.objects.get(id=sku_id)
            sku_goods.append(sku_good)
        # 构造上下文
        context = {
            'address': address,
            'sku_goods': sku_goods,
        }
        # 渲染模板
        return render(request, 'user_center_info.html', context)


class AddressView(LoginRequiredMixin, View):
    """用户中心"""
    def get(self, request):
        """提供地址页面， 查询地址信息，并且渲染"""
        # 获取登录的用户的地址
        user = request.user
        # 查询登陆用户的地址信息
        # address = user.address_set.order_by('-create_time')[0]
        try:
            address = user.address_set.latest('create_time')
        except Address.DoesNotExist:
            address = None
        # 构造上下文
        context = {
            # 'user': user,
            'address': address,
        }
        # 渲染模板
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        """处理地址修改逻辑"""
        # 读取用户地址参数信息
        recv_name = request.POST.get('recv_name')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        recv_mobile = request.POST.get('recv_mobile')

        # 判断地址信息是否为空
        if all([recv_name, addr, zip_code, recv_mobile]):
            Address.objects.create(
                user=request.user,
                receiver_name = recv_name,
                receiver_mobile = recv_mobile,
                detail_addr = addr,
                zip_code = zip_code,
            )
        return redirect(reverse('users:address'))


    """
    原始方法：
        def get(self, request):
        if not request.user.is_authenticated():
            return redirect(reverse('users:login'))
        else:
            return render(request, 'user_center_site.html')

    """

class LogoutView(View):
    """退出登陆"""
    def get(self, request):
        logout(request)
        return redirect(reverse('users:login'))

class LoginView(View):
    """登录"""
    def get(self, request):
        """提供登录页面"""
        return render(request, 'login.html')

    def post(self, request):
        """处理登陆逻辑"""
        # 获取用户登录参数
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')

        # 校验参数
        if not all([username, pwd]):
            return redirect(reverse('users:login'))
        user = authenticate(username=username, password=pwd)
        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})
        if user.is_active == False:
            return render(request, 'login.html', {'errmsg': '请激活'})
        login(request, user)

        # 状态保持，如果用户勾选了记住用户名，则保持10天，否则，保持0秒
        remembered = request.POST.get('remembered')
        if remembered != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(60*60*24*10)

        #登陆时获取cookies中的缓存数据，并将cookies中的缓存数据合并到redis数据库
        cache_cart_json_str = request.COOKIES.get('cart')

        # 判断json字典是否为空，如果为空则，跳过，如果不为空则合并到redis数据库
        user_id = request.user.id
        if cache_cart_json_str is not None:
            cache_cart_dict = json.loads(cache_cart_json_str)

            # 连接redis数据库，获取redis中的购物车信息
            redis_conn = get_redis_connection('default')
            redis_cart_dict_bytes = redis_conn.hgetall('cart_%s' % user_id)

            # 遍历缓存中的购物车信息
            for sku_id, count in cache_cart_dict.items():
                sku_id = sku_id.encode()
                if sku_id in redis_cart_dict_bytes:
                    origin_count = redis_cart_dict_bytes[sku_id]
                    count += int(origin_count)
                redis_cart_dict_bytes[sku_id] = count

            if redis_cart_dict_bytes:
                """如果购物车中有数据，则保存到redis"""
                redis_conn.hmset('cart_%s' % user_id, redis_cart_dict_bytes)

        # 判断链接中有没有next
        next = request.GET.get('next')

        if next is None:
            """如果没有next,登陆后进入主页"""
            return redirect(reverse('goods:index'))
        else:
            """如果有next, 进入到next页面"""
            return redirect(next)


# Create your views here.
class ActiveView(View):
    """邮件激活"""

    def get(self, request, token):
        """处理激活请求"""
        s = Serializer(settings.SECRET_KEY, 3600)
        try:
            result = s.loads(token)
        except SignatureExpired:
            return HttpResponse("激活链接已过期")

        user_id = result.get("confirm")

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return HttpResponse("该用户不存在")

        user.is_active = True
        user.save()

        return redirect(reverse("users:login"))


class RegisterView(View):

    def get(self, request):
        """提供注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """处理注册逻辑"""
        # 1. 接收用户注册请求数据
        user_name = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        cpwd = request.POST.get('cpwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 2. 校验数据是否为空
        if not all([user_name, pwd, cpwd, email]):
            return redirect(reverse('users:register'))
        # 3. 校验数据是否有效
        if not re.match(r"^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$", email):
            return render(request, 'register.html', {'errmsg':'您输入的邮箱格式不正确'})
        # 4. 校验是否已勾选用户协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg':'请勾选用户协议'})
        # 5. 保存数据
        try:
            user = User.objects.create_user(user_name, email, pwd)
        except db.IntegrityError:
            return render(request, 'register.html', {'errmsg':'该用户名已注册'})
        # 6. 将用户初始化为未激活状态
        user.is_active = False
        user.save()
        # 生产token
        token = user.generate_active_token()
        # 7. 发送激活邮件
        send_active_email.delay(email, user_name, token)
        return redirect(reverse('goods:index'))

# def register(request):
#     """函数视图"""
#
#     if request.method == 'GET':
#         """提供注册页面"""
#         return render(request, 'register.html')
#     if request.method == 'POST':
#         """处理注册逻辑，保存注册信息"""
#         return HttpResponse("注册逻辑处理")