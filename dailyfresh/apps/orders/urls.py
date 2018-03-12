from django.conf.urls import url
from orders import views

urlpatterns = [
    # http://127.0.0.1:8000/orders/placeorder
    url(r'^placeorder$', views.PlaceOrderView.as_view(), name='placeorder'),
]