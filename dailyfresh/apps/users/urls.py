from django.conf.urls import url
from users import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # url(r'^register$', views.register)
    url(r'^register$', views.RegisterView.as_view(), name='register'),
    # http://127.0.0.1:8000/users/active/user.id
    url(r'^active/(?P<token>.+)$', views.ActiveView.as_view(), name='active'),
    # http://127.0.0.1:8000/users/login
    url(r'^login$', views.LoginView.as_view(), name='login'),
    # http://127.0.0.1:8000/users/logout
    url(r'^logout$', views.LogoutView.as_view(), name='logout'),
    # ttp://127.0.0.1:8000/users/address
    url(r'^address$', views.AddressView.as_view(), name='address'),
    # http://127.0.0.1:8000/users/address
    # url(r'^address$', login_required(views.AddressView.as_view()), name='address'),
    # http://127.0.0.1:8000/users/userinfo
    url(r'^userinfo$', views.UserInfoView.as_view(), name='userinfo'),
]