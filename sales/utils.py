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
    # Get the sum of all cycles for the client's bills
    total_cycles_sum = Bill.objects.filter(short_name=client).aggregate(
        total_cycles_sum=Sum('cycle9'))['total_cycles_sum'] or Decimal('0.00')

    # Round the total_cycles_sum to two decimal places
    total_cycles_sum = round(total_cycles_sum, 2)

    # Update the overdue120 field in the Client model
    client.overdue120 = total_cycles_sum
    client.save()
    
def update_client_balance(client):
    # Get the sum of the 'balance' field for the client's bills
    total_balance_sum = Bill.objects.filter(short_name=client).aggregate(
        total_balance_sum=Sum('balance')
    )['total_balance_sum'] or Decimal('0.00')

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
    Action.objects.filter(short_name=bill.short_name, completed=False).delete()
    
    if not bill.short_name.pause:  # Corrected this line
    
        grant_period_days = int(bill.short_name.grant_period)
        target_date = bill.due_date + timedelta(days=grant_period_days)

        # Create Action 1
        action1 = Action.objects.create(
            action_date=target_date,
            type='auto',
            action_type='SMS',
            action_amount=bill.short_name.balance,
            short_name=bill.short_name,
            completed=False,
            subtype='Reminder'
        )
        print(f"Action 1 Created: {action1}")

        # Create Action 2
        action2 = Action.objects.create(
            action_date=target_date + timedelta(days=1),
            type='auto',
            action_type='SMS',
            action_amount=bill.short_name.balance,
            short_name=bill.short_name,
            completed=False,
            subtype='Gentle'
        )
        print(f"Action 2 Created: {action2}")

        # Create Action 3
        action3 = Action.objects.create(
            action_date=target_date + timedelta(days=3),
            type='auto',
            action_type='SMS',
            action_amount=bill.short_name.balance,
            short_name=bill.short_name,
            completed=False,
            subtype='Strong'
        )
        print(f"Action 3 Created: {action3}")

        # Create Action 4 (if group is 'Normal')
        if bill.short_name.group == 'Normal':
            action4 = Action.objects.create(
                action_date=target_date + timedelta(days=7),
                type='auto',
                action_type='SMS',
                action_amount=bill.short_name.balance,
                short_name=bill.short_name,
                completed=False,
                subtype='Final'
            )
            print(f"Action 4 Created: {action4}")
            
