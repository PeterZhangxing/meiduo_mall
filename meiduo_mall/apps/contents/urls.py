from django.conf.urls import url
from contents.views import IndexView

urlpatterns = [
    url(r'^$',IndexView.as_view(),name='index'),
]