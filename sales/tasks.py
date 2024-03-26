from celery import shared_task
from django.contrib import messages
from django.forms import ValidationError
from django.shortcuts import redirect, render
from requests import request
from .forms import ExcelUploadForm
import pandas as pd
from .models import Bill, Client
from datetime import datetime

from sales.utils import bill_process

@shared_task
def bill_upload(file_contents):
    try:
        # Call the bill_process view function and pass the file contents
        bill_process(file_contents)
        
    except Exception as e:
        print("Error:", e)