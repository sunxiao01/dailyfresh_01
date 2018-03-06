from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
import json

# Create your views here.

class DeleteCartView(View):
    """从购物车中删除商品"""

    def post(self, request):
        # 获取客户发送的要删除的sku_id信息
        sku_id = request.POST.get('sku_id')

        # 判断sku_id是否存在，若不存在，则返回错误信息，若存在则继续
        if sku_id is None:
            return JsonResponse({'code': 2, 'message':'参数不完整'})

        # 查询sku_id是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 3, 'message': '您要删除的商品不存在'})

        #判断用户是否登陆，若已经登陆，则从redis中删除购物车信息，若未登陆，则从cookies中删除购物车信息

        if request.user.is_authenticated():
            """用户已登陆的情况"""
            user_id = request.user.id
            redis_conn = get_redis_connection('default')
            redis_conn.hdel('cart_%s' % user_id, sku_id)

        else:
            """用户未登陆的情况"""
            # 获取cookies中的购物车信息
            cache_cart_json_str = request.COOKIES.get('cart')

            # 如果缓存中有数据，则执行删除，若无数据，则直接提示删除成功
            if cache_cart_json_str is not None:
                """购物车不为空"""
                # 转换为字典
                cache_cart_dict = json.loads(cache_cart_json_str)

                #判断购物车中是否有该商品，若有则执行删除若没有则继续
                if sku_id in cache_cart_dict:
                    del cache_cart_dict[sku_id]

                # 将cart字典转换为json字符串，然后保存到cookies中
                cache_cart_json_newstr = json.dumps(cache_cart_dict)

                response = JsonResponse({'code':0, 'message':'删除成功'})
                response.set_cookie('cart', cache_cart_json_newstr)

                return response

        return JsonResponse({'code':0, 'message':'删除成功'})


class UpdateCartView(View):

    def post(self, request):
        # 获取用户发送的数据，包含sku_id和count
        sku_id = request.POST.get('sku_id')
        sku_count = request.POST.get('count')
        # 判断参数不为空
        if not all([sku_id, sku_count]):
            """如果为空，则返回错误信息，不为空，则继续执行"""
            return JsonResponse({'code':2, 'message':'参数不完整'})

        # 判断商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code': 3, 'message':'商品不存在'})

        # 判断count是否为数字
        try:
            sku_count = int(sku_count)
        except Exception:
            return JsonResponse({'code':4, 'message':'商品数量不正确，请输入整数'})

        # 判断商品数量是否超出库存
        if sku_count > sku.stock:
            return JsonResponse({'code':5, 'message':'库存不足'})

        user_id = request.user.id

        #  判断用户是否登陆，如果已经登陆，则更新redis购物车中的信息，若未登陆则更新cookies中的购物车信息
        if request.user.is_authenticated():
            """如果已登陆，则获取并更新redis中的cookies信息"""
            redis_conn = get_redis_connection('default')
            redis_conn.hset('cart_%s' % user_id, sku_id, sku_count)

            return JsonResponse({'code':0, 'message':'添加购物车成功'})

        else:
            """如果未登陆，则获取并更新cookies信息"""
            # 获取cache中的购物车信息，返回json字符串
            cache_cart_json_str = request.COOKIES.get('cart')

            # 判断是否为空，如果为空，则赋值一个空字典，如果不为空，则将json字符串转换为json_dict
            if cache_cart_json_str is not None:
                cache_cart_json_dict = json.loads(cache_cart_json_str)
            else:
                cache_cart_json_dict = {}

            cache_cart_json_dict[sku_id]=sku_count

            # 将json字典转换为json字符串
            cache_cart_json_newstr = json.dumps(cache_cart_json_dict)

            response = JsonResponse({'code':0, 'message':'添加购物车成功'})
            response.set_cookie('cart', cache_cart_json_newstr)

            return response


