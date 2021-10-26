from django.conf.urls import url
from users.views import (
    RegisterView,
    UsernameCountView,
    MobileCountView,
    LoginView,
    LogoutView,
    UserInfoView,
    EmailView,
    VerifyEmailView,
    AddressView,
    CreateAddressView,
    UpdateDestroyAddressView,
    DefaultAddressView,
    UpdateTitleAddressView,
    ChangePasswordView,
    UserBrowseHistory,
)

urlpatterns = [
    url(r'^register/$',RegisterView.as_view(),name='register'),
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$',UsernameCountView.as_view(),name='usernames'),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$',MobileCountView.as_view(),name='mobiles'),

    url(r'^login/$',LoginView.as_view(),name='login'),
    url(r'^logout/$',LogoutView.as_view(),name='logout'),
    url(r'^changepassword/$',ChangePasswordView.as_view(),name='pass'),

    url(r'^info/$',UserInfoView.as_view(),name='info'),
    url(r'^emails/$',EmailView.as_view()),
    url(r'^emails/verification/$',VerifyEmailView.as_view()),

    url(r'^addresses/$',AddressView.as_view(),name='address'),
    url(r'^addresses/create/$',CreateAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/$',UpdateDestroyAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/default/$',DefaultAddressView.as_view()),
    url(r'^addresses/(?P<address_id>\d+)/title/$',UpdateTitleAddressView.as_view()),

    url(r'^browse_histories/$',UserBrowseHistory.as_view()),
]