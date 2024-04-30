from datetime import date
from django import forms
from .models import Client,Action,Bill,CreditEntry

from django.utils import timezone


class ExcelUploadForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'dropify'}))
    
class ClientUploadForm(forms.Form):
    file = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'dropify'}))

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = '__all__'
        exclude = ['grant_period']
        widgets = {
            'account_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pan_number': forms.TextInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.TextInput(attrs={'class': 'form-control'}),
            'collector': forms.Select(attrs={'class': 'form-control'}),
            'guarantee_world_insurer': forms.TextInput(attrs={'class': 'form-control'}),
            'credit_limit': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class ActionUpdateForm(forms.ModelForm):
    class Meta:
        model = Action
        fields = ['completed']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form control class to the completed field
        self.fields['completed'].widget.attrs.update({'class': 'form-control'})


class ActionCreationForm(forms.ModelForm):
    class Meta:
        model = Action
        exclude = ['action_amount']

    action_date = forms.DateField(initial=timezone.now, widget=forms.DateInput(attrs={'readonly': 'readonly'}))
    
    # Use a callable for the queryset to dynamically filter based on the user
    account_name = forms.ModelChoiceField(
        queryset=Client.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    
    action_type = forms.ChoiceField(
        choices=Action.ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'btn btn-primary waves-effect waves-light'})
    )
    
    followup_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically set the queryset for the short_name field based on the user
        self.fields['account_name'].queryset = Client.objects.filter(collector=user)
        
        # Add form control to other fields if needed
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class SendSMSForm(forms.ModelForm):
    # Add non-model fields
    phone_number = forms.CharField(label='Phone Number', max_length=10)
    
    class Meta:
        model = Action
        fields = ['description', 'subtype']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add form control to other fields if needed
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

class ExtendActionForm(forms.Form):

    extended_date = forms.IntegerField(
        label='Number of Days to Extend',
        required=True,
        min_value=1  # Set a minimum value as needed
    )

class CreditEntryForm(forms.ModelForm):
    class Meta:
        model = CreditEntry
        fields = ['account_name', 'amount', 'date']

    account_name = forms.ModelChoiceField(
        queryset=Client.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    amount = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        required=True
    )

    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically set the queryset for the account_name field based on the user
        if user and user.is_authenticated:
            self.fields['account_name'].queryset = Client.objects.filter(collector=user)
        
        # Add form control to other fields if needed
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError('Amount is required')
        if amount < 0:
            raise forms.ValidationError('Amount must be positive')
        return amount
