import logging

from django import http
from django.shortcuts import render
from django.core.cache import cache
# Create your views here.
from django.views import View

from areas.models import Area
from meiduo_mall.utils.response_code import RETCODE


logger = logging.getLogger('django')


class AreasView(View):

    def get(self,request):

        area_id = request.GET.get('area_id')

        if not area_id:
            p_li = cache.get('province_list')

            if not p_li:
                try:
                    pm_li = Area.objects.filter(parent__isnull=True)

                    p_li = []
                    for pm in pm_li:
                        p_dict = {
                            'id':pm.pk,
                            'name':pm.name
                        }
                        p_li.append(p_dict)

                    cache.set('province_list', p_li, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '省份数据错误'})

            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': p_li})
        else:
            sub_dict = cache.get('sub_area_' + area_id)

            if not sub_dict:
                try:
                    p_obj = Area.objects.get(pk=area_id)
                    sm_li = p_obj.subs.all()

                    s_li = []
                    for sm in sm_li:
                        sm_dict = {
                            'id':sm.id,
                            'name':sm.name
                        }
                        s_li.append(sm_dict)

                    sub_dict = {
                        'id':p_obj.id,
                        'name':p_obj.name,
                        'subs':s_li
                    }

                    cache.set('sub_area_' + area_id, sub_dict, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '城市或区数据错误'})

            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_dict})