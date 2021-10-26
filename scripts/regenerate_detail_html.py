#!/usr/bin/env python

import os
import sys

# sys.path.insert(0, '../')
# print(sys.path)

f_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print(f_path)
sys.path.insert(0, f_path)
# print(sys.path)


if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

import django
django.setup()

from django.template import loader
from django.conf import settings

from goods import models
from contents.utils import get_categories
from goods.utils import get_breadcrumb


def generate_static_sku_detail_html(sku_id):
    sku = models.SKU.objects.get(id=sku_id)

    categories = get_categories()
    breadcrumb = get_breadcrumb(sku.category)

    sku_specs = sku.specs.order_by('spec_id')
    sku_key = []
    for spec in sku_specs:
        sku_key.append(spec.option.id)

    skus = sku.spu.sku_set.all()
    spec_sku_map = {}
    for s in skus:
        s_specs = s.specs.order_by('spec_id')
        key = []
        for spec in s_specs:
            key.append(spec.option.id)
        spec_sku_map[tuple(key)] = s.id

    goods_specs = sku.spu.specs.order_by('id')
    if len(sku_key) < len(goods_specs):
        return

    for index, spec in enumerate(goods_specs):
        key = sku_key[:]
        spec_options = spec.options.all() # 获取这一类商品的每个规格的所有选项
        for option in spec_options:
            key[index] = option.id
            option.sku_id = spec_sku_map.get(tuple(key))
        spec.spec_options = spec_options

    context = {
        'categories': categories,
        'breadcrumb': breadcrumb,
        'sku': sku,
        'specs': goods_specs,
    }

    template = loader.get_template('detail.html')
    html_text = template.render(context)
    file_path = os.path.join(settings.STATICFILES_DIRS[0], *['detail',str(sku_id) + '.html'] )
    with open(file_path, 'w',encoding='utf-8') as f:
        f.write(html_text)


if __name__ == '__main__':
    skus = models.SKU.objects.all()
    for sku in skus:
        print(sku.id)
        generate_static_sku_detail_html(sku.id)