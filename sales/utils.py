from datetime import datetime, timedelta, date
from nepali_date_converter import english_to_nepali_converter, nepali_to_english_converter
from .models import Bill, Client,Action,CompanyBalance,UserBalance,DailyBalance,LogEntry
from django.db.models import Sum, F, Max, Q
from decimal import Decimal
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from account.models import User
from django.urls import reverse
from django.contrib import messages
from django.core.exceptions import ValidationError
from decimal import Decimal
from IPython.display import FileLink
from django.utils import timezone
import pandas as pd
from django.contrib import messages
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.utils import timezone
from .models import LogEntry

def convert_date_format(input_date):
    try:
        # Check if the input_date is already a datetime object
        if isinstance(input_date, datetime):
            # If it is, return the formatted date as a string
            return input_date.strftime('%Y/%m/%d')
        
        # If not, parse the input string and format it
        input_datetime = datetime.strptime(str(input_date), '%Y-%m-%d %H:%M:%S')
        output_date = input_datetime.strftime('%Y/%m/%d')
        
        return output_date
    except ValueError:
        # If parsing fails, assume the input is already in the desired format
        return input_date

def convert_nepali_to_ad(nepali_date):
    try:
        # Parse the Nepali date into year, month, and day
        nepali_year, nepali_month, nepali_day = map(int, nepali_date.split('/'))

        # Convert Nepali date to English date
        english_date = nepali_to_english_converter(nepali_year, nepali_month, nepali_day)
        return english_date
    except Exception as e:
        print(f"Error converting Nepali date: {e}")
        return None  # or return the original value if conversion fails
    
def overdue120d(client):
    try:
        # Get the bills for the client
        client_bills = Bill.objects.filter(account_name=client)

        # Initialize total_cycles_sum
        total_cycles_sum = Decimal('0.00')

        # Iterate over the bills and calculate the total amount for cycles 7, 8, and 9
        for bill in client_bills:
            if bill.cycle in [7, 8, 9]:
                total_cycles_sum += Decimal(bill.inv_amount)

        # Round the total_cycles_sum to two decimal places
        total_cycles_sum = round(total_cycles_sum, 2)

        # Update the overdue120 field in the Client model
        client.overdue120 = total_cycles_sum
        client.save()
    except Exception as e:
        print(f"Error in calculating overdue120 for client {client}: {e}")


def update_client_balance(client):
    # Get the sum of the 'balance' field for the client's bills
    total_balance_sum = Bill.objects.filter(account_name=client).aggregate(
        total_balance_sum=Sum('inv_amount')
    )['total_balance_sum']

    # If total_balance_sum is None (meaning no bills), set it to 0
    if total_balance_sum is None:
        total_balance_sum = Decimal('0.00')
    else:
        # Round the total_balance_sum to two decimal places
        total_balance_sum = round(total_balance_sum, 2)

    # Update the balance field in the Client model
    client.balance = total_balance_sum
    client.save()
    
