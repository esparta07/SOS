from celery import shared_task
from django.contrib import messages
from django.forms import ValidationError
from requests import request
import pandas as pd
from .utils import (
    overdue120d,
    update_client_balance,
    create_actions_for_bill,
    delete_actions,
    company_balance,
    update_collector_balances,
    calculate_total_balance_for_all_collectors,
    send_update_email
)
from .models import Bill, Client
from datetime import datetime

@shared_task
def bill_upload(file_contents):
    try:
        # Assuming file_contents is the Excel file content
        excel_data = pd.read_excel(file_contents, skiprows=5)
        
        df = excel_data.drop(0, axis=0)
        
        # Deleting the unnecessary column
        df = df.drop(["Unnamed: 0", "Due Miti"], axis=1)

        # Deleting the row of the total amount that is displayed
        df = df[:-1] 

        # Your processing logic here...
        
        success_messages = []
        error_messages = []
        
        # Set the 0th row data as column headings
        df.columns = df.iloc[0]
        
        # Check if the expected columns are present
        expected_columns = ['Date', 'Ref. No.', "Party's Name", 'Pending', 'Due on', 'Overdue']

        if not all(col in df.columns for col in expected_columns):
            error_message = 'Wrong format file. Please make sure all required columns are present.'
            error_messages.append(error_message)
            print(error_messages)
            return error_messages  # Return error messages to the caller
            
        # Reset the index after filtering
        df = df.reset_index(drop=True)

        # Reset the index after removing rows and set the 0th row as the new column headings
        df = df.iloc[1:].reset_index(drop=True)
        df.fillna(0, inplace=True)
        
        df['Due on'] = pd.to_datetime(df['Due on'])  # Convert 'Due on' to datetime
        
        current_date = datetime.now()

        df['Aging'] = (current_date - df['Due on']).dt.days
        
        # Define a function to categorize aging
        def categorize_aging(age):
            if age >= 0 and age <= 15:
                return 'cycle1'
            elif age >= 16 and age <= 30:
                return 'cycle2'
            elif age >= 31 and age <= 45:
                return 'cycle3'
            elif age >= 46 and age <= 60:
                return 'cycle4'
            elif age >= 61 and age <= 75:
                return 'cycle5'
            elif age >= 76 and age <= 90:
                return 'cycle6'
            elif age >= 91 and age <= 105:
                return 'cycle7'
            elif age >= 106 and age <= 120:
                return 'cycle8'
            else:
                return 'cycle9'

        # Apply the categorize_aging function to the Aging column to get the cycle for each row
        df['Cycle'] = df['Aging'].apply(categorize_aging)

        # Define the new column names
        new_column_names = [
            'type',
            'bill_no',
            'due_date',
            'pending_amount',
            'overdue',
            'cycle1',
            'cycle2',
            'cycle3',
            'cycle4',
            'cycle5',
            'cycle6',
            'cycle7',
            'cycle8',
            'cycle9',
            'short_name'
        ]

        # Create a dictionary mapping old column names to new column names
        column_mapping = dict(zip(df.columns, new_column_names))

        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Calculate the balance directly in the DataFrame
        df['balance'] = df[new_column_names[5:14]].sum(axis=1)

        # Assuming df is your DataFrame
        df.to_excel('sorted_aging_report.xlsx', index=False)

        

        # Fetch all clients at once
        short_names = df['short_name'].astype(str).str.strip().unique()
        clients = Client.objects.filter(short_name__in=short_names)

        success_count = 0
        
        
        # Identify and delete bills not present in the Excel file
        existing_bills = Bill.objects.filter(
        short_name__in=clients.values('id')
        )
        bills_to_delete = existing_bills.exclude(ref_no__in=df['Ref. No.'].unique())

        if bills_to_delete.exists():
            bills_to_delete.delete() 
                    
        for index, row in df.iterrows():
            try:
                ref_no_value = row['Ref. No.'].strip()
                client = clients.get(ref_no=ref_no_value)
                        
                # Check if a Bill with the same data already exists
                existing_bill = Bill.objects.filter(
                    ref_no=row['Ref. No.'],
                    due_on=row['Due on'],  # Assuming 'due_on' is a field in your Bill model
                    short_name=client,
                ).first()

                        
                if existing_bill:
                    # Update existing Bill with new data
                    existing_bill.type = row['type']
                    existing_bill.due_on = row['Due on']
                    existing_bill.pending = row['Pending']
                    existing_bill.overdue = row['Overdue']
                    existing_bill.aging = row['Aging']
                    existing_bill.cycle = row['Cycle']
                    # Assuming there are fields named cycle1, cycle2, ..., cycle9 in your Bill model
                    existing_bill.cycle1 = row['cycle1']
                    existing_bill.cycle2 = row['cycle2']
                    existing_bill.cycle3 = row['cycle3']
                    existing_bill.cycle4 = row['cycle4']
                    existing_bill.cycle5 = row['cycle5']
                    existing_bill.cycle6 = row['cycle6']
                    existing_bill.cycle7 = row['cycle7']
                    existing_bill.cycle8 = row['cycle8']
                    existing_bill.cycle9 = row['cycle9']
                    
                    # Save the changes
                    existing_bill.save()
                    # Call the functions to update the client's balance and overdue120
                    update_client_balance(existing_bill.short_name)
                    overdue120d(existing_bill.short_name)
                                                    
                    continue

                print("Before creating new_bill")
                # If a bill with the given data doesn't exist, create a new one
                new_bill = Bill.objects.create(
                    type=row['type'],  # Assuming 'type' is a field in your Bill model
                    ref_no=row['Ref. No.'],
                    due_on=row['Due on'],  # Assuming 'due_on' is a field in your Bill model
                    pending=row['Pending'],
                    overdue=row['Overdue'],
                    aging=row['Aging'],
                    cycle=row['Cycle'],
                    cycle1=row['cycle1'],
                    cycle2=row['cycle2'],
                    cycle3=row['cycle3'],
                    cycle4=row['cycle4'],
                    cycle5=row['cycle5'],
                    cycle6=row['cycle6'],
                    cycle7=row['cycle7'],
                    cycle8=row['cycle8'],
                    cycle9=row['cycle9'],
                    # Assuming 'short_name' is a ForeignKey field in your Bill model referencing your Client model
                    short_name=client,
                )
                # Call the functions to update the client's balance and overdue120
                update_client_balance(new_bill.short_name)
                overdue120d(new_bill.short_name)
                    
                # Create a new Bill instance
                new_bill = Bill.objects.create(
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
                create_actions_for_bill(new_bill)
                create_actions_for_bill(new_bill)
                            
            except Client.DoesNotExist:
                                error_messages.append(f'Client "{short_names}" not found at row {index + 2}\n')
            except ValidationError as e:
                                error_messages.append(f'Validation error at row {index + 2}: {e}\n')
            except Exception as e:
                                error_messages.append(f'Error processing row {index + 2}: {e}')
                    
            
                        
        if success_count > 0:
            success_messages.append(f"{success_count} records successfully uploaded.")
            
        else:
            download_link = None
            
        for success_message in success_messages:
            messages.success(request, success_message)
        for error_message in error_messages:
            messages.error(request, error_message)
        

        calculate_total_balance_for_all_collectors()
        update_collector_balances()
        company_balance()
        delete_actions()  
        
        today_date = datetime.today()
        formatted_today_date = today_date.strftime('%Y-%m-%d %H:%M:%S')  

        update_subject = 'Excel File Update Notification'
        update_message = f'The Excel file has been successfully uploaded on {formatted_today_date}'

        # send_update_email(update_subject, update_message) 
                    
        
        print("Processing uploaded Excel file...")
        
    except Exception as e:
        print(f"Error processing uploaded Excel file: {e}")
