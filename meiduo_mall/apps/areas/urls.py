from django.conf.urls import url
from areas.views import AreasView


urlpatterns = [
    url(r'^areas/$', AreasView.as_view()),

]