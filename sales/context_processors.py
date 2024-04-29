from  .models import Action, Client, CreditEntry
from datetime import date, timedelta, datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .views import client_list

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
        from_date_param = request.GET.get('from')
        to_date_param = request.GET.get('to')
        account_param = request.GET.get('account_name')

        # Start with the base queryset
        entries = CreditEntry.objects.filter(collector=request.user, settle=False)

        # Apply date range filter if provided
        if from_date_param and to_date_param:
            from_date = datetime.strptime(from_date_param, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date_param, '%Y-%m-%d').date()
            entries = entries.filter(date__range=[from_date, to_date])

        # Apply account name filter if provided
        if account_param:
            # Filter entries by the account name
            entries = entries.filter(account_name__account_name__icontains=account_param)

        # Paginate the queryset
        paginator = Paginator(entries.order_by('-id'), 10)  # 10 entries per page
        page_number = request.GET.get('page')
        try:
            entries = paginator.page(page_number)
        except PageNotAnInteger:
            entries = paginator.page(1)
        except EmptyPage:
            entries = paginator.page(paginator.num_pages)

        for entry in entries:
            entry.message = f"You have credited {entry.amount} for {entry.account_name}"
            entry.date = entry.date.strftime("%d %b, %Y")

        return {"entries": entries}
    else:
        return {}