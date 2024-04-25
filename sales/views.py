
from datetime import datetime, timedelta, date
from django.shortcuts import get_object_or_404, redirect, render
from .models import Action, CreditEntry
from .filters import ActionFilter

from .models import Client, Bill, Action

from .models import Client, Bill, Action,LogEntry

from django.contrib import messages
from .forms import ExcelUploadForm, ClientForm, ActionUpdateForm, ActionCreationForm, ExtendActionForm,SendSMSForm,ClientUploadForm,CreditEntryForm
from django.core.exceptions import  ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.core.files.storage import default_storage
from django.db.models import Sum, F
from decimal import Decimal
from django.utils import timezone
import pandas as pd
import requests
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.serializers.json import DjangoJSONEncoder
from django.template import Context, Template
import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from account.utils import check_role_admin, check_role_user

from sales.tasks import bill_upload

from sales.tasks import bill_upload
from collections import defaultdict


# Create your views here.
@login_required(login_url='login')
def profile(request):
    return render(request , 'profile.html')


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def upload_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            
            try:
                
                # Get file contents
                file_contents = request.FILES['file'].read()

                # Call the Celery task to process the uploaded Excel file
                bill_upload.delay(file_contents)

                # Notify the user that the file is being processed
                messages.info(request, "The uploaded Excel file is being processed. Please wait for the results.")

                return redirect('upload_excel')

            except Exception as e:
                messages.error(request, f'Error processing Excel file: {e}')

    else:
        form = ExcelUploadForm()

    return render(request, 'upload.html', {'form': form})


@login_required(login_url='login')
@user_passes_test(check_role_user)
def collection(request):
     # Filter clients for the currently logged-in user
    clients = Client.objects.filter(collector=request.user)

    
    # Filter actions for the currently logged-in user
    actions = Action.objects.filter(account_name__collector=request.user).order_by('-created')
     
    # Calculate the count of manual actions that are not completed
    manual_not_completed_count = Action.objects.filter(type='manual', completed=False).count()
    auto_count = Action.objects.filter(type='auto', completed=False).count()
   
    # Set the initial value of the "Action Date" field to today's date
    today_date = datetime.today()
    # Corrected usage
    add_form = ActionCreationForm(user=request.user, initial={'action_date': today_date})

    update_form = ActionUpdateForm()
    if request.method == 'POST':
        
        if 'add_action' in request.POST:
            action_type = request.POST.get('action_type')
            account_name_id = request.POST.get('account_name')
            description=request.POST.get('description')
            subtype=request.POST.get('subtype')
            followup_date=request.POST.get('followup_date')
            completed=request.POST.get('completed')
            if followup_date=='':
                followup_date=None
            
            # Validate that required fields are present
            if not (action_type ):
                messages.error(request, 'Action type is  required')
                return redirect('collection')

            # Fetch the related objects
            try:
                
                account_name = Client.objects.get(pk=account_name_id)
            except (Bill.DoesNotExist, Client.DoesNotExist):
                messages.error(request, 'Invalid bill number or short name.')
                return redirect('collection')

            # Set the action_amount to the balance of the corresponding bill
            action_amount = account_name.balance if hasattr(account_name, 'balance') else 0

            type = 'manual'  # Set the type to 'manual'

            # Create an Action instance and save it to the database
            action_instance = Action(
                action_date=today_date,
                type=type,
                action_type=action_type,
                action_amount=action_amount,
                account_name=account_name,
                followup_date=followup_date,
                description=description,
                subtype=subtype,
                completed=True,
            )
            action_instance.save()

            return redirect('collection')
                
        # Check if the form submitted is the ActionUpdateForm
        elif 'update_actions' in request.POST:
            update_form = ActionUpdateForm(request.POST)
            if update_form.is_valid():
                selected_actions_ids = request.POST.getlist('completed_actions')
                
                # Convert the list of strings to a list of integers
                selected_actions_ids = [int(action_id) for action_id in selected_actions_ids]

                # Update the completion status of selected actions
                Action.objects.filter(id__in=selected_actions_ids).update(completed=True)

                # Recalculate the counts after the update
                manual_not_completed_count = Action.objects.filter(type='manual', completed=False).count()
                auto_count = Action.objects.filter(type='auto', completed=False).count()

                # Redirect to the same view to avoid resubmitting the form on page reload
                return redirect('collection')
    else:
        add_form = ActionCreationForm(user=request.user)
        update_form = ActionUpdateForm()

    context = {'actions': actions, 
               'clients': clients,
               'manual_not_completed_count': manual_not_completed_count, 
               'auto_count': auto_count,
               'add_form': add_form,
               'update_form': update_form}
    return render(request, 'collection.html', context)


