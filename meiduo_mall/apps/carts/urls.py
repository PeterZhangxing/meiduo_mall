from django.conf.urls import url
from carts.views import CartsView,CartsSelectAllView,CartsSimpleView


urlpatterns = [
    url(r'^carts/$', CartsView.as_view(),name="info"),
    url(r'^carts/selection/$', CartsSelectAllView.as_view()),
    url(r'^carts/simple/$', CartsSimpleView.as_view()),

]