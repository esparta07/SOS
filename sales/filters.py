# filters.py
import django_filters
from django import forms
from django_filters.widgets import RangeWidget

from account.models import User
from .models import Action, Client

class ActionFilter(django_filters.FilterSet):
    short_name__collector = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(role=User.USER),
        empty_label='Select Collector ',
        label='',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    action_date = django_filters.DateFromToRangeFilter(
        widget=RangeWidget(attrs={'class': 'form-control', 'placeholder': 'Date Filter'}),
    )

    # completed = django_filters.BooleanFilter(
    #     label='Completed',
    #     widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    # )


    short_name = django_filters.ModelChoiceFilter(
        queryset=Client.objects.all(),
        empty_label='Select Client Name',
        label='',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Action
        fields = ['short_name__collector', 'action_date', 'short_name', 'completed']


class ClientFilter(django_filters.FilterSet):
    account_name = django_filters.ModelChoiceFilter(
        queryset=Client.objects.all(),  # Use queryset to specify available choices
        
        empty_label="Select Client",
        label='',
        widget=forms.Select(attrs={'class': 'form-control'}),
        field_name='account_name' 
    )
    
    # You can define a method to customize the queryset if needed
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Example: filter the queryset based on the collector
        collector = kwargs.get('collector')
        if collector:
            self.queryset = self.queryset.filter(collector=collector)

    class Meta:
        model = Client
        fields = ['account_name']