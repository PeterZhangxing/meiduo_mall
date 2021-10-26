from collections import OrderedDict

from django.shortcuts import render

# Create your views here.
from django.views import View

from contents.models import ContentCategory
from contents.utils import get_categories


class IndexView(View):

    def get(self,request):
        categories = get_categories()

        contents = OrderedDict()
        content_categories = ContentCategory.objects.all()
        for content_category in content_categories:
            contents[content_category.key] = content_category.content_set.filter(status=True).order_by('sequence')

        context = {
            'categories': categories,
            'contents': contents,
        }

        return render(request, 'index.html', context)