class CartView(View):

    def get(self, request):
        """展示购物车页面"""
        # 判断用户是否登陆，如果已经登陆从redis中获取购物车信息，如果未登陆从缓存中获取
        if request.user.is_authenticated():
            # 连接redis查询购物车数据
            redis_conn = get_redis_connection('default')
            user_id = request.user.id
            # 获取bytes类型的字典
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)

        else:
            # 从cookies中获取购物车信息:为json字符串
            cart_json_str = request.COOKIES.get('cart')
            #判断是否为空，如果不为空则转换为字典，否则，赋值一个空字典
            if cart_json_str is not None:
                cart_dict = json.loads(cart_json_str)
            else:
                cart_dict = {}

        total_count = 0
        total_amount = 0
        skus = []
        #  遍历购物车字典
        for sku_id, count in cart_dict.items():
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                continue
            count = int(count)
            sku.count = count
            sku.amount = count * sku.price

            total_count += count
            total_amount += sku.amount
            skus.append(sku)


        #   构造上下文
        context = {
            'total_count': total_count,
            'total_amount': total_amount,
            'skus': skus,
        }

        return render(request, 'cart.html', context)





class AddCartView(View):

    def post(self, request):

        # 接收数据sku_id, count
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验参数:是否为空
        if not all([sku_id, count]):
            return JsonResponse({'code':2, 'message':'参数不完整'})

        # 校验sku_id是否正确
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'code':3, 'message': '商品不存在'})

        # 校验count是否为整数，是否超过库存
        try:
            count = int(count)
        except Exception:
            return JsonResponse({'code':4, 'message': '商品数量错误'})

        if count > sku.stock:
            return JsonResponse({'code':5, 'message':'库存不足'})

        if request.user.is_authenticated():
            """如果已经登陆"""
            # 接收数据user_id
            user_id = request.user.id

            # 操作redis数据库，存储商品到购物车
            redis_conn = get_redis_connection('default')

            # redis数据库中，购物车的数据格式：cart_userid:{sku_id: count, sku_id2：count2}
            origin_count = redis_conn.hget('cart_%s' % user_id, sku_id)

            # 需要先获取该商品是否在购物车中已经存在，
            if origin_count is not None:
                count += int(origin_count)

            # 若存在则累加count，且校验累加后的count是否超出库存
            if count > sku.stock:
                return JsonResponse({'code': 5, 'message': '库存不足'})

            # 若不存在，则直接添加到redis数据库
            redis_conn.hset('cart_%s' % user_id, sku_id, count)

            # 查询购物车的总数，返回给浏览器
            cart_num = 0
            cart_dict_bytes = redis_conn.hgetall('cart_%s' % user_id)

            for sku_count in cart_dict_bytes.values():
                cart_num += int(sku_count)

            # json响应添加购物车之后的数据
            return JsonResponse({'code': 0, 'message': '添加购物车成功', 'cart_num': cart_num})

        else:
            """如果用户未登陆"""
            # 查询缓存中有没有购物车数据
            cart_json = request.COOKIES.get('cart')

            # 如果有购物车数据，则获取购物车数量
            if cart_json is not None:
                # 将json字符串转换成json字典
                cart_dict = json.loads(cart_json)
            else:
                # 若没有则未空
                cart_dict = {}

            # 设置新的购物车缓存信息，
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id]
                # 如果sku_id已经存在cart——dict中，则读取origin_count信息进行累加
                count += origin_count

            # 若存在则累加count，且校验累加后的count是否超出库存
            if count > sku.stock:
                return JsonResponse({'code': 5, 'message': '库存不足'})
            # 如果不存在购物车中，则添加
            cart_dict[sku_id] = count

            # 获取购物车数量
            cart_num = 0
            for val in cart_dict.values():
                cart_num += val

            cart_json_new = json.dumps(cart_dict)
            response = JsonResponse({'code': 0, 'message': '添加购物车成功', 'cart_num':cart_num})
            response.set_cookie('cart', cart_json_new)

            return response



