from django.conf.urls import url, include
from verifications.views import ImageCodeView,SMSCodeView

urlpatterns = [
    url(r'^image_codes/(?P<uuid>[\w-]+)/$',ImageCodeView.as_view()),
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/$',SMSCodeView.as_view()),
]