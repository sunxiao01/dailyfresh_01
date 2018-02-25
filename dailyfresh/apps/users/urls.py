from django.conf.urls import url
from users import views

urlpatterns = [
    # url(r'^register$', views.register)
    url(r'^register$', views.RegisterView.as_view(), name='register')
]