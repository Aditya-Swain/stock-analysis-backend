

from django.db import models
from django.contrib.auth.models import User

class Trade(models.Model):
    ACTION_CHOICES = (
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trades')
    stock_symbol = models.CharField(max_length=10)
    action = models.CharField(max_length=4, choices=ACTION_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    price_per_share = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.stock_symbol} - {self.action} ({self.quantity})"

    class Meta:
        ordering = ['-date']

