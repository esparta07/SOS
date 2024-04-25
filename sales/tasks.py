from celery import shared_task


from sales.utils import bill_process

@shared_task
def bill_upload(file_contents):
    try:
        # Call the bill_process view function and pass the file contents
        bill_process(file_contents)

    except Exception as e:
        print("Error:", e)