def delete_actions():
    # Fetch actions that meet the deletion criteria
    actions_to_delete = Action.objects.filter(
        completed=False,
        type='auto',
        short_name__balance__lte=300
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
        excel_data = pd.read_excel(file_contents)

        # Skip the first 3 rows and set the 0th row data as column headings
        df = excel_data.iloc[3:]
        df.columns = df.iloc[0]

        # Check if the expected columns are present
        expected_columns = ['Type', 'Bill No.', 'Date', 'Due Date', 'Days', 'Inv.Amt', '0 - 15',
                            '16 - 30', '31 - 45', '46 - 60', '61 - 75', '76 - 90', '91 - 105',
                            '106 - 120', 'Over 121', 'Balance']
        if not all(col in df.columns for col in expected_columns):
            error_message = 'Wrong format file. Please make sure all required columns are present.'
            error_messages.append(error_message)
            return error_messages
        # Replace "Type" column with "1" where "Bill No." contains "Ledger =>"
        df.loc[df['Bill No.'].str.contains('Ledger =>', na=False), 'Type'] = '1'

        # Remove rows where 'Type' is '1'
        df = df[df['Type'] != '1']

        # Reset the index after filtering
        df = df.reset_index(drop=True)

        # Reset the index after removing rows and set the 0th row as the new column headings
        df = df.iloc[1:].reset_index(drop=True)
        df.fillna(0, inplace=True)

        # Define a list of values to check for in the "Type" column
        values_to_check = ['0', 'SB', 'OB']

        # Initialize a variable to store the first 'Bill No.' value
        first_bill_no = None

        # Iterate through the DataFrame
        for index, row in df.iterrows():
            type_value = str(row['Type']).strip()
            
            # Check if the 'Type' value is '0'
            if type_value == '0':
                # Reset the first_bill_no when '0' is encountered
                first_bill_no = None
            
            # If first_bill_no is not set, set it to the current 'Bill No.' value
            if first_bill_no is None:
                first_bill_no = row['Bill No.']
            
            # Assign the first_bill_no value to 'short_name'
            df.at[index, 'short_name'] = first_bill_no

        # Keep only the rows where 'Type' is 'OB' or 'SB' after the loop
        df = df[df['Type'].isin(['OB', 'SB'])]

        # Apply the lambda function to 'short_name' based on the condition
        df['short_name'] = df['short_name'].apply(lambda x: x.rsplit('-', 1)[0] if x.startswith('L') else x.split('-', 1)[0])


        # Apply the lambda function to 'short_name' to remove leading zeros
        df['short_name'] = df['short_name'].apply(lambda x: x.lstrip('0') if x[0].isdigit() else x)
        
        # Apply the convert_date_format function to 'Date' and 'Due Date' columns
        df['Date'] = df['Date'].apply(convert_date_format)

        # Copy 'Date' data to 'Due Date' column
        df['Due Date'] = df['Date']                

        # Apply the convert_nepali_to_ad function to the 'Date' column
        df['Date'] = df['Date'].apply(convert_nepali_to_ad)
        
        # Apply the convert_nepali_to_ad function to the 'Due Date' column
        df['Due Date'] = df['Due Date'].apply(convert_nepali_to_ad)
        
        #Delete the Date column
        df.drop(columns=['Date'], inplace=True)

        #Delete the Date column
        df.drop(columns=['Days'], inplace=True)

        # Define the new column names
        new_column_names = [
            'type',
            'bill_no',
            'due_date',
            'inv_amount',
            'cycle1',
            'cycle2',
            'cycle3',
            'cycle4',
            'cycle5',
            'cycle6',
            'cycle7',
            'cycle8',
            'cycle9',
            'balance',
            'short_name'
        ]

        # Create a dictionary mapping old column names to new column names
        column_mapping = dict(zip(df.columns, new_column_names))

        # Rename columns
        df = df.rename(columns=column_mapping)
        
            # Calculate the balance directly in the DataFrame
        df['balance'] = df[['cycle1', 'cycle2', 'cycle3', 'cycle4', 'cycle5', 'cycle6', 'cycle7', 'cycle8', 'cycle9']].sum(axis=1)

        # Assuming df is your DataFrame
        df.to_excel('sorted_aging_report.xlsx', index=False)

        # Create a link to download the file
        FileLink('sorted_aging_report.xlsx')

        # Fetch all clients at once
        short_names = df['short_name'].astype(str).str.strip().unique()
        clients = Client.objects.filter(short_name__in=short_names)

        success_count = 0
        
        
        # Identify and delete bills not present in the Excel file
        existing_bills = Bill.objects.filter(
            short_name__in=clients.values('id')
        )
        bills_to_delete = existing_bills.exclude(bill_no__in=df['bill_no'].unique())

        if bills_to_delete.exists():
            bills_to_delete.delete() 
                
        for index, row in df.iterrows():
            try:
                short_name_value = row['short_name'].strip()
                client = clients.get(short_name=short_name_value)
                
                # Check if a Bill with the same data already exists
                existing_bill = Bill.objects.filter(
                    type=row['type'],
                    bill_no=row['bill_no'],
                    due_date=row['due_date'],
                    short_name=client,
                ).first()

                
                if existing_bill:
                    # Update existing Bill with new data
                    existing_bill.type = row['type']
                    existing_bill.due_date = row['due_date']
                    existing_bill.inv_amount = row['inv_amount']
                    existing_bill.cycle1 = row['cycle1']
                    existing_bill.cycle2 = row['cycle2']
                    existing_bill.cycle3 = row['cycle3']
                    existing_bill.cycle4 = row['cycle4']
                    existing_bill.cycle5 = row['cycle5']
                    existing_bill.cycle6 = row['cycle6']
                    existing_bill.cycle7 = row['cycle7']
                    existing_bill.cycle8 = row['cycle8']
                    existing_bill.cycle9 = row['cycle9']
                    existing_bill.balance = row['balance']

                    # Save the changes
                    existing_bill.save()
                    # Call the functions to update the client's balance and overdue120
                    update_client_balance(existing_bill.short_name)
                    overdue120d(existing_bill.short_name)
                                                
                    continue

                print("Before creating new_bill")
                
                # Create a new Bill instance
                new_bill=Bill.objects.create(
                    type=row['type'],
                    bill_no=row['bill_no'],
                    due_date=row['due_date'],
                    inv_amount=row['inv_amount'],
                    cycle1=row['cycle1'],
                    cycle2=row['cycle2'],
                    cycle3=row['cycle3'],
                    cycle4=row['cycle4'],
                    cycle5=row['cycle5'],
                    cycle6=row['cycle6'],
                    cycle7=row['cycle7'],
                    cycle8=row['cycle8'],
                    cycle9=row['cycle9'],
                    balance=row['balance'],
                    short_name=client,
                )
                success_count += 1
                print(new_bill)
                print(f"Due Date: {new_bill.due_date}")
                # Call the function to update the client's balance after each Bill creation
                update_client_balance(client)
                overdue120d(client)
                # create_actions_for_bill(new_bill)
                            
            except Client.DoesNotExist:
                error_messages.append(f'Client "{short_name_value}" not found\n')
            except ValidationError as e:
                error_messages.append(f'Validation error at row {index + 2}: {e}\n')
            except Exception as e:
                error_messages.append(f'Error processing row {index + 2}: {e}') 
        
            
                    
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

        send_update_email(update_subject, update_message) 
        
        
        
        
    except Exception as e:
        error_messages.append(f'Error processing Excel file: {e}')
        
    for error in error_messages:
        LogEntry.objects.create(message=error, is_error=True)
    
    for success in success_messages:
        LogEntry.objects.create(message=success, is_error=False)
        
    return success_messages, error_messages