from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tx_ref = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(default=timezone.now)
    chapa_reference = models.CharField(max_length=100, blank=True, null=True)
    # Track if this payment has been applied to user's subscription
    subscription_updated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} ETB - {self.payment_date.strftime('%Y-%m-%d')}"