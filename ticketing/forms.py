from django import forms
from django.utils.translation import gettext, gettext_lazy as _

from .models import TicketDepartments


class TicketForm(forms.Form):
    department = forms.ChoiceField(label=_("Department"),
                                   choices=TicketDepartments.choices,
                                   widget=forms.Select(
                                   attrs={'autocapitalize': 'none',
                                          'autocomplete': 'department',
                                          'class': "form-control",
                                          'id': '"exampleFormControlSelect1"'})
                                   )

    subject = forms.CharField(label=_("Subject"),
                              strip=False,
                              widget=forms.TextInput(
                              attrs={'autocapitalize': 'none',
                                     'autocomplete': 'subject',
                                     'class': "form-control",
                                     'placeholder': 'Ticket Subject',
                                     'id': 'subject'}))

    body = forms.CharField(widget=forms.Textarea(attrs={'id': 'exampleFormControlTextarea1',
                                                        'rows': 3,
                                                        'placeholder': 'Message',
                                                        'class': "form-control"}))

    attachment = forms.ImageField(label='attachment',
                                  required=False,
                                  widget=forms.ClearableFileInput(attrs={'multiple': True,
                                                                         'class': "custom-file-input",
                                                                         'id': "inputGroupFile01",
                                                                         'aria-describedby': "inputGroupFileAddon01"}))






