from django.urls import path 
from . import views

urlpatterns = [
    path('profile/', views.profile , name='profile' ),

    path('client/', views.client , name='client' ),
    path('client_profile/<int:client_id>/', views.client_profile, name='client_profile'),

    path('edit_client/<int:client_id>/', views.edit_client, name='edit_client'),
    path('delete_client/<int:client_id>/', views.delete_client, name='delete_client'),
    path('add_client/', views.add_client, name='add_client'),


    path('upload/', views.upload_excel, name='upload_excel'),
    path('download_excel/', views.download_excel, name='download_excel'),
    path('collection/', views.collection , name='collection' ),
    

]
