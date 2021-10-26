import json

from django import http
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
import re
import logging

# Create your views here.
from django_redis import get_redis_connection

from carts.utils import merge_cart_cookie_to_redis
from celery_tasks.email.tasks import send_verify_email
from users import constants
from users.models import User, Address
from users.utils import generate_verify_email_url, check_verify_email_token
from utils.response_code import RETCODE
from meiduo_mall.utils.views import LoginRequiredJSONMixin
from goods.models import SKU


logger = logging.getLogger('django')


class RegisterView(View):

    def get(self,request):

        return render(request,'register.html')

    def post(self,request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden('缺少必传参数')

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入5-20个字符的用户名')

        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return http.HttpResponseForbidden('请输入8-20位的密码')

        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')

        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')

        redis_conn  = get_redis_connection('verify_code')
        sms_code_server = redis_conn.get('sms_%s' % mobile).decode()
        try:
            redis_conn.delete('sms_%s' % mobile)
        except Exception as e:
            logger.error(e)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': '无效的短信验证码'})
        if sms_code_client != sms_code_server:
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})

        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})

        login(request,user)
        response = redirect(reverse('contents:index'))
        response.set_cookie('username',user.username,max_age=3600 * 24 * 15)

        return response


class UsernameCountView(View):

    def get(self,request,username):

        count = User.objects.filter(username=username).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class MobileCountView(View):

    def get(self,request,mobile):

        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'count': count})


class LoginView(View):

    def get(self,request):

        return render(request,'login.html')

    def post(self,request):

        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
        next_url = request.GET.get('next')

        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden('请输入正确的用户名或手机号')

        user = authenticate(username=username,password=password)
        if not user:
            return render(request, 'login.html', {'account_errmsg': '用户名或密码错误'})
        login(request, user)

        if remembered != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(3600 * 24 *15)

        if next_url:
            response = redirect(next_url)
        else:
            response = redirect(reverse('contents:index'))

        response = merge_cart_cookie_to_redis(request, user, response)

        response.set_cookie('username',user.username,max_age=3600 * 24 * 15)

        return response


class LogoutView(View):

    def get(self,request):

        logout(request)

        response = redirect(reverse('contents:index'))
        response.delete_cookie('username')

        return response


class UserInfoView(LoginRequiredMixin,View):

    def get(self, request):
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html',context=context)


class EmailView(LoginRequiredJSONMixin,View):

    def put(self,request):
        email = json.loads(request.body.decode()).get('email')

        if not email:
            return http.HttpResponseForbidden('缺少email参数')
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')

        try:
            User.objects.filter(pk=request.user.pk).update(email=email)
            # request.user.email = email
            # request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})

        verify_url = generate_verify_email_url(request.user)
        print(verify_url)
        # send_verify_email.delay(email, verify_url)

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加邮箱成功'})


class VerifyEmailView(View):

    def get(self,request):
        token = request.GET.get("token")

        if not token:
            return http.HttpResponseBadRequest('缺少token')

        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseForbidden('无效的token')

        try:
            User.objects.filter(pk=user.id).update(email_active=True)
            # user.email_active = True
            # user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮件失败')

        return redirect(reverse('users:info'))


class AddressView(LoginRequiredMixin,View):

    def get(self,request):

        adds = Address.objects.filter(user=request.user,is_deleted=False)
        if not adds:
            context = {
                'default_address_id': 0,
                'addresses': [],
            }
        else:
            add_li = []
            for add in adds:
                add_dict = {
                    "id": add.id,
                    "title": add.title,
                    "receiver": add.receiver,
                    "province": add.province.name,
                    "city": add.city.name,
                    "district": add.district.name,
                    "place": add.place,
                    "mobile": add.mobile,
                    "tel": add.tel,
                    "email": add.email
                }
                add_li.append(add_dict)

            context = {
                'default_address_id': request.user.default_address_id,
                'addresses': add_li,
            }

        return render(request,'user_center_site.html',context)


class CreateAddressView(LoginRequiredJSONMixin,View):

    def post(self,request):

        count = request.user.addresses.count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return http.JsonResponse({'code': RETCODE.THROTTLINGERR, 'errmsg': '地址数量超过上限'})

        data_dict = json.loads(request.body.decode())
        receiver = data_dict.get('receiver')
        province_id = data_dict.get('province_id')
        city_id = data_dict.get('city_id')
        district_id = data_dict.get('district_id')
        place = data_dict.get('place')
        mobile = data_dict.get('mobile')
        tel = data_dict.get('tel')
        email = data_dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        try:
            address = Address.objects.create(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
            if not request.user.default_address:
                User.objects.filter(pk=request.user.id).update(default_address=address)
                # request.user.default_address = address
                # request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '新增地址失败'})

        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '新增地址成功', 'address':address_dict})


