from django.contrib.auth.backends import ModelBackend
import re

from users import constants
from .models import User
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import BadData
from django.conf import settings



def get_user_by_account(account):
    try:
        if re.match('^1[3-9]\d{9}$', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class UsernameMobileAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        user = get_user_by_account(username)
        if user and user.check_password(password):
            return user


def generate_verify_email_url(user):

    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    data = {'user_id': user.id, 'email': user.email}
    token = serializer.dumps(data).decode()
    verify_url = settings.EMAIL_VERIFY_URL + '?token=' + token

    return verify_url


def check_verify_email_token(token):

    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.VERIFY_EMAIL_TOKEN_EXPIRES)

    try:
        token_dict = serializer.loads(token)
        # print("*"*20,token_dict)
    except BadData:
        return None

    user_id = token_dict.get('user_id')
    email = token_dict.get('email')
    # print("*"*20,user_id)
    try:
        user = User.objects.get(pk=user_id,email=email)
    except Exception:
        return None

    return user