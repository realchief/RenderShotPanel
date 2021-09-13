from django.urls import path
from ticketing import views as ticket_views

urlpatterns = [
    path('tickets/', ticket_views.TicketView.as_view(), name='tickets'),
    path('tickets/get_ticket_replies/', ticket_views.TicketView.get_ticket_replies, name='get_ticket_replies'),
    path('tickets/new_ticket/', ticket_views.NewTicketView.as_view(), name='new_ticket'),
]