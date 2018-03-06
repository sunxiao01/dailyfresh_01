from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import GoodsCategory, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexCategoryGoodsBanner, Goods
from orders.models import OrderGoods
from django.core.cache import cache
from django_redis import get_redis_connection
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage
import json

# Create your views here.

class BaseCartView(View):

    def get_cart_num(self, request):

        cart_num = 0

        if request.user.is_authenticated():
            # 创建redis链对象接
            redis_conn = get_redis_connection('default')

            # 如果为已登录用户，则查询购物车数据
            cart_dict = redis_conn.hgetall('cart_%s'% request.user.id)

            # 遍历购物车字典，对购物车数量累加求和
            for val in cart_dict.values():
                cart_num += int(val)

        else:
            # 从缓存中获取购物车信息，为json字符串
            cart_json = request.COOKIES.get('cart')
            if cart_json is not None:
                cart_dict = json.loads(cart_json)   #将json字符串转换未json字典
            else:
                cart_dict = {}

            for val in cart_dict.values():
                cart_num += val

        return cart_num

class ListView(BaseCartView):
    """获取商品列表页面"""

    def get(self, request, category_id, page_num):
        """展示商品详情页面"""
        # 获取排序方式
        sort = request.GET.get('sort', 'default')

        # 判断category是否正确
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 查询新品推荐
        new_skus = GoodsSKU.objects.filter(category=category).order_by('-create_time')[:2]

        # 查询所有商品分类
        categorys = GoodsCategory.objects.all()

        # 查询商品分类对应的sku数据信息:按照排序方式查询
        if sort == 'hot':
            skus = GoodsSKU.objects.filter(category=category).order_by('-sales')
        elif sort == 'price':
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            sort = 'default'

        # 对skus进行分页
        page_num = int(page_num)
        paginator = Paginator(skus, 2)
        # 校验page_num
        try:
            page_skus = paginator.page(page_num)
        except EmptyPage:
            page_skus = paginator.page(1)

        page_list = paginator.page_range

        # 查询购物车
        cart_num = self.get_cart_num(request)

        # 构造上下文
        context = {
            'categorys': categorys,
            'category': category,
            'new_skus': new_skus,
            'page_skus': page_skus,
            'page_list': page_list,
            'sort': sort,
            'cart_num': cart_num,
        }

        return render(request, 'list.html', context)


class DetailView(BaseCartView):

    def get(self, request, sku_id):

        # 查询所有的商品分类
        categorys = GoodsCategory.objects.all()

        # 查询商品的SKU信息
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # # 查询商品的详情介绍信息
        # goods = sku.goods

        # 查询商品订单评论信息
        sku_orders = sku.ordergoods_set.all().order_by('-create_time')[:30]

        if sku_orders:
            for sku_order in sku_orders:
                sku_order.ctime = sku_order.create_time.strftime('%Y-%m-%d %H:%M:%S')
                sku_order.username = sku_order.order.user.username
        else:
            sku_orders = []

        # 查询最新商品推荐信息
        new_skus = GoodsSKU.objects.filter(category=sku.category).order_by('-create_time')[:2]

        # 查询其他规格的商品
        other_skus = sku.goods.goodssku_set.exclude(id=sku_id)

        context = {
            'categorys': categorys,
            'sku': sku,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            'other_skus': other_skus,
        }

        cart_num = self.get_cart_num(request)
        # 如果已登陆 查询购物车数量
        if request.user.is_authenticated():
            user_id = request.user.id
            redis_conn = get_redis_connection('default')
            # 记录在用户登陆时记录浏览信息
            redis_conn.lrem('history_%s' % user_id, 0, sku_id)
            redis_conn.lpush('history_%s' % user_id, sku_id)
            redis_conn.ltrim('history_%s' % user_id, 0, 4)

        context['cart_num'] = cart_num


        return render(request, 'detail.html', context)


class IndexView(BaseCartView):

    def get(self, request):

        # 读取缓存
        context = cache.get('index_page_data')

        if context is None:
            print("没有缓存")
            # 查询用户user
            # user = request.user

            # 查询商品分类
            categorys = GoodsCategory.objects.all()

            # 查询轮播
            banners = IndexGoodsBanner.objects.all().order_by('index')

            # 查询活动商品
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 查询主页商品分类信息列表
            for category in categorys:
                title_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=0).order_by('index')
                category.title_banners = title_banners

                image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')[0:4]
                category.image_banners = image_banners

            context = {
                'categorys': categorys,
                'banners': banners,
                'promotion_banners': promotion_banners,
            }
            cache.set('index_page_data', context, 3600)

        # 查询购物车
        cart_num = self.get_cart_num(request)

        context.update(cart_num=cart_num)

        return render(request, 'index.html', context)
