from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    mobile=models.CharField(max_length=20,unique=True,blank=True)
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True)
    user_desc = models.TextField(max_length=500, blank=True)
    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table='tb_user'#修改表名
        verbose_name='用户信息'#admin后台展示
        verbose_name_plural=verbose_name

    def __str__(self):
        return self.mobile