def download_excel(request):
    file_path = 'sorted_aging_report.xlsx'
    if default_storage.exists(file_path):
        with default_storage.open(file_path, 'rb') as excel_file:
            response = HttpResponse(excel_file.read(), content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = f'attachment; filename="{file_path}"'
            return response
    else:
        return HttpResponse("File not found", status=404)
    
@login_required(login_url='login')
@user_passes_test(check_role_admin)
def client(request):
    clients = Client.objects.all()
    if request.method == 'POST':
        form = ClientUploadForm(request.POST, request.FILES)
        
    else:
        form = ClientUploadForm()

    context = {
        'form': form,
        'clients': clients,
        
    }    
    return render(request , 'client.html' , context)

@login_required(login_url='login')
def client_profile(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    actions = Action.objects.filter(account_name=client).order_by('-created')
    bills = Bill.objects.filter(account_name=client)
    cyclebills = client.bill_set.all()
    

    aging_data = {
        'cycle1': Decimal(0),
        'cycle2': Decimal(0),
        'cycle3': Decimal(0),
        'cycle4': Decimal(0),
        'cycle5': Decimal(0),
        'cycle6': Decimal(0),
        'cycle7': Decimal(0),
        'cycle8': Decimal(0),
        'cycle9': Decimal(0),
    }
    
    for bill in cyclebills:
        cycle = bill.cycle
        if cycle is not None:
            aging_data[f'cycle{cycle}'] += Decimal(bill.inv_amount)

    # Check if all actions for the client have completed=True
    all_actions_completed = all(action.completed for action in actions)

    incomplete_actions = []  # Initialize as an empty list

    if all_actions_completed:
        # If all actions are completed, store the last action
        last_action = actions.first()
    else:
        # If not all actions are completed, filter and store only the incomplete ones
        incomplete_actions = [action for action in actions if not action.completed]
        last_action = None  # Initialize to None, in case there are no incomplete actions

   

    total_amount = client.balance
    # Calculate percentages based on grand total balance
    percentages = calculate_percentages(aging_data, total_amount)
    
    
    if request.method == 'POST':
        sms_form = SendSMSForm(request.POST)
        if sms_form.is_valid():
            # Process the form data
            description = sms_form.cleaned_data['description']
            subtype = sms_form.cleaned_data['subtype']
            phone_number = sms_form.cleaned_data['phone_number']


            # For example, log the SMS action in the database
            Action.objects.create(
                action_date=timezone.now(),
                type='manual',
                action_type='SMS',
                action_amount=client.balance,  
                short_name=client,
                subtype=subtype,
                description=description,
                completed=True,
                
            )

            # Send the SMS using an external service 
            send_sms(phone_number, description)

            # Redirect or render a response as needed
            return redirect(request.path)
    else:
        # Assuming you have access to the client's phone number
        initial_phone_number = client.phone_number if client.phone_number else ''
        sms_form = SendSMSForm(initial={'phone_number': initial_phone_number})


    context = {
        'client': client,
        'actions': actions,
        'last_action': last_action,
        'incomplete_actions': incomplete_actions,
        'cyclebills': cyclebills,
        'aging_data': aging_data,
        'percentages': percentages,
        'bills': bills,
        'sms_form':sms_form,
        
    }

    return render(request, 'client_profile.html', context)

def pause_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    
    if request.method == 'POST':
        # Toggle the 'pause' field
        client.pause = not client.pause
        client.save()
    
    # Redirect back to the client profile page
    return redirect('client_profile', client_id=client_id)

@login_required(login_url='login')
def edit_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)

    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid(): 
            form.save()
            return redirect('client')  # Redirect to a success page or another view
    else:
        form = ClientForm(instance=client)

    return render(request, 'edit_client.html', {'form': form, 'client': client})

@login_required(login_url='login')
def delete_client(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    client.delete()
    messages.success(request, 'Client has been deleted successfully!')
    return redirect('client')

@login_required(login_url='login')
def add_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client')  # Redirect to a success page or another view
    else:
        form = ClientForm()

    return render(request, 'add_client.html', {'form': form, 'client': None})
       
def get_client_names(request):
    # Query all clients and their associated bill numbers
    client_data = (
        Client.objects
        .values('account_name')
        .annotate(bill_numbers=F('bill__bill_no')).distinct()
    )

    # Convert QuerySet to a list of dictionaries
    client_data_list = list(client_data)

    # Iterate over the list and fetch all unique bill numbers for each client
    for client in client_data_list:
        # Use a set to ensure uniqueness of bill numbers
        unique_bill_numbers = set(Bill.objects.filter(short_name__account_name=client['account_name']).values_list('bill_no', flat=True))
        client['bill_numbers'] = list(unique_bill_numbers)

    return JsonResponse({'client_data': client_data_list}, encoder=DjangoJSONEncoder, safe=False)

# AJAX
def load_bills(request):
    client_id = request.GET.get('client_id')
    client = get_object_or_404(Client, pk=client_id)
    bills = Bill.objects.filter(short_name=client).order_by('bill_no')
    
    options = '<option value="">---------</option>'
    for bill in bills:
        options += f'<option value="{bill.id}">{bill.bill_no}</option>'
    
    return HttpResponse(options)

def send_sms(phone_number, sms_content, simulate_success=False):
    if simulate_success:
        # Simulate a successful response without making the actual API call
        print(f"Simulated success: SMS content for {phone_number}: {sms_content}")
        return True, "Simulated success: SMS content printed"

    url = "https://api.sparrowsms.com/v2/sms/"
    data = {
        'token': 'v2_M1vtw2aeNOXETkVFSgoOXmOchwN.BR',
        'from': 'Demo',
        'to': phone_number,
        'text': sms_content,
    }

    response = requests.post(url, data=data)

    if response.status_code == 200:
        # If SMS is successfully sent, return a tuple indicating success
        return True, response.text
    else:
        # If there is an error, return a tuple indicating failure
        return False, response.text

@receiver(post_save, sender=Action)
def check_and_trigger_sms(sender, instance, **kwargs):
    # Disconnect the signal to prevent it from triggering multiple times
    post_save.disconnect(check_and_trigger_sms, sender=Action)
    
    today = timezone.now().date()

    # Check if the action type is 'auto' and action_type is 'SMS'
    if instance.type == 'auto' and instance.action_type == 'SMS' and instance.action_date == today and not instance.completed: 
        try:
            # Fetch related client and bill
            client = instance.account_name

            # Get dynamic SMS content based on subtype
            sms_content = generate_sms_text(instance.subtype, client)

            # Trigger send_sms function
            success, response_text = send_sms(client.phone_number, sms_content)

            if success:
                # Update the 'completed' field to True if SMS is sent successfully
                # Check if 'completed' is already True before updating
                if not instance.completed:
                    instance.completed = True
                    instance.description = sms_content
                    instance.save()
            else:
                # If sending SMS fails, update the instance description with the "response" part
                try:
                    response_json = json.loads(response_text)
                    instance.description = response_json.get("response", response_text)
                except json.JSONDecodeError:
                    instance.description = response_text

                # Optionally, you may log the error or take other actions if needed
                print(f"SMS sending failed. Response: {response_text}")
                instance.save()

        except ObjectDoesNotExist:
            # Handle the case where the related client is not found
            print("Client not found for the given Action.")

        except Exception as e:
            # Handle any other exceptions that might occur
            print(f"Error occurred: {e}")

    # Reconnect the signal after processing
    post_save.connect(check_and_trigger_sms, sender=Action)

def generate_sms_text(subtype, client):
    # Default agent name (you can replace it with actual agent name)
    agent_name = client.collector.full_name if client.collector else "Accounts Team"

    # Default contact number (you can replace it with actual contact number)
    contact_number = "9800000001"

    # Initialize template string based on subtype
    template_str = ""

    if subtype == 'Reminder':
        template_str = "Dear {{ client.account_name }}, This is {{ agent_name }} from SparrowSMS. We'd like to remind you that payment for Nrs. {{ client.balance }} is due. For more information, call {{ contact_number }}."

    elif subtype == 'Gentle':
        template_str = "Dear {{ client.account_name }},A gentle reminder of payment Rs{{ client.balance }} is pending. Please send the payment and contact: {{ agent_name }} SPARROW SMS."

    elif subtype == 'Strong':
        template_str = "Dear {{ client.account_name }}, we still have not received Nrs {{ bill.balance }} payment . We request you to make the payment as soon as possible. {{ contact_number }} SPARROW SMS."

    elif subtype == 'Final':
        template_str = "Dear {{ client.account_name }}, after several attempts and reminders, we have not received the due Nrs. {{ bill.balance }}. Unfortunately, service will be blocked. Contact us at {{ contact_number }}."

    else:
        return "Unknown subtype."

    # Render the template with dynamic data
    template = Template(template_str)
    context = Context({'client': client, 'agent_name': agent_name, 'contact_number': contact_number})
    return template.render(context)

@login_required(login_url='login')
def action(request):
    clients = Client.objects.all()
    actions = Action.objects.all().order_by('-created')

    # Process the date range filter
    date_from = request.GET.get('action_date_from')
    date_to = request.GET.get('action_date_to')

    if date_from and date_to:
        date_from = datetime.strptime(date_from, "%Y-%m-%d")
        date_to = datetime.strptime(date_to, "%Y-%m-%d")
        actions = actions.filter(action_date__range=[date_from, date_to])
    
    # Calculate the count of manual actions that are not completed
    manual_not_completed_count = Action.objects.filter(type='manual', completed=False).count()
    auto_count = Action.objects.filter(type='auto', completed=False).count()
   
    # Set the initial value of the "Action Date" field to today's date
    today_date = date.today()

    action_filter = ActionFilter(request.GET, queryset=actions)
    actions = action_filter.qs


    context = {'actions': actions, 
               'clients': clients,
               'manual_not_completed_count': manual_not_completed_count, 
               'auto_count': auto_count,
               'action_filter': action_filter, 
                }
   
    return render(request, 'action.html' , context)


def calculate_total_cycles_for_client(client):
    total_cycles = defaultdict(float)  # Initialize a dictionary to store total cycles for the client
    
    # Iterate through the client's bills
    for bill in Bill.objects.filter(account_name=client):
        cycle = bill.cycle  # Get the cycle for the bill
        amount = bill.inv_amount  # Get the amount from the bill
        
        # Add the amount to the corresponding cycle
        total_cycles[f'cycle{cycle}'] += amount
    
    return dict(total_cycles)


@login_required(login_url='login')
@user_passes_test(check_role_admin)
def aging(request):
    clients = Client.objects.all()

    # Dictionary to store total cycles for each client
    total_cycles_by_client = {}

    for client in clients:
        total_cycles_by_client[client.id] = calculate_total_cycles_for_client(client)

    aging_data = {
        'cycle1': Decimal(0),
        'cycle2': Decimal(0),
        'cycle3': Decimal(0),
        'cycle4': Decimal(0),
        'cycle5': Decimal(0),
        'cycle6': Decimal(0),
        'cycle7': Decimal(0),
        'cycle8': Decimal(0),
        'cycle9': Decimal(0),
    }

    for client in clients:
        cyclebills = client.bill_set.all()
        for bill in cyclebills:
            cycle = bill.cycle
            if cycle is not None:
                aging_data[f'cycle{cycle}'] += Decimal(bill.inv_amount)
    for key, value in aging_data.items():
        aging_data[key] = round(value, 2)

    # Calculate the total sum of all bills
    total_sum = sum(aging_data.values())

    # Calculate the grand total sum of all bills' balance
    grand_total_balance = Bill.objects.aggregate(Sum('inv_amount'))['inv_amount__sum'] or 0

    # Calculate percentages based on grand total balance
    percentages = calculate_percentages(aging_data, grand_total_balance)

    context = {
        'aging_data': aging_data,
        'total_sum': total_sum,
        'grand_total_balance': grand_total_balance,
        'percentages': percentages,
        'clients': clients,
        'total_cycles_by_client': total_cycles_by_client,
    }

    return render(request, 'aging.html', context)


@login_required(login_url='login')
def delete_action(request , action_id):
    action = get_object_or_404(Action, id=action_id)
    action.delete()
    messages.success(request, 'Action has been deleted successfully!')
    return redirect('action')

def calculate_percentages(aging_data, total_amount):
    if total_amount == 0:
        return {
            'percentage_0_30_days': 0,
            'percentage_31_60_days': 0,
            'percentage_61_90_days': 0,
            'percentage_90_days_plus': 0,
        }

    percentage_0_30_days = (float(aging_data['cycle1']) + float(aging_data['cycle2'])) / float(total_amount) * 100
    percentage_31_60_days = (float(aging_data['cycle3']) + float(aging_data['cycle4'])) / float(total_amount) * 100
    percentage_61_90_days = (float(aging_data['cycle5']) + float(aging_data['cycle6'])) / float(total_amount) * 100
    percentage_90_days_plus = (float(aging_data['cycle7']) + float(aging_data['cycle8']) + float(aging_data['cycle9'])) / float(total_amount) * 100

    # Adjust the final percentage to ensure it sums up to 100%
    total_percentage = percentage_0_30_days + percentage_31_60_days + percentage_61_90_days + percentage_90_days_plus
    adjustment = 100 - total_percentage
    percentage_90_days_plus += adjustment

    return {
        'percentage_0_30_days': '{:.2f}'.format(percentage_0_30_days),
        'percentage_31_60_days': '{:.2f}'.format(percentage_31_60_days),
        'percentage_61_90_days': '{:.2f}'.format(percentage_61_90_days),
        'percentage_90_days_plus': '{:.2f}'.format(percentage_90_days_plus),
    }


@login_required(login_url='login')
def extend_action_dates(request, client_id):
    client = Client.objects.get(pk=client_id)
    actions = Action.objects.filter(short_name=client)

    if request.method == 'POST':
        form = ExtendActionForm(request.POST)
        if form.is_valid():
            # Process the form data and update the action dates for all actions of the client

            # Example:
            days_to_extend = form.cleaned_data['extended_date']

            for action in actions:
                # Add days_to_extend to the original action date for each action
                if days_to_extend:
                    action.action_date += timedelta(days=days_to_extend)
                    action.save()

            return redirect('client_profile', client_id=client_id)
    else:
        form = ExtendActionForm()

    context = {
        'client': client,
        'actions': actions,
        'form': form,
    }

    return render(request, 'client_profile.html', context)

@login_required(login_url='login')
@user_passes_test(check_role_user)
def myclient(request):
    user = request.user
    # Filter clients for the currently logged-in user
    clients = Client.objects.filter(collector=user)
    context = {
        'user': user,
        'clients': clients,
        
    }
    return render(request, 'myclient.html',context)

def process_uploaded_file(request):
    if request.method == 'POST':
        form = ClientUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Validate file format
            uploaded_file = request.FILES['file']
            if not uploaded_file.name.endswith('.xlsx'):
                messages.error(request, "Invalid file format. Please upload a .xlsx file.")
                return redirect('client')

            try:
                # Retrieve the uploaded file from the form
                excel_data = pd.read_excel(uploaded_file)

                # Perform data processing steps
                df = excel_data.iloc[3:]
                df = df[:-2]
                df.columns = df.iloc[0]

                # Validate the required columns
                required_columns = {'Short Name', 'Account Name', 'Phone (O) & Contact', 'Address', 'PAN No.', 'Balance'}
                if not set(df.columns).issuperset(required_columns):
                    # If any of the required columns is missing, handle the validation error
                    messages.error(request, "The format of the excel file is invalid. Check for invalid column names or missing columns.")
                    return redirect('client')  # Redirect back to the 'client' view

                df = df.iloc[1:]
                df = df.reset_index(drop=True)
                df = df.rename(columns={df.columns[2]: 'POC'})
                df[['Phone', 'Contact Name']] = df['POC'].str.extract(r'([^a-zA-Z]+)-\s*([^0-9]+)')
                df = df.drop(columns=['POC'])

                df = df.rename(columns={
                    'Short Name': 'short_name',
                    'Account Name': 'account_name',
                    'Address': 'address',
                    'PAN No.': 'pan_number',
                    'Balance': 'balance',
                    'Phone': 'phone_number',
                    'Contact Name': 'contact_name'
                    
                })
                
                # Fill NaN values with blanks
                df = df.fillna('')

                # Additional processing logic
                created_count = 0
                updated_count = 0

                for index, row in df.iterrows():
                    try:
                        # Check if short name already exists in the database
                        short_name = row.get('short_name')
                        existing_client = Client.objects.filter(short_name=short_name).first()

                        if existing_client:
                            # Client with this short name already exists, you can update or skip
                            existing_client.account_name = row.get('account_name', existing_client.account_name)
                            existing_client.address = row.get('address', existing_client.address)
                            existing_client.pan_number = row.get('pan_number', existing_client.pan_number)

                            # Ensure that the balance is within the allowed range
                            new_balance = row.get('balance', existing_client.balance)
                            existing_client.balance = min(max(new_balance, -10**6), 10**8)  # Adjust as needed

                            existing_client.phone_number = row.get('phone_number', existing_client.phone_number)
                            existing_client.email = row.get('email', existing_client.email)
                            existing_client.contact_name = row.get('contact_name', existing_client.contact_name)

                            existing_client.save()
                            updated_count += 1
                        else:
                            # Create a new client using DataFrame values
                            new_client = Client.objects.create(
                                short_name=row.get('short_name'),
                                account_name=row.get('account_name'),
                                address=row.get('address'),
                                pan_number=row.get('pan_number'),

                                # Ensure that the balance is within the allowed range
                                balance = min(max(row.get('balance', 0), -10**6), 10**8),  # Adjust as needed

                                phone_number=row.get('phone_number'),
                                contact_name=row.get('contact_name'),
                                
                                # Add other fields as needed
                            )
                            created_count += 1
                    except Exception as e:
                        # Print the error and information about the row causing the issue
                        print(f"Error processing row {index + 4} (Excel row {index + 1}): {e}")
                        print(row)
                        # Optionally, log the error for further investigation
                if created_count >0:
                    # Display success message
                    messages.success(request, f"{created_count} new clients created successfully")
                else:
                    messages.success(request, "No new client was added")
                
                # Redirect back to the 'client' view after processing
                return redirect('client')
            except Exception as e:
                # Handle any exception during file processing
                messages.error(request, f"Error processing the file: {e}")
                return redirect('client')

    return redirect('client')

def credit_entry(request):
    if request.method == 'POST':
        form = CreditEntryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Credit Entry added successfully")
            # Clear the form by instantiating a new form object
            return redirect('credit_entry')  # Redirect to the same page to display success message and clear form
    else:
        # If the request method is not POST, create a new instance of the form
        form = CreditEntryForm()


    # If form validation fails, display form errors
    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, f"Error adding credit entry: {error}")

    # Render the HTML template with the form instance in the context
    return render(request, 'credit_track.html', {'form': form})

@login_required
def notification(request):
    # Filter out unsettled entries for the current user (collector)
    unsettled_entries = CreditEntry.objects.filter(collector=request.user, settle=False)
    return render(request, 'notification.html', {'entries': unsettled_entries})

def settle_notification(request, entry_id):
    if request.method == 'POST':
        entry = CreditEntry.objects.get(pk=entry_id)
        entry.settle = True
        entry.save()  # Save the entry with settle=True instead of deleting it
    return redirect('notification')

def log_page(request):
    log_entries = LogEntry.objects.order_by('-timestamp')  
    return render(request, 'log_page.html', {'log_entries': log_entries})




