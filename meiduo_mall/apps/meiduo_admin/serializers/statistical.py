from rest_framework.serializers import ModelSerializer
from rest_framework import serializers

from goods.models import GoodsVisitCount


class GoodsSerializer(ModelSerializer):

    category = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = GoodsVisitCount
        fields = ('count', 'category')