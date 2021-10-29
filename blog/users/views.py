from random import random, randint

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse

from users.models import User

# Create your views here.
from django.views import View
from django.http import JsonResponse,HttpResponse,HttpResponseBadRequest
from django_redis import get_redis_connection
import re
from django.contrib.auth import logout


class RegisterView(View):
    def get(self,request):
        return render(request,'register.html')
    def post(self,request):
        mobile=request.POST.get("mobile")
        password = request.POST.get("password")
        password2 = request.POST.get("password2")
        sms_code = request.POST.get("sms_code")
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')
        if not re.match(r'^[0-9A-Za-z]{4,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
        if not all([mobile,password,password2,sms_code]):
            return JsonResponse({"code":400,"errmsg":"参数缺失"})
        if password!=password2:
            return JsonResponse({"code":400,"errmsg":"两次密码输入不一致"})
        redis_cli=get_redis_connection("default")
        sms_code_server=redis_cli.get("sms%s"%mobile)
        if sms_code_server is None:
            return JsonResponse({"code":400,"errmsg":"短信验证码过期"})
        if not sms_code_server.decode()==sms_code:
            return JsonResponse({"code":400,"errmsg":"验证玛输入错误"})
        try:
            user=User.objects.create_user(username=mobile,password=password,mobile=mobile)
            user.save()
        except Exception:
            return HttpResponseBadRequest('注册失败')
        from django.shortcuts import redirect
        from django.urls import reverse
        from django.contrib.auth import login
        login(request,user)
        # 响应注册结果
        response=redirect(reverse('home:index'))
        response.set_cookie('is_login',True)
        response.set_cookie('username',user.username,max_age=30*24*3600)
        return response
        pass

class ImageCodeView(View):

    def get(self,request):

        uuid=request.GET.get("uuid")
        if uuid is None:
            return HttpResponseBadRequest("请求参数错误")
        from libs.captcha.captcha.captcha import Captcha
        text,image=Captcha().generate_captcha()
        redis_cli=get_redis_connection("default")
        redis_cli.setex("img:%s"%uuid,300,text)
        return HttpResponse(image,content_type='image/jpeg')

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
        if not re.match(r'^1[3-9]\d{9}$',mobile):
            return HttpResponseBadRequest("手机号格式不正确")
        sms_code=('%06d')%randint(0,999999)
        pl=redis_cli.pipeline()
        pl.setex("sms%s"%mobile,300,sms_code)
        pl.setex("send_flag%s"%mobile,60,1)
        pl.execute()
        from libs.yuntongxun.sms import CCP
        CCP().send_template_sms(mobile,[sms_code,5],1)
        return JsonResponse({"code":0,"errmsg":"发送成功"})

from django.contrib.auth import authenticate, login


class LoginView(View):

    def get(self,request):
        return render(request,'login.html')

    def post(self,request):
        mobile=request.POST.get("mobile")
        password = request.POST.get("password")
        remember = request.POST.get("remember")
        if not all([mobile, password]):
            return HttpResponseBadRequest('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('密码最少8位，最长20位')
        # try:
        #     user=User.objects.filter(username=mobile)
        # except User.DoesNotExist:
        #     return HttpResponseBadRequest('用户不存在')
        user=authenticate(mobile=mobile,password=password)
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')
        login(request,user)

        next_page=request.GET.get("next")
        if next_page:
            response=redirect(next_page)
        else:
            response=redirect(reverse('home:index'))
        if remember:
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)
        else:
            request.session.set_expiry(0)
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)
        return response
        pass
class LogoutView(View):
    def get(self,request):
        logout(request)
        response=redirect(reverse('users:login'))
        response.delete_cookie('is_login')
        # response.delete_cookie('username')
        return response

        pass

class ForgetPasswordView(View):

    def get(self, request):
        return render(request,'forget_password.html')


    def post(self, request):
        mobile=request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        sms_code = request.POST.get('sms_code')
        if not all([mobile,password,password2,sms_code]):
            return HttpResponseBadRequest("参数不全")
        if not all([mobile, password, password2, sms_code]):
            return HttpResponseBadRequest('缺少必传参数')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('请输入正确的手机号码')
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位的密码')
        if password != password2:
            return HttpResponseBadRequest('两次输入的密码不一致')
        redis_cli=get_redis_connection('default')
        sms_code_server=redis_cli.get("sms%s"%mobile)
        if not sms_code_server.decode().lower()==sms_code.lower():
            return HttpResponseBadRequest("短信验证码输入不正确")
        try:
            user=User.objects.get(username=mobile)
        except User.DoesNotExist:
            try:
                user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
            except Exception:
                return HttpResponseBadRequest("修改失败 请稍后再试")
        else:
            user.set_password(password)
            user.save()
        return redirect(reverse('users:login'))

from django.views import View

class UserCenterView(LoginRequiredMixin,View):
    def get(self,request):
        user=request.user
        context={
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request,'center.html',context=context)
        pass
    def post(self,request):
        user=request.user
        avatar=request.FILES.get('avatar')
        username=request.POST.get("username",user.username)
        user_desc=request.POST.get("desc",user.user_desc)
        try:
            user.username=username
            user.user_desc=user_desc
            if avatar:

                user.avatar=avatar
            user.save()
        except Exception as e:
            return HttpResponseBadRequest("更新失败")
        response=redirect(reverse('users:center'))
        response.set_cookie('username',user.username,max_age=30*24*3600)
        return response

        pass
from home.models import ArticleCategory
class WriteBlogView(LoginRequiredMixin,View):

    def get(self,request):
        categories=ArticleCategory.objects.all()
        context={
            'categories':categories
        }
        return render(request,'write_blog.html',context=context)



