from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.template.loader import render_to_string
from django.core.validators import validate_image_file_extension

from rendershot_django.utils import get_random_code
from rendershot_django.utils import post_message_to_slack


class TicketDepartments(models.TextChoices):
    SALES = 'sales', _('Sales')
    TECHNICAL = 'technical', _('Technical')


class TicketStatus(models.TextChoices):
    OPEN = 'open', _('Open')
    PENDING = 'pending', _('Pending')
    RESOLVED = 'resolved', _('Resolved')
    CLOSED = 'closed', _('Closed')
    WAITINGCUSTOMER = 'waiting_on_customer', _('Waiting On Customer')
    WAITINGADMIN = 'waiting_on_admin', _('Waiting On Admin')


class Ticket(models.Model):

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    number = models.CharField(max_length=20, null=True)
    department = models.CharField(max_length=100, null=True,
                                  choices=TicketDepartments.choices,
                                  default=TicketDepartments.TECHNICAL)
    status = models.CharField(max_length=100, null=True, choices=TicketStatus.choices, default=TicketStatus.OPEN)
    subject = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        if created:
            id_string = str(instance.id)
            random_str = get_random_code()
            instance.number = random_str + id_string
            instance.save()

    def __str__(self):
        return self.subject


post_save.connect(Ticket.post_create, sender=Ticket)


class TicketReply(models.Model):

    ticket = models.ForeignKey(Ticket, null=True, on_delete=models.CASCADE)
    author = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    body = models.TextField(null=True, max_length=5000)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']

    def __init__(self, *args, **kwargs):
        self.operator = 'web_admin'
        self.signals = {'on_new_reply': self.on_new_reply}
        super(TicketReply, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.author.username + " " + self.ticket.subject

    def save(self, *args, **kwargs):
        pre_save_model = TicketReply.objects.filter(pk=self.pk).first()
        if 'operator' in kwargs:
            self.operator = kwargs.pop('operator')
        super(TicketReply, self).save(*args, **kwargs)

        created = False
        if not pre_save_model and self:
            created = True

        # call signals
        new_reply_event = 'on_new_reply'
        new_reply_signal_func = self.signals.get(new_reply_event)
        if created and new_reply_signal_func:
            new_reply_signal_func(new_reply_event)

    def on_new_reply(self, event):
        if self.author.is_superuser:
            self.email_new_reply()
        self.slack_new_reply(event)

    def slack_new_reply(self, event):
        post_message_to_slack(event, event, {'user': self.author.username, 'reply': self.body}, 'ticket')

    def email_new_reply(self):
        from django.contrib.sites.models import Site
        current_site = Site.objects.get_current()
        site_name = current_site.name
        domain = current_site.domain

        context = {'subject': f'New Admin Message',
                   'description': f'New Message on {self.ticket.subject}',
                   'paragraph_01': f'{self.body}.',
                   'action_text': f'Show Message',
                   'action_url': reverse("tickets") + f"?ticket_number={self.ticket.number}",
                   'current_site': current_site,
                   'domain': domain, 'site_name': site_name,
                   'protocol': 'https', }

        html = render_to_string('email/job_update_email.html',
                                context=context)

        self.ticket.user.email_user(f'New Admin Message', self.ticket.subject, html_message=html)


class TicketAttachment(models.Model):

    reply = models.ForeignKey(TicketReply, null=True, on_delete=models.CASCADE)
    date_created = models.DateTimeField(default=timezone.now)
    attachment = models.ImageField(upload_to='images/%Y-%m-%d/',
                                   null=True,
                                   blank=True,
                                   validators=[validate_image_file_extension])

    def __str__(self):
        return self.attachment.name
