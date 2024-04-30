from  .models import Action, Client, CreditEntry
from datetime import date, timedelta, datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from .views import client_list
from .filters import ClientFilter

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



def notifications(request):
    if request.user.is_authenticated:
        # Fetch all unsettled CreditEntry objects for the current user
        unsettled_entries = CreditEntry.objects.filter(collector=request.user, settle=False)
        
        # Filter entries that are older than yesterday
        yesterday = datetime.now() - timedelta(days=1)
        older_entries = unsettled_entries.filter(date__lte=yesterday)
        
        # Get the 10 newest older entries
        oldest_entries = older_entries.order_by('-date')[:10]
        
        # Count the number of older entries
        older_entries_count = older_entries.count()
        
        return {
            'notifications': oldest_entries,
            'notifications_count': older_entries_count,
        }
    else:
        return {}
