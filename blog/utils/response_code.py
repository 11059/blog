from random import random, randint

from django.shortcuts import render

# Create your views here.
from django.views import View
from django.http import JsonResponse,HttpResponse,HttpResponseBadRequest
from django_redis import get_redis_connection
import re

class SmsCodeView(View):

    def get(self,request):
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        mobile=request.GET.get('mobile')
        if not all([image_code_client,uuid,mobile]):
            return HttpResponseBadRequest("参数不全")
        redis_cli=get_redis_connection("default")
        image_code_server=redis_cli.get("img:%s"%uuid)
        send_flag=redis_cli.get("send_flag%s"%mobile)
        if send_flag is not None:
            return HttpResponseBadRequest("请勿反复发送验证码")
        if image_code_server is None:
            return HttpResponseBadRequest("图片验证码过期或者失效")
        if not image_code_server.decode().lower()==image_code_client.lower():
            return HttpResponseBadRequest("图片验证码不正确")
        # if not re.match(r'1[2-9]{1}\d{9}]',mobile):
        #     return HttpResponseBadRequest("手机号格式不正确")
        sms_code=('%06d')%randint(0,999999)
        pl=redis_cli.pipeline()
        pl.setex("sms%s"%mobile,300,sms_code)
        pl.setex("send_flag%s"%mobile,60,1)
        pl.execute()
        from libs.yuntongxun.sms import CCP
        CCP().send_template_sms(mobile,[sms_code,5],1)
        return JsonResponse({"code":0,"errmsg":"发送成功"})