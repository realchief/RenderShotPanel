import os
import secrets
import string
import requests
import json
import pprint

from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import get_formatter_by_name


def get_random_code(lenght=5):
    random_str = ''.join((secrets.choice(string.ascii_letters) for i in range(lenght)))
    return random_str


def reformat_json(instance):
    response = json.dumps(instance.data, sort_keys=True, indent=2)
    formatter = get_formatter_by_name('html')
    response = highlight(response, get_lexer_by_name('json'), formatter)
    style = "<style>" + formatter.get_style_defs() + "</style><br>"
    return mark_safe(style + response)


def formatted_data(data):
    output = ''
    for key, value in data.items():
        if not isinstance(value, dict):
            output += f"{key} : {value}\n"

    return output


def post_message_to_slack(popup_text, subject, data, model_type=None):
    if model_type and model_type == 'ticket':
        slack_channel = '#rendershot_ticket'
    else:
        slack_channel = '#rendershot_notification'

    slack_token = os.getenv('SLACK_TOKEN', '')
    if not slack_token:
        return

    slack_icon_url = 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTuGqps7ZafuzUsViFGIremEL2a3NR0KO0s0RTCMXmzmREJd5m4MA&s'
    slack_user_name = os.getenv('SLACK_USER_NAME')

    blocks = [{"type": "divider"},
              {"type": "section",
               "text": {"type": "mrkdwn",
                        "text": f"*{subject}*\n{formatted_data(data)}"}},]

    request = requests.post('https://slack.com/api/chat.postMessage',
                            {'token': slack_token,
                             'channel': slack_channel,
                             'text': popup_text,
                             'icon_url': slack_icon_url,
                             'username': slack_user_name,
                             'blocks': json.dumps(blocks) if blocks else None})


def send_update_email(user, context, subject, message):
    from django.contrib.sites.models import Site
    current_site = Site.objects.get_current()
    site_name = current_site.name
    domain = current_site.domain

    context.update({'current_site': current_site,
                    'domain': domain,
                    'site_name': site_name,
                    'protocol': 'https', })

    html = render_to_string('email/job_update_email.html', context=context)
    user.email_user(subject, message, html_message=html)
