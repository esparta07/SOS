from django.db import models
from account.models import User
from django.utils import timezone
import datetime
from django.core.exceptions import ValidationError

class Client(models.Model):
    short_name = models.CharField(max_length=255, unique=True , null=True, blank=True)
    account_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    pan_number = models.CharField(max_length=20, null=True, blank=True)
    balance = models.DecimalField(
        max_digits=10,  
        decimal_places=2,
        null=True,
        blank=True,
        default=0
    )

    phone_number = models.CharField(max_length=15, null=True, blank=True)
    email=models.EmailField(null=True,blank=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    
    GROUP_CHOICES = (
    ('Advanced', 'Advanced'),
    ('Normal', 'Normal'),
    )

    group = models.CharField(max_length=100, choices=GROUP_CHOICES, null=True, blank=True, default='Normal')
    collector = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': User.USER}, related_name='clients', null=True, blank=True)
    guarantee_world_insurer = models.CharField(max_length=255, null=True, blank=True)
    credit_limit = models.DecimalField(max_digits=15,default=0, decimal_places=2, null=True, blank=True)
    overdue120=models.FloatField(null=True, blank=True,default=0)
    grant_period=models.FloatField(default=0)
    pause = models.BooleanField(default=False)


    def __str__(self):
        if self.account_name:
            return self.account_name
        elif self.short_name:
            return self.short_name
        else:
            return f"Client {self.pk}"  
        


class Bill(models.Model):
    bill_no = models.CharField(max_length=40, blank=True)
    due_date = models.DateField(null=True, blank=True)
    inv_amount = models.FloatField(null=True, blank=True)  
    account_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    

    @property
    def cycle(self):
        if self.due_date:
            days_diff = (timezone.now().date() - self.due_date).days
            if days_diff <= 15:
                return 1
            elif 16 <= days_diff <= 30:
                return 2
            elif 31 <= days_diff <= 45:
                return 3
            elif 46 <= days_diff <= 60:
                return 4
            elif 61 <= days_diff <= 75:
                return 5
            elif 76 <= days_diff <= 90:
                return 6
            elif 91 <= days_diff <= 105:
                return 7
            elif 106 <= days_diff <= 120:
                return 8
            else:
                return 9
        else:
            return None

    def __str__(self):
        if self.bill_no:
            return self.bill_no
        else:
            account_name = self.account_name.account_name 
            return account_name or f"Bill {self.pk}"
    
class Action(models.Model):
    action_date = models.DateTimeField(default=datetime.datetime.combine(datetime.date.today(), datetime.time(9, 30)))
    TYPE_CHOICES = (
        ('auto', 'auto'),
        ('manual', 'manual'),
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    SMS_CHOICES = (
        ('Reminder', 'Reminder'),
        ('Gentle', 'Gentle'),
        ('Strong', 'Strong'),
        ('Final', 'Final'),
    )
    ACTION_CHOICES = (
        ('SMS', 'SMS'),
        ('Email', 'Email'),
        ('Call', 'Call'),
    )
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    action_amount = models.FloatField()
    account_name = models.ForeignKey(Client, on_delete=models.CASCADE)
    subtype = models.CharField(max_length=20, choices=SMS_CHOICES, null=True, blank=True)
    followup_date = models.DateField(blank=True, default=None, null=True)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True,)

    def __str__(self):
        return f"{self.action_type} on {self.action_date} "

       
class DailyBalance(models.Model):
    collector = models.ForeignKey(User, on_delete=models.CASCADE)
    total_balance = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.collector.full_name} - {self.date}"

    class Meta:
        unique_together = ['collector', 'date']
    


class UserBalance(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='balance', limit_choices_to={'role': User.USER})
    collector_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    last_updated = models.DateTimeField(default=timezone.now)

    def clean(self):
        # Ensure that the associated user has the role USER
        if self.user.role != User.USER:
            raise ValidationError("The associated user must have the role USER.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name}'s Balance"

    class Meta:
        verbose_name_plural = 'User Balances'

    

class CompanyBalance(models.Model):
    total_balance = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Balance on {self.date}"

    class Meta:
        unique_together = ['date']
        
class LogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    is_error = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.timestamp}: {'Error' if self.is_error else 'Success'} - {self.message}"