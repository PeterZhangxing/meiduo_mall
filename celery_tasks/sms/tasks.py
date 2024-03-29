from celery_tasks.sms.yuntongxun.ccp_sms import CCP
from celery_tasks.sms import constants
from celery_tasks.main import celery_app

@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, sms_code):
    send_ret = CCP().send_template_sms(
        mobile,
        [sms_code, constants.SMS_CODE_REDIS_EXPIRES // 60],
        constants.SEND_SMS_TEMPLATE_ID
    )
    return send_ret

# 启动celery进程
# celery -A celery_tasks.main worker -l info -P eventlet -c 1000 用协程允许任务
# celery -A celery_tasks.main worker -l info 用线程允许任务