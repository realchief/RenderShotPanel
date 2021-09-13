from django import forms
from django.contrib import admin
from ticketing.models import *
import nested_admin


class TicketAttachmentInline(nested_admin.NestedStackedInline):
    model = TicketAttachment
    list_display = ['reply', 'attachment', 'date_created']
    extra = 1


class TicketReplyInline(nested_admin.NestedStackedInline):
    model = TicketReply
    extra = 1
    autocomplete_fields = ('author',)

    formfield_overrides = {models.TextField: {'widget': forms.Textarea(attrs={'spellcheck': 'true',
                                                                              'rows': 7,
                                                                              'cols': 100})}}
    inlines = [TicketAttachmentInline]


class TicketAdmin(nested_admin.NestedModelAdmin):
    list_display = ['subject', 'user', 'number', 'department', 'status',  'date_modified']
    readonly_fields = ['number']
    list_filter = ['status']
    inlines = [TicketReplyInline]


admin.site.register(Ticket, TicketAdmin)


