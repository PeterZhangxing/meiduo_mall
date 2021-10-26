import base64
import json
import pickle

from django.shortcuts import render
from django import http
from django.views import View
# Create your views here.
from django_redis import get_redis_connection

from goods.models import SKU
from users import constants
from utils.response_code import RETCODE


class CartsView(View):

    def get(self, request):

        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
                # print(cart_dict)
            else:
                cart_dict = {}

        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        cart_skus = []
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'selected': str(cart_dict.get(sku.id).get('selected')),
                'default_image_url': sku.default_image.url,
                'price': str(sku.price),
                'amount': str(sku.price * cart_dict.get(sku.id).get('count')),
            })
        context = {
            'cart_skus': cart_skus,
        }

        return render(request, 'cart.html', context)

    def post(self, request):

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            SKU.objects.get(id=sku_id)
        except Exception as e:
            return http.HttpResponseForbidden('商品不存在')
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hincrby('carts_%s' % user.id, sku_id, count)
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            pl.execute()

            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            if sku_id in cart_dict:
                count = cart_dict[sku_id]['count'] + count

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()

            response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
            response.set_cookie('carts',cookie_cart_str, max_age=3600 * 24)

            return response

    def put(self, request):

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)

        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        cart_sku = {
            'id': sku_id,
            'count': count,
            'selected': selected,
            'name': sku.name,
            'default_image_url': sku.default_image.url,
            'price': sku.price,
            'amount': sku.price * count,
        }
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '修改购物车成功', 'cart_sku': cart_sku})

        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hset('carts_%s' % user.id, sku_id, count)
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }
            cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cookie_cart_str)

        return response

    def delete(self, request):

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})
        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hdel('carts_%s' % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

            if sku_id in cart_dict:
                del cart_dict[sku_id]
                cookie_cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('carts', cookie_cart_str)

        return response


class CartsSelectAllView(View):

    def put(self,request):
        json_dict = json.loads(request.body.decode())
        selected = json_dict.get('selected', True)

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '全选购物车成功'})
        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            cart = redis_conn.hgetall('carts_%s' % user.id)
            sku_id_list = cart.keys()
            if selected:
                redis_conn.sadd('selected_%s' % user.id, *sku_id_list)
            else:
                redis_conn.srem('selected_%s' % user.id, *sku_id_list)
        else:
            cart = request.COOKIES.get('carts')

            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                for sku_id,sku_dict in cart.items():
                    sku_dict['selected'] = selected
                cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                response.set_cookie('carts', cookie_cart)

        return response


class CartsSimpleView(View):

    def get(self, request):

        user = request.user
        if user is not None and user.is_authenticated:
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }
        else:
            cart_str = request.COOKIES.get('carts')
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                cart_dict = {}

        cart_skus = []
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name': sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                'default_image_url': sku.default_image.url
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'cart_skus': cart_skus})