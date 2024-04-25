from  .models import Action, Client, CreditEntry
from datetime import date, timedelta, datetime
from django.utils import timezone


def action_counts(request):
    manual_not_completed_count = Action.objects.filter(type='manual', completed=False).count()
    
    auto_count = Action.objects.filter(type='auto', completed=False).count()
    total_count = manual_not_completed_count + auto_count

    return {
        'manual_not_completed_count': manual_not_completed_count,
        'auto_count': auto_count,
        'total_count': total_count,
        
    }
    

def check_upcoming_actions(request, days_in_future=2):
    user = request.user

    # Check if the user is authenticated
    if user.is_authenticated: 
        today = date.today()
        future_date = today + timedelta(days=days_in_future)

        # Filter actions for the current user where follow-up date is up to two days in the future
        upcoming_actions = Client.objects.filter(
            collector=user,
            action__followup_date__range=[today, future_date]
        ).distinct()

        # Count of upcoming actions
        upcoming_actions_count = upcoming_actions.count()

        # Fetch clients for the current user where follow-up date is today
        clients_with_follow_up_today = Client.objects.filter(
            collector=user,
            action__followup_date=today
        ).distinct()
        
        follow_up_today = clients_with_follow_up_today.count()

        return {
            'upcoming_actions': upcoming_actions,
            'upcoming_actions_count': upcoming_actions_count,
            'clients_with_follow_up_today': clients_with_follow_up_today,
            'follow_up_today': follow_up_today,
        }
    else:
        # If the user is not authenticated, return empty data
        return {
            'upcoming_actions': [],
            'upcoming_actions_count': 0,
            'clients_with_follow_up_today': [],
            'follow_up_today': 0,
        }

def notifications_context(request):
    if request.user.is_authenticated:
        # Get the date parameter from the request's query string
        from_date_param = request.GET.get('from')
        to_date_param = request.GET.get('to')

        if from_date_param and to_date_param:
            # Convert the date strings to datetime objects
            from_date = datetime.strptime(from_date_param, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_param, '%Y-%m-%d').date()
            # Fetch CreditEntry objects within the specified date range for the current user, excluding settled entries
            data = CreditEntry.objects.filter(date__range=[from_date, to_date], collector=request.user, settle=False).order_by('-id')
        else:
            # Fetch all unsettled CreditEntry objects for the current user
            data = CreditEntry.objects.filter(collector=request.user, settle=False).order_by('-id')

        # Assign message for each entry
        for entry in data:
            entry.message = f"You have credited {entry.amount} for {entry.account_name}"
            entry.date = entry.date.strftime("%d %b, %Y")

        # Return data
        return {
            "entries": data
        }
    else:
        # Return an empty dictionary if the user is not authenticated
        return {}