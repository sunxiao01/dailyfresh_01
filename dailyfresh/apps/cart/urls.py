from django.conf.urls import url
from cart import views

urlpatterns = [
    url(r'^add$', views.AddCartView.as_view(), name='addcart'),
    # http://127.0.0.1:8000/cart/info
    url(r'^info$', views.CartView.as_view(), name='cartinfo'),
    # http://127.0.0.1:8000/cart/update
    url(r'^update$', views.UpdateCartView.as_view(), name='update_cart'),
    # http://127.0.0.1:8000/cart/delete
    url(r'^delete$', views.DeleteCartView.as_view(), name='delete_cart'),
]