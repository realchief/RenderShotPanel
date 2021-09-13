from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.http import JsonResponse
from django.urls import reverse

from users.decorators import blocked_validation
from .forms import TicketForm
from .models import Ticket, TicketReply, TicketAttachment, TicketStatus


from django.template.loader import render_to_string


class TicketView(View):

    template_name = 'ticketing/tickets.html'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def close_ticket(self, selected_ticket):

        selected_ticket.status = TicketStatus.CLOSED
        selected_ticket.save()
        messages.error(self.request, "Requested ticket is closed.")

        return selected_ticket

    def get(self, request, *args, **kwargs):
        tickets = Ticket.objects.order_by('-date_modified').filter(user=request.user)

        ticket_number = self.request.GET.get('ticket_number', '')
        selected_ticket = Ticket.objects.filter(number=ticket_number).first()

        close_ticket = self.request.GET.get('close', '')
        if close_ticket:
            selected_ticket = self.close_ticket(selected_ticket)

        ticket_form = TicketForm()
        return render(self.request, template_name=self.template_name, context={'tickets': tickets,
                                                                               'selected_ticket': selected_ticket,
                                                                               'ticket_form': ticket_form})

    def post(self, request, *args, **kwargs):
        ticket = Ticket.objects.filter(user=request.user, number=request.POST.get('ticket_number')).first()

        if not ticket:
            messages.error(self.request, 'Reply submission failed.')
            return redirect('tickets')

        for file in request.FILES.getlist('attachment'):
            if file.size > 5242880:
                messages.error(self.request, f'Attachment size limit of 5 MB is exceeded : {file.name} .')
                return redirect('tickets')

        new_reply = TicketReply.objects.create(ticket=ticket, author=request.user, body=request.POST.get('body'))
        if not new_reply:
            messages.error(self.request, 'Reply submission failed.')
            return redirect('tickets')

        ticket.status = TicketStatus.WAITINGADMIN
        ticket.save()
        new_reply.save(operator='web_user')

        for file in request.FILES.getlist('attachment'):
            attachment = TicketAttachment.objects.create(reply=new_reply, attachment=file)
            attachment.save()

        messages.success(self.request, 'Your request is successfully submitted, '
                                       'we will get in touch with you as soon as we can.')
        return redirect(f"{reverse('tickets')}?ticket_number={ticket.number}")

    @staticmethod
    def get_ticket_replies(request, *args, **kwargs):
        ticket_number = request.GET.get('ticket_number', None)
        ticket = Ticket.objects.filter(number=ticket_number).first()
        data = {'html_content': ''}

        if not ticket.user == request.user:
            return JsonResponse(data)

        ticket_form = TicketForm()
        html = render_to_string('ticketing/reply_content.html',
                                request=request,
                                context={'selected_ticket': ticket, 'ticket_form': ticket_form})
        data = {'html_content': html}
        return JsonResponse(data)


class NewTicketView(View):

    template_name = 'ticketing/new_ticket.html'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        # this sets initial subject for create report bug
        initial = {}
        if request.GET.get('subject', ""):
            initial['subject'] = request.GET.get('subject')
        ticket_form = TicketForm(initial=initial)

        return render(self.request,
                      template_name=self.template_name,
                      context={'ticket_form': ticket_form})

    def post(self, request, *args, **kwargs):

        ticket = Ticket.objects.create(user=request.user,
                                       department=request.POST.get('department'),
                                       subject=request.POST.get('subject'))
        if not ticket:
            messages.error(self.request, 'Ticket submission failed.')
            return redirect('new_ticket')

        for file in request.FILES.getlist('attachment'):
            if file.size > 5242880:
                messages.error(self.request, f'Attachment size limit of 5 MB is exceeded : {file.name} .')
                return redirect('new_ticket')

        if ticket.ticketreply_set.all():
            ticket.status = TicketStatus.WAITINGADMIN
        ticket.save()

        ticket_reply = TicketReply.objects.create(ticket=ticket, author=request.user, body=request.POST.get('body'))
        if not ticket_reply:
            messages.error(self.request, 'Ticket submission failed.')
            return redirect('new_ticket')

        ticket_reply.save(operator='web_user')

        for file in request.FILES.getlist('attachment'):
            attachment = TicketAttachment.objects.create(reply=ticket_reply, attachment=file)
            attachment.save()

        messages.success(self.request, 'Your request is successfully submitted, '
                                       'we will get in touch with you as soon as we can.')
        return redirect(f"{reverse('tickets')}?ticket_number={ticket.number}")
