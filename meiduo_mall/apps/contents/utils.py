from goods.models import *
from collections import OrderedDict


def get_categories():
    categories = OrderedDict()

    channels = GoodsChannel.objects.order_by('group_id','sequence')

    # "channels": [
    #     {"id": 1, "name": "手机", "url": "http://shouji.jd.com/"},
    #     {"id": 2, "name": "相机", "url": "http://www.itcast.cn/"}
    # ],
    for channel in channels:
        if channel.group_id not in categories:
            categories[channel.group_id] = {
                "channels": [],
                'sub_cats': []
            }

        categories[channel.group_id]["channels"].append({
            "id": channel.category_id,
            "name": channel.category.name,
            "url": channel.url
        })

        # {
        #     "id": 38,
        #     "name": "手机通讯",
        #     "sub_cats": [
        #         {"id": 115, "name": "手机"},
        #         {"id": 116, "name": "游戏手机"}
        #     ]
        # },
        for sub_cat in channel.category.subs.all():
            categories[channel.group_id]["sub_cats"].append(sub_cat)
            sub_cat.sub_cats = []

            for trd_cat in sub_cat.subs.all():
                sub_cat.sub_cats.append(trd_cat)

    return categories