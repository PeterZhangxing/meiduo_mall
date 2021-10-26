import datetime
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render
from django import http
from django.views import View
from django.db import transaction

# Create your views here.
from django_redis import get_redis_connection
import json

from goods.models import SKU
from orders.models import OrderInfo, OrderGoods
from users import constants
from users.models import Address
from utils.response_code import RETCODE
from utils.views import LoginRequiredJSONMixin
import logging

logger = logging.getLogger('django')


class OrderSettlementView(LoginRequiredMixin,View):

    def get(self, request):

        user = request.user
        try:
            addresses = Address.objects.filter(user=request.user, is_deleted=False)
        except Exception as e:
            addresses = None

        redis_conn = get_redis_connection('carts')
        redis_cart = redis_conn.hgetall('carts_%s' % user.id)
        cart_selected = redis_conn.smembers('selected_%s' % user.id)
        cart = {}
        for cart_id in cart_selected:
            cart[int(cart_id)] = int(redis_cart[cart_id])

        total_count = 0
        total_amount = Decimal(0.00)
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart[sku.id]
            sku.amount = sku.count * sku.price

            total_count += sku.count
            total_amount += sku.count * sku.price

        freight = Decimal('10.00')

        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount': total_amount + freight
        }

        return render(request, 'place_order.html',context=context)


class OrderCommitView(LoginRequiredJSONMixin,View):

    def post(self,request):

        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')

        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')

        try:
            address = Address.objects.get(id=address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id错误')

        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                user = request.user
                order_id = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + "%09d"%user.id
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )
                redis_conn = get_redis_connection('carts')
                redis_cart = redis_conn.hgetall('carts_%s' % user.id)
                selected = redis_conn.smembers('selected_%s' % user.id)
                carts = {}
                for sku_id in selected:
                    carts[int(sku_id)] = int(redis_cart[sku_id])
                sku_ids = carts.keys()

                for sku_id in sku_ids:
                    while True:
                        sku = SKU.objects.get(id=sku_id)

                        origin_stock = sku.stock
                        origin_sales = sku.sales

                        sku_count = carts[sku.id]
                        if sku_count > origin_stock:
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

                        # # SKU减少库存，增加销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()

                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count
                        res = SKU.objects.filter(id=sku_id,stock=origin_stock).update(stock=new_stock, sales=new_sales)
                        if not res:
                            continue

                        sku.spu.sales += sku_count
                        sku.spu.save()

                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price,
                        )

                        order.total_count += sku_count
                        order.total_amount += (sku_count * sku.price)

                        break

                order.total_amount += order.freight
                order.save()
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '下单失败'})

            transaction.savepoint_commit(save_id)

        pl = redis_conn.pipeline()
        pl.hdel('carts_%s' % user.id, *selected)
        pl.srem('selected_%s' % user.id, *selected)
        pl.execute()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单成功', 'order_id': order.order_id})


class OrderSuccessView(LoginRequiredMixin,View):

    def get(self,request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'pay_method': pay_method
        }

        return render(request, 'order_success.html', context)


class UserOrderInfoView(LoginRequiredMixin,View):

    def get(self,request,page_num):

        user = request.user
        orders = user.orderinfo_set.order_by("-create_time")
        for order in orders:
            order.status_name = order.get_status_display()
            order.pay_method_name = order.get_pay_method_display()

            order.sku_list = []
            order_goods = order.skus.all()
            for order_good in order_goods:
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.price * sku.count
                order.sku_list.append(sku)

        try:
            page_num = int(page_num)
            paginator = Paginator(orders, constants.ORDERS_LIST_LIMIT)
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages
        except Exception as e:
            logger.error(e)
            return http.HttpResponseNotFound('订单不存在')

        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }

        return render(request,'user_center_order.html',context=context)


class OrderCommentView(LoginRequiredMixin,View):

    def get(self,request):

        order_id = request.GET.get('order_id')
        try:
            OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseNotFound('订单不存在')
        try:
            uncomment_goods = OrderGoods.objects.filter(order_id=order_id, is_commented=False)
        except Exception:
            return http.HttpResponseServerError('订单商品信息出错')

        uncomment_goods_list = []
        for goods in uncomment_goods:
            uncomment_goods_list.append({
                'order_id': goods.order.order_id,
                'sku_id': goods.sku.id,
                'name': goods.sku.name,
                'price': str(goods.price),
                'default_image_url': goods.sku.default_image.url,
                'comment': goods.comment,
                'score': goods.score,
                'is_anonymous': str(goods.is_anonymous),
            })

        context = {
            'uncomment_goods_list': uncomment_goods_list
        }
        return render(request, 'goods_judge.html', context)

    def post(self,request):

        json_dict = json.loads(request.body.decode())
        order_id = json_dict.get('order_id')
        sku_id = json_dict.get('sku_id')
        score = json_dict.get('score')
        comment = json_dict.get('comment')
        is_anonymous = json_dict.get('is_anonymous')

        if not all([order_id, sku_id, score, comment]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            OrderInfo.objects.filter(order_id=order_id, user=request.user,
                                     status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except Exception:
            return http.HttpResponseForbidden('参数order_id错误')
        try:
            sku = SKU.objects.get(id=sku_id)
        except Exception:
            return http.HttpResponseForbidden('参数sku_id错误')
        if is_anonymous:
            if not isinstance(is_anonymous, bool):
                return http.HttpResponseForbidden('参数is_anonymous错误')

        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                OrderGoods.objects.filter(order_id=order_id, sku_id=sku_id, is_commented=False).update(
                    comment=comment,
                    score=score,
                    is_anonymous=is_anonymous,
                    is_commented=True
                )

                sku.comments += 1
                sku.save()

                sku.spu.comments += 1
                sku.spu.save()

                if OrderGoods.objects.filter(order_id=order_id, is_commented=False).count() == 0:
                    OrderInfo.objects.filter(order_id=order_id).update(status=OrderInfo.ORDER_STATUS_ENUM['FINISHED'])
            except Exception as e:
                logger.error(e)
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '评价失败'})

            transaction.savepoint_commit(save_id)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '评价成功'})


class GoodsCommentView(View):

    def get(self,request,sku_id):

        order_goods_list = OrderGoods.objects.filter(sku_id=sku_id, is_commented=True).order_by('-create_time')[:30]

        comment_list = []
        for order_goods in order_goods_list:
            username = order_goods.order.user.username if order_goods.is_anonymous == False else order_goods.order.user.username[0] + '***' + order_goods.order.user.username[-1]
            comment_list.append({
                'username': username,
                'comment': order_goods.comment,
                'score': order_goods.score,
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'comment_list': comment_list})