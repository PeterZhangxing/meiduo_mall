from alipay import AliPay
from django.shortcuts import render
from django.views import View
# Create your views here.
from orders.models import *
from django import http
from django.conf import settings
import os
from meiduo_mall.utils.response_code import RETCODE
from payment.models import *
import logging


logger = logging.getLogger("django")


class PaymentView(View):

    def get(self,request, order_id):
        user = request.user
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('订单信息错误')

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), *["keys","app_private_key.pem"]),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),*["keys","alipay_public_key.pem"]),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )

        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_amount),
            subject="美多商城%s" % order_id,
            return_url=settings.ALIPAY_RETURN_URL,
        )

        alipay_url = settings.ALIPAY_URL + "?" + order_string # 用户支付页面地址

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'alipay_url': alipay_url})


class PaymentStatusView(View):

    def get(self,request):
        query_dict = request.GET
        data = query_dict.dict()

        signature = data.pop('sign')

        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              *["keys", "app_private_key.pem"]),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                *["keys", "alipay_public_key.pem"]),
            sign_type="RSA2",
            debug=settings.ALIPAY_DEBUG
        )

        success = alipay.verify(data, signature)
        if success:
            order_id = data.get('out_trade_no')
            trade_id = data.get('trade_no')

            try:
                Payment.objects.create(order_id=order_id,trade_id=trade_id)
                OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM['UNPAID']).update(
                    status=OrderInfo.ORDER_STATUS_ENUM["UNCOMMENT"])
            except Exception as e:
                logger.error(e)
                return http.HttpResponseForbidden('支付成功，支付信息保存失败')

            context = {
                'trade_id': trade_id
            }
            return render(request, 'pay_success.html', context)
        else:
            return http.HttpResponseForbidden('非法请求')