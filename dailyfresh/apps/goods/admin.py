from django.contrib import admin
from goods.models import GoodsCategory, Goods, GoodsSKU, GoodsImage, IndexPromotionBanner, IndexCategoryGoodsBanner
from celery_tasks.tasks import generate_static_index_html
from django.core.cache import cache

# Register your models here.

class BaseAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        obj.save()
        generate_static_index_html.delay()
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        obj.delete()
        generate_static_index_html.delay()
        cache.delete('index_page_data')


class GoodsCategoryAdmin(BaseAdmin):
    pass

class GoodsAdmin(BaseAdmin):
    pass

class GoodsSKUAdmin(BaseAdmin):
    pass

class GoodsImageAdmin(BaseAdmin):
    pass

class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass

class IndexPromotionBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsCategory, GoodsCategoryAdmin)
admin.site.register(Goods, GoodsAdmin)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(GoodsImage, GoodsImageAdmin)
admin.site.register(IndexPromotionBanner, IndexCategoryGoodsBannerAdmin)
admin.site.register(IndexCategoryGoodsBanner,IndexCategoryGoodsBannerAdmin)