def create_actions_for_bill(bill):
    # Skip if due_date is None
    if bill.due_date is None:
        print(f"Invalid 'due_date' for Bill {bill.pk}. Skipping action creation.")
        return

    # Convert 'due_date' to datetime if it's a string
    if isinstance(bill.due_date, str):
        try:
            bill.due_date = datetime.strptime(bill.due_date, '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid 'due_date' format for Bill {bill.id}. Skipping action creation.")
            return

    # Add a check to delete existing incomplete actions for the client
    Action.objects.filter(account_name=bill.account_name, completed=False).delete()
    
    if not bill.account_name.pause:  
    
        grant_period_days = int(bill.account_name.grant_period)
        target_date = bill.due_date + timedelta(days=grant_period_days)

        # Create Action 1
        action1 = Action.objects.create(
            action_date=target_date,
            type='auto',
            action_type='SMS',
            action_amount=bill.account_name.balance,
            account_name=bill.account_name,
            completed=False,
            subtype='Reminder'
        )
        print(f"Action 1 Created: {action1}")

        # Create Action 2
        action2 = Action.objects.create(
            action_date=target_date + timedelta(days=1),
            type='auto',
            action_type='SMS',
            action_amount=bill.account_name.balance,
            account_name=bill.account_name,
            completed=False,
            subtype='Gentle'
        )
        print(f"Action 2 Created: {action2}")

        # Create Action 3
        action3 = Action.objects.create(
            action_date=target_date + timedelta(days=3),
            type='auto',
            action_type='SMS',
            action_amount=bill.account_name.balance,
            account_name=bill.account_name,
            completed=False,
            subtype='Strong'
        )
        print(f"Action 3 Created: {action3}")

        # Create Action 4 (if group is 'Normal')
        if bill.account_name.group == 'Normal':
            action4 = Action.objects.create(
                action_date=target_date + timedelta(days=7),
                type='auto',
                action_type='SMS',
                action_amount=bill.account_name.balance,
                account_name=bill.account_name,
                completed=False,
                subtype='Final'
            )
            print(f"Action 4 Created: {action4}")
            
def delete_actions():
    # Fetch actions that meet the deletion criteria
    actions_to_delete = Action.objects.filter(
        completed=False,
        type='auto',
        account_name__balance__lte=300
    )
    # Delete the selected actions
    actions_to_delete.delete()
    
def company_balance():
    today = date.today()

    # Calculate the total balance by summing up the balances of all clients
    total_balance = Client.objects.aggregate(total_balance=Sum('balance'))['total_balance'] or 0

    # Check if a CompanyBalance entry already exists for today
    company_balance_entry = CompanyBalance.objects.filter(date=today).first()

    if company_balance_entry:
        # Update existing CompanyBalance entry with new total_balance
        company_balance_entry.total_balance = total_balance
        company_balance_entry.save()
    else:
        # Create a new CompanyBalance entry
        CompanyBalance.objects.create(total_balance=total_balance, date=today)
        
def update_collector_balances():
    # Get all collectors (users with role USER)
    collectors = User.objects.filter(role=User.USER)

    # Calculate yesterday's date
    yesterday = datetime.now().date() - timedelta(days=1)

    for collector in collectors:
        # Get UserBalance for the collector if it exists
        user_balance = UserBalance.objects.filter(user=collector).first()

        # Check if last_updated is already set to today's date
        if user_balance and user_balance.last_updated.date() == timezone.now().date():
            # Skip if already updated for today
            continue

        # Get or create UserBalance for the collector
        if not user_balance:
            user_balance = UserBalance.objects.create(user=collector)

        # Get yesterday's DailyBalance
        yesterday_daily_balance = DailyBalance.objects.filter(
            collector=collector,
            date=yesterday
        ).values('total_balance').first()
        print(yesterday_daily_balance)

        # Get today's DailyBalance
        today_daily_balance = DailyBalance.objects.filter(
            collector=collector,
            date=datetime.now().date()
        ).values('total_balance').first()
        print(today_daily_balance)

        if yesterday_daily_balance and today_daily_balance:
            # Calculate the difference as yesterday's balance minus today's balance
            balance_difference = yesterday_daily_balance['total_balance'] - today_daily_balance['total_balance']

            if balance_difference > 0:
                # Update collector_balance by adding the positive difference
                user_balance.collector_balance += balance_difference
            else:
                # Handle the case where balance_difference is not greater than 0
                # You may want to log a message or handle it based on your requirements
                pass

            # Update the UserBalance for today with the new collector_balance
            user_balance.last_updated = timezone.now()
            user_balance.save()
            
def calculate_total_balance_for_all_collectors():
    today = date.today()

    # Get all collectors
    collectors = User.objects.filter(role=User.USER)

    for collector in collectors:
        # Calculate the total balance for all clients of the collector in the last 15 days
        total_balance = Client.objects.filter(collector=collector).aggregate(
            total_balance=Sum('balance')
        )['total_balance'] or 0

        # Check if a DailyBalance entry already exists for today and this collector
        daily_balance_entry = DailyBalance.objects.filter(collector=collector, date=today).first()

        if daily_balance_entry:
            # Update existing DailyBalance entry with new total_balance
            daily_balance_entry.total_balance = total_balance
            daily_balance_entry.save()
        else:
            # Create a new DailyBalance entry
            DailyBalance.objects.create(collector=collector, total_balance=total_balance, date=today)
            
def send_update_email(subject, message):
    
    from_email = settings.DEFAULT_FROM_EMAIL
    
    to_email = "manoj.thapa@janakitech.com"  
    
    # Create an EmailMessage with the subject, message, and sender/recipient information
    mail = EmailMessage(subject, message, from_email, to=[to_email])
    
    # Specify that the email content type is plain text
    mail.content_subtype = "plain"
    
    mail.send()
      
def bill_process(file_contents):
    success_messages = []
    error_messages = []

    try:
        # Read the uploaded Excel file
        df = pd.read_excel(file_contents)

        # Remove the first 5 rows
        df = df.iloc[6:]
        # Drop the first and fifth columns
        df = df.drop(df.columns[[0,1,5,7]], axis=1)

        # Rename the columns
        df = df.rename(columns={'Unnamed: 2': 'bill_no', 'Unnamed: 3': 'client', 'Unnamed: 4': 'inv_amount','Unnamed: 6': 'due_date', })

        # Check if the expected columns are present
        expected_columns = ['bill_no', 'client', 'inv_amount', 'due_date',]
        if not all(col in df.columns for col in expected_columns):
            error_message = 'Wrong format file. Please make sure all required columns are present.'
            error_messages.append(error_message)
            return error_messages


        # Fetch all clients at once
        account_names = df['client'].astype(str).str.strip().unique()
        clients = Client.objects.filter(account_name__in=account_names)
        print(clients)

        success_count = 0
        
        
        # Identify and delete bills not present in the Excel file
        existing_bills = Bill.objects.filter(
            account_name__in=clients.values('id')
        )
        bills_to_delete = existing_bills.exclude(bill_no__in=df['bill_no'].unique())

        if bills_to_delete.exists():
            bills_to_delete.delete() 
                
        for index, row in df.iterrows():
            try:
                account_name_value = row['client']
                client = clients.get(account_name=account_name_value)
                
                # Check if a Bill with the same data already exists
                existing_bill = Bill.objects.filter(
                    bill_no=row['bill_no'],
                    due_date=row['due_date'],
                    account_name=client,
                ).first()
                

                
                if existing_bill:
                    if existing_bill.inv_amount != row['inv_amount']:
                        # Update existing Bill with new inv_amount
                        existing_bill.inv_amount = row['inv_amount']
                        # Save the changes
                        existing_bill.save()
                        # Add success message
                        success_messages.append(f"Bill {existing_bill.bill_no} updated successfully.")
                        # Call the functions to update the client's balance and overdue120
                       
                    else:
                                                    
                        continue
                    
                    
               
                # Create a new Bill instance
                new_bill=Bill.objects.create(
                    bill_no=row['bill_no'],
                    due_date=row['due_date'],
                    inv_amount=row['inv_amount'],
                    account_name=client
                )
                success_count += 1
                
                
                # Call the function to update the client's balance after each Bill creation
                create_actions_for_bill(new_bill)
                            
            except Client.DoesNotExist:
                error_messages.append(f'Client "{account_name_value}" not found\n')
            except ValidationError as e:
                error_messages.append(f'Validation error at row {index + 2}: {e}\n')
            except Exception as e:
                error_messages.append(f'Error processing row {index + 2}: {e}') 
        
        for client in clients:
            update_client_balance(client)
            overdue120d(client)   
                    
        if success_count > 0:
            success_messages.append(f"{success_count} records successfully uploaded.")
            download_link = reverse('download_excel')
        else:
            download_link = None   
            success_messages.append("No new bills were added")

        
            
        calculate_total_balance_for_all_collectors()
        update_collector_balances()
        company_balance()
        delete_actions()  
        
        today_date = datetime.today()
        formatted_today_date = today_date.strftime('%Y-%m-%d %H:%M:%S')  

        update_subject = 'Excel File Update Notification'
        update_message = f'The Excel file has been successfully uploaded on {formatted_today_date}'

        # send_update_email(update_subject, update_message) 
        
        
        
        
    except Exception as e:
        error_messages.append(f'Error processing Excel file: {e}')
        
    for error in error_messages:
        LogEntry.objects.create(message=error, is_error=True)
    
    for success in success_messages:
        LogEntry.objects.create(message=success, is_error=False)
        
    return success_messages, error_messages


@receiver(post_save, sender=LogEntry)
def delete_old_logs(sender, instance, **kwargs):
    # Define the threshold date (15 days ago)
    threshold_date = timezone.now() - timedelta(days=15)
    
    # Delete logs older than the threshold date
    LogEntry.objects.filter(timestamp__lt=threshold_date).delete()