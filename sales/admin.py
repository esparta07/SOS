from django.contrib import admin

from .models import Client, Bill,Action,DailyBalance,UserBalance,CompanyBalance,CreditEntry

from .models import Client, Bill,Action,DailyBalance,UserBalance,CompanyBalance,LogEntry

from import_export.admin import ImportExportActionModelAdmin

@admin.register(Client)
class ClientData(ImportExportActionModelAdmin):
    list_display = ['short_name', 'account_name', 'balance', 'phone_number', 'collector']
    list_editable = ['collector']  
    search_fields = ['short_name', 'account_name', 'collector__full_name']

@admin.register(Bill)
class BillData(ImportExportActionModelAdmin):
    list_display = ['account_name','bill_no', 'inv_amount', 'due_date',]
    search_fields = ['account_name__account_name', 'bill_no'] 
   

@admin.register(Action)
class ActionData(ImportExportActionModelAdmin):
    list_display = ['action_date','account_name', 'action_type','type','completed','subtype','followup_date']
    search_fields = ['type']
    list_editable = ['completed','type','action_type']  
    
@admin.register(DailyBalance)
class BalanceData(ImportExportActionModelAdmin):
    list_display = ['collector', 'total_balance', 'date',]
    
@admin.register(UserBalance)
class UserBalanceData(ImportExportActionModelAdmin):
    list_display = ['user', 'collector_balance', 'last_updated',]
    
@admin.register(CompanyBalance)
class CompanyBalanceData(ImportExportActionModelAdmin):
    list_display = ['total_balance', 'date',]

@admin.register(CreditEntry)
class CreditEntryAdmin(ImportExportActionModelAdmin):
    list_display=['account_name','amount','collector','date','settle']
    list_editable=['settle',]    
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['message', 'is_error', 'timestamp']  
    search_fields = ['message']  
    list_filter = ['is_error'] 
