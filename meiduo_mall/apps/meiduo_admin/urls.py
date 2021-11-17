from django.conf.urls import url
from rest_framework_jwt.views import obtain_jwt_token
from meiduo_admin.views.statistical import (
    UserTotalCountView,
    UserDayCountView,
    UserActiveCountView,
    UserOrderCountView,
    UserMonthCountView,
    GoodsDayView,
)


urlpatterns = [
    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^statistical/total_count/$', UserTotalCountView.as_view()),
    url(r'^statistical/day_increment/$', UserDayCountView.as_view()),
    url(r'^statistical/day_active/$', UserActiveCountView.as_view()),
    url(r'^statistical/day_orders/$', UserOrderCountView.as_view()),
    url(r'^statistical/month_increment/$', UserMonthCountView.as_view()),
    url(r'^statistical/goods_day_views/$', GoodsDayView.as_view()),
]