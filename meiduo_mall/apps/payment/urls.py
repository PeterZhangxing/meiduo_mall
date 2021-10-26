from django.conf.urls import url
from payment.views import PaymentView,PaymentStatusView

urlpatterns = [
    url(r'^payment/(?P<order_id>\d+)/$', PaymentView.as_view()),
    url(r'^payment/status/$', PaymentStatusView.as_view()),
]