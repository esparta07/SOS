from celery import shared_task
from django.contrib import messages
from django.forms import ValidationError
from django.shortcuts import redirect, render
from requests import request
from .forms import ExcelUploadForm
import pandas as pd
from .utils import convert_date_format,convert_nepali_to_ad,overdue120d,update_client_balance,create_actions_for_bill,delete_actions,company_balance,update_collector_balances,calculate_total_balance_for_all_collectors,send_update_email
from .models import Bill, Client
from datetime import datetime

@shared_task
def bill_upload(file_contents):
    try:
        # Assuming file_contents is the Excel file content
        excel_data = pd.read_excel(file_contents)
        
        # Skip the first 3 rows
        df = excel_data.iloc[3:]
        df.columns = df.iloc[0]
        
        # Your processing logic here...
        
        success_messages = []
        error_messages = []
        
        # Set the 0th row data as column headings
        df.columns = df.iloc[0]
        
        # Check if the expected columns are present
        expected_columns = ['Type', 'Bill No.', 'Date', 'Due Date', 'Days', 'Inv.Amt', '0 - 15',
                            '16 - 30', '31 - 45', '46 - 60', '61 - 75', '76 - 90', '91 - 105',
                            '106 - 120', 'Over 121', 'Balance']

        if not all(col in df.columns for col in expected_columns):
            error_message = 'Wrong format file. Please make sure all required columns are present.'
            error_messages.append(error_message)
            print(error_messages)  
            return error_message
        
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
                create_actions_for_bill(new_bill)
                        
            except Client.DoesNotExist:
                error_messages.append(f'Client "{short_name_value}" not found at row {index + 2}\n')
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







