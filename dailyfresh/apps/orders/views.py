from django.shortcuts import render, redirect
from utils.views import LoginRequiredMixin
from django.views.generic import View
from goods.models import GoodsSKU
from django.core.urlresolvers import reverse
from django_redis import get_redis_connection
from users.models import Address, User

# Create your views here.


class PlaceOrderView(LoginRequiredMixin, View):

    def post(self, request):

        # 判断用户是否登陆：LoginRequiredMixin

        # 获取参数：sku_ids, count
        sku_ids = request.POST.getlist('sku_ids')
        count = request.POST.get('count')
        user_id = request.user.id

        # 校验sku_ids参数：not
        if not sku_ids:
            return redirect(reverse('goods:index'))
        # 定义一个空的列表，用于存储商品的sku信息
        skus = []
        transfer_cost = 10
        total_count = 0
        total_amount = 0
        # 校验count参数：用于区分用户从哪儿进入订单确认页面
        if count is None:
            # 如果空，则表示是从购物车的去结算页面过来

            # 商品的数量从redis中获取
            redis_conn = get_redis_connection('default')
            cart_dict = redis_conn.hgetall('cart_%s' % user_id)

            # 查询商品数据
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    return redirect(reverse('goods:index'))

                try:
                    sku_count = cart_dict[sku_id.encode()]
                except Exception:
                    return redirect(reverse('cart:cartinfo'))
                sku_count =int(sku_count)
                # 计算每个商品的价格小计
                sku_amount = sku.price*sku_count
                #动态的给sku对象添加count和amount属性
                sku.count = sku_count
                sku.amount = sku_amount
                total_count += sku_count
                total_amount += sku_amount
                skus.append(sku)

        else:
            # 如果count不为空，则是从详情页面过来

            # 查询商品数据
            for sku_id in sku_ids:
                try:
                    sku = GoodsSKU.objects.get(id=sku_id)
                except GoodsSKU.DoesNotExist:
                    return redirect(reverse('goods:index'))

                # 商品的数量从request中获取,并try校验
                try:
                    count = int(count)
                except Exception:
                    return redirect(reverse('goods:detail', args=sku_id))
                # 判断库存：立即购买没有判断库存
                if sku.stock < count:
                    return redirect(reverse('goods:detail', args=sku_id))
                sku.count = count
                amount = count*sku.price
                sku.amount = amount
                total_count += count
                total_amount += amount
                skus.append(sku)

        total_cost = total_amount + transfer_cost
        # 查询用户地址信息
        try:
            address = Address.objects.filter(user=request.user).latest('create_time')
        except Address.DoesNotExist:
            address = None
        # 构造上下文

        context = {
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'transfer_cost': transfer_cost,
            'total_cost': total_cost,
            'address': address,
        }

        return render(request, 'place_order.html', context)


