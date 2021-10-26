import base64
import pickle

from django_redis import get_redis_connection


def merge_cart_cookie_to_redis(request, user, response):
    cookie_cart_str = request.COOKIES.get('carts')

    if not cookie_cart_str:
        return response

    cookie_cart_dict = pickle.loads(base64.b64decode(cookie_cart_str.encode()))

    new_cart_dict = {}
    new_cart_selected_add = []
    new_cart_selected_remove = []
    for sku_id, cookie_dict in cookie_cart_dict.items():
        new_cart_dict[sku_id] = cookie_dict['count']
        if cookie_dict['selected']:
            new_cart_selected_add.append(sku_id)
        else:
            new_cart_selected_remove.append(sku_id)

    redis_conn = get_redis_connection('carts')
    pl = redis_conn.pipeline()
    pl.hmset('carts_%s' % user.id, new_cart_dict)
    if new_cart_selected_add:
        pl.sadd('selected_%s' % user.id, *new_cart_selected_add)
    if new_cart_selected_remove:
        pl.srem('selected_%s' % user.id, *new_cart_selected_remove)
    pl.execute()

    response.delete_cookie('carts')
    return response