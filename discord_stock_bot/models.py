from django.db import models

# Create your models here.
class Users(models.Model):
    discord_id = models.CharField(max_length = 30)
    stock_list = models.CharField(max_length = 500)