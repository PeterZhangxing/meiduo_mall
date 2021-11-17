from datetime import date,timedelta

from django.shortcuts import render
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

# Create your views here.
from users.models import User
from goods.models import GoodsVisitCount
from meiduo_admin.serializers.statistical import GoodsSerializer


class UserTotalCountView(APIView):

    permission_classes = [IsAdminUser]

    def get(self,request):
        now_date = date.today()
        count = User.objects.all().count()
        return Response({
            'count': count,
            'date': now_date
        })


class UserDayCountView(APIView):

    permission_classes = [IsAdminUser]

    def get(self,request):
        now_date = date.today()
        count = User.objects.filter(date_joined__gte=now_date).count()
        return Response({
            "count": count,
            "date": now_date
        })


class UserActiveCountView(APIView):

    permission_classes = [IsAdminUser]

    def get(self,request):
        now_date = date.today()
        count = User.objects.filter(last_login__gte=now_date).count()
        return Response({
            "count": count,
            "date": now_date
        })


class UserOrderCountView(APIView):

    permission_classes = [IsAdminUser]

    def get(self,request):
        now_date = date.today()
        count = User.objects.filter(orderinfo_set__create_time__gte=now_date).count()
        return Response({
            "count": count,
            "date": now_date
        })


class UserMonthCountView(APIView):

    permission_classes = [IsAdminUser]

    def get(self,request):
        now_date = date.today()
        start_date = now_date - timedelta(29)
        date_list = []

        for i in range(30):
            index_date = start_date + timedelta(days=i)
            next_date = start_date + timedelta(days=i + 1)
            count = User.objects.filter(date_joined__gte=index_date,date_joined__lt=next_date).count()
            date_list.append({"count": count,"date": index_date})

        return Response(date_list)


class GoodsDayView(APIView):

    permission_classes = [IsAdminUser]

    def get(self, request):
        now_date = date.today()
        data = GoodsVisitCount.objects.filter(date=now_date)
        ser = GoodsSerializer(instance=data,many=True)
        return Response(ser.data)