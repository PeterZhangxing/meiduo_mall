from django.contrib.auth.backends import ModelBackend
from users.models import User


class MeiduoModelBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if request is None:
            # 后台登录
            try:
                # is_superuser判断用户是否是超级管理员用户
                user = User.objects.get(username=username, is_superuser=True)
            except:
                user = None

            if user is not None and user.check_password(password):
                return user
        else:
            try:
                # if re.match(r'^1[3-9]\d{9}$', username):
                #     user = User.objects.get(mobile=username)
                # else:
                #     user = User.objects.get(username=username)
                user = User.objects.get(username=username)
            except:
                # 如果未查到数据，则返回None，用于后续判断
                try:
                    user = User.objects.get(mobile=username)
                except:
                    return None

            # 判断密码
            if user.check_password(password):
                return user
            else:
                return None