class UpdateDestroyAddressView(LoginRequiredJSONMixin,View):

    def put(self,request,address_id):

        json_dict = json.loads(request.body.decode())
        receiver = json_dict.get('receiver')
        province_id = json_dict.get('province_id')
        city_id = json_dict.get('city_id')
        district_id = json_dict.get('district_id')
        place = json_dict.get('place')
        mobile = json_dict.get('mobile')
        tel = json_dict.get('tel')
        email = json_dict.get('email')

        if not all([receiver, province_id, city_id, district_id, place, mobile]):
            return http.HttpResponseForbidden('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('参数mobile有误')
        if tel:
            if not re.match(r'^(0[0-9]{2,3}-)?([2-9][0-9]{6,7})+(-[0-9]{1,4})?$', tel):
                return http.HttpResponseForbidden('参数tel有误')
        if email:
            if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
                return http.HttpResponseForbidden('参数email有误')

        try:
            Address.objects.filter(id=address_id).update(
                user=request.user,
                title=receiver,
                receiver=receiver,
                province_id=province_id,
                city_id=city_id,
                district_id=district_id,
                place=place,
                mobile=mobile,
                tel=tel,
                email=email
            )
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '更新地址失败'})

        address = Address.objects.get(id=address_id)
        address_dict = {
            "id": address.id,
            "title": address.title,
            "receiver": address.receiver,
            "province": address.province.name,
            "city": address.city.name,
            "district": address.district.name,
            "place": address.place,
            "mobile": address.mobile,
            "tel": address.tel,
            "email": address.email
        }

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '更新地址成功', 'address': address_dict})

    def delete(self,request,address_id):
        try:
            Address.objects.filter(pk=address_id).update(is_deleted = True)
            # address = Address.objects.get(id=address_id)
            # address.is_deleted = True
            # address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '删除地址失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除地址成功'})


class DefaultAddressView(LoginRequiredJSONMixin,View):

    def put(self,request,address_id):

        try:
            addr = Address.objects.get(pk=address_id)
            User.objects.filter(pk=request.user.id).update(default_address=addr)
            # request.user.default_address = addr
            # request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置默认地址失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置默认地址成功'})


class UpdateTitleAddressView(LoginRequiredJSONMixin,View):

    def put(self,request,address_id):

        json_dict = json.loads(request.body.decode())
        title = json_dict.get('title')

        try:
            Address.objects.filter(pk=address_id).update(title=title)
            # address = Address.objects.get(id=address_id)
            # address.title = title
            # address.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '设置地址标题失败'})

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '设置地址标题成功'})


class ChangePasswordView(LoginRequiredMixin,View):

    def get(self,request):

        return render(request,'user_center_pass.html')

    def post(self,request):

        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        new_password2 = request.POST.get('new_password2')
        print(new_password)

        if not all([old_password, new_password, new_password2]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            request.user.check_password(old_password)
        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'origin_pwd_errmsg': '原始密码错误'})
        if not re.match(r'^[0-9A-Za-z]{8,20}$', new_password):
            return http.HttpResponseForbidden('密码最少8位，最长20位')
        if new_password != new_password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')

        try:
            request.user.set_password(new_password)
            request.user.save()
        except Exception as e:
            logger.error(e)
            return render(request, 'user_center_pass.html', {'change_pwd_errmsg': '修改密码失败'})

        logout(request)
        response = redirect(reverse('users:login'))
        response.delete_cookie('username')

        return response


class UserBrowseHistory(LoginRequiredJSONMixin,View):

    def get(self,request):

        redis_conn = get_redis_connection('history')
        sku_ids = redis_conn.lrange('history_%s' % request.user.id, 0, -1)

        skus = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(pk=sku_id)
            skus.append({
                'id': sku.id,
                'name': sku.name,
                'default_image_url': sku.default_image.url,
                'price': sku.price
            })

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'skus': skus})

    def post(self,request):

        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')

        try:
            SKU.objects.get(id=sku_id)
        except Exception as e:
            return http.HttpResponseForbidden('sku不存在')

        redis_conn = get_redis_connection('history')
        pl = redis_conn.pipeline()
        user_id = request.user.id
        pl.lrem('history_%s' % user_id, 0, sku_id)
        pl.lpush('history_%s' % user_id, sku_id)
        pl.ltrim('history_%s' % user_id, 0, 4)
        pl.execute()

        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})