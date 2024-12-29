from django.db import models

from django.db import models
from django.contrib.auth.models import User

class StockInventory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    
class Trade(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    buy_price = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    sell_price = models.DecimalField(max_digits=100, decimal_places=2, null=True, blank=True)
    extra_charges = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=100, decimal_places=2, default=0.0)
    trade_date = models.DateField(auto_now_add=True)
    is_buy = models.BooleanField(default=True)