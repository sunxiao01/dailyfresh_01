from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from goods.models import GoodsCategory, IndexGoodsBanner, IndexPromotionBanner, GoodsSKU, IndexCategoryGoodsBanner
from django.template import loader
import os

# 创建celery客户端
# 参数1：指定任务所在的路径，从包名开始；参数2：指定任务队列（broker）,以redis数据库为例
app = Celery('celery_tasks.tasks', broker="redis://192.168.102.128:6379/2")

#生产任务
@app.task
def send_active_email(to_email, user_name, token):
    """封装发送邮件的任务"""
    subject = "天天生鲜用户激活"
    body = ""
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_body = '<h1>尊敬的用户 %s, 感谢您注册天天生鲜！</h1>' \
                '<br/><p>请点击此链接激活您的帐号<a href="http://127.0.0.1:8000/users/active/%s">' \
                'http://127.0.0.1:8000/users/active/%s</a></p>' % (user_name, token, token)
    send_mail(subject=subject, message=body, from_email=sender, recipient_list=receiver, html_message=html_body)

@app.task
def generate_static_index_html():
    """异步的生成静态主页"""
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

        image_banners = IndexCategoryGoodsBanner.objects.filter(category=category, display_type=1).order_by('index')[
                        0:4]
        category.image_banners = image_banners

    # 查询购物车
    cart_num = 0

    context = {
        'categorys': categorys,
        'banners': banners,
        'promotion_banners': promotion_banners,
        'cart_num': cart_num
    }

    # 加载模板
    template = loader.get_template('static_index.html')
    html_data = template.render(context)

    # 保存静态文件
    file_path = os.path.join(settings.STATICFILES_DIRS[0], 'index.html')
    with open(file_path, 'w') as file:
        file.write(html_data)

