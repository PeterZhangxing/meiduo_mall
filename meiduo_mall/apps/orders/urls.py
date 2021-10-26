from django.conf.urls import url
from orders.views import (
    OrderSettlementView,
    OrderCommitView,
    OrderSuccessView,
    UserOrderInfoView,
    OrderCommentView,
    GoodsCommentView,
)


urlpatterns = [
    url(r'^orders/settlement/$', OrderSettlementView.as_view(), name='settlement'),
    url(r'^orders/commit/$', OrderCommitView.as_view()),
    url(r'^orders/success/$', OrderSuccessView.as_view()),
    url(r'^orders/info/(?P<page_num>\d+)/$', UserOrderInfoView.as_view(),name='info'),
    url(r'^orders/comment/$', OrderCommentView.as_view(),name='comment'),
    url('r^comments/(?P<sku_id>\d+)/',GoodsCommentView.as_view(),name='goods')
]