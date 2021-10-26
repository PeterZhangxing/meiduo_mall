import datetime

from django import http
from django.core.paginator import Paginator
from django.shortcuts import render
from collections import OrderedDict
from django.views import View

# Create your views here.
from goods.models import *
from contents.utils import get_categories
from goods.utils import get_breadcrumb
from utils.response_code import RETCODE
import logging


logger = logging.getLogger("django")


class ListView(View):

    def get(self,request,category_id,page_num):

        try:
            category = GoodsCategory.objects.get(pk=category_id)
        except Exception as e:
            return http.HttpResponseNotFound('GoodsCategory does not exist')

        sort = request.GET.get('sort', 'default')

        categories = get_categories()
        breadcrumb = get_breadcrumb(category)

        if sort == 'price':
            sort_field = 'price'
        elif sort == 'hot':
            sort_field = '-sales'
        else:
            sort = 'default'
            sort_field = 'create_time'

        skus = category.sku_set.filter(is_launched=True).order_by(sort_field)
        paginator = Paginator(skus, 5)
        page_skus = paginator.page(page_num)
        total_page = paginator.num_pages

        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sort': sort,  # 排序字段
            'category': category,  # 第三级分类
            'page_skus': page_skus,  # 分页后数据
            'total_page': total_page,  # 总页数
            # 'page_num': page_num,  # 当前页码
            'page_num': page_skus.number,  # 当前页码
            'category_id': category_id,
        }

        return render(request, 'list.html',context)


class HotGoodsView(View):

    def get(self,request,category_id):

        hot_skus = []
        try:
            category = GoodsCategory.objects.get(pk=category_id)
        except Exception as e:
            return http.HttpResponseNotFound('GoodsCategory does not exist')

        skus = category.sku_set.filter(is_launched=True).order_by('-sales')[:2]
        for sku in skus:
            hot_skus.append({
                'id': sku.id,
                'default_image_url': sku.default_image.url,
                'name': sku.name,
                'price': sku.price
            })

        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'hot_skus':hot_skus})


class DetailView(View):

    def get(self,request,sku_id):

        try:
            sku = SKU.objects.get(id=sku_id)
        except Exception as e:
            return render(request, '404.html')

        categories = get_categories()
        breadcrumb = get_breadcrumb(sku.category)

        sku_specs = sku.specs.order_by('spec_id')
        sku_key = []
        for spec in sku_specs:
            sku_key.append(spec.option.id)

        skus = sku.spu.sku_set.all()
        spec_sku_map = {}
        for s in skus:
            # 获取sku的规格参数
            s_specs = s.specs.order_by('spec_id')
            # 用于形成规格参数-sku字典的键
            key = []
            for spec in s_specs:
                key.append(spec.option.id)
            # 记录每一个商品所有规格(颜色、内存等)的id，和该商品id的对应关系
            spec_sku_map[tuple(key)] = s.id

        goods_specs = sku.spu.specs.order_by('id')
        if len(sku_key) < len(goods_specs):
            return

        for index, spec in enumerate(goods_specs): # [颜色、版本、内存]
            # 复制当前sku的规格键
            key = sku_key[:] # [金色、14.4、128G]

            spec_options = spec.options.all()
            for option in spec_options: # [金色、银色、玫瑰]
                # 在规格参数sku字典中查找符合当前规格的sku
                key[index] = option.id
                option.sku_id = spec_sku_map.get(tuple(key))
            spec.spec_options = spec_options

        context = {
            'categories': categories,
            'breadcrumb': breadcrumb,
            'sku': sku,
            'specs': goods_specs,
        }

        return render(request, 'detail.html', context)


class DetailVisitView(View):

    def post(self, request, category_id):

        try:
            category = GoodsCategory.objects.get(id=category_id)
        except Exception as e:
            return http.HttpResponseForbidden('缺少必传参数')

        # t = timezone.localtime()
        # today_str = '%d-%02d-%02d' % (t.year, t.month, t.day)
        # today_date = datetime.datetime.strptime(today_str, '%Y-%m-%d')
        today_date = datetime.datetime.now().date()
        try:
            counts_data = category.goodsvisitcount_set.get(date=today_date)
        except Exception as e:
            # logger.error(e)
            counts_data = GoodsVisitCount()

        try:
            counts_data.category = category
            counts_data.count += 1
            counts_data.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('服务器异常')

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})