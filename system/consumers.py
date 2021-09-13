import logging
import pprint

from channels.generic.websocket import WebsocketConsumer

from job.models import *
from rendershot_django.utils import post_message_to_slack


class SystemConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(SystemConsumer, self).__init__()
        self.actions = {'set_deadline_ids': self.set_deadline_ids,
                        'set_new_status': self.set_new_status}

        self.group_name = ''
        self.log = logging.getLogger('SystemSocket')

    def connect(self):

        if self.scope['user'].is_superuser:
            self.group_name = 'admin'
        else:
            self.group_name = 'client'

        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

        if self.scope['user'].is_anonymous:
            self.log.debug(f'anonymous user detected. closing socket.')
            self.send(text_data=json.dumps({'message': "Access token could not be validated."}))
            self.close()
            return

        if not self.group_name:
            self.log.debug(f'invalid socket group detected. closing socket.')
            self.send(text_data=json.dumps({'message': "Connection could not be authenticated."}))
            self.close()
            return

        self.log.debug(f'creating socket connection database object : {self.scope["user"].username}')
        if not isinstance(self.scope["user"], User):
            self.log.debug(f'bad user instance detected : {self.scope["user"].username} - {type(self.scope["user"])}')
            self.send(text_data=json.dumps({'message': "User is not validated."}))
            self.close()
            return

        socket_conn = SocketConnection.objects.create(user=self.scope["user"],
                                                      channel=self.channel_name,
                                                      group=self.group_name)
        socket_conn.save()
        self.send(text_data=json.dumps({'message': f"{self.group_name} connected."}))
        if self.group_name == 'admin':
            post_message_to_slack('WebSocket Connection Triggered',
                                  f"{self.group_name} connected.",
                                  {'user': self.scope['user'].username})

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

        if isinstance(self.scope["user"], User):
            socket_conn = SocketConnection.objects.filter(user=self.scope["user"],
                                                          group=self.group_name,
                                                          channel=self.channel_name).first()
            if socket_conn:
                socket_conn.delete()
        self.send(text_data=json.dumps({'message': 'disconnected'}))
        if self.group_name == 'admin':
            post_message_to_slack('WebSocket Disconnection Triggered',
                                  f"{self.group_name} disconnected.",
                                  {'user': self.scope['user'].username})

    def receive(self, text_data=None, bytes_data=None):

        data = json.loads(text_data)
        self.log.debug(pprint.pformat(data))

        action = self.actions.get(data.get('type', ''), '')
        if action:
            action(data)

    def send_message(self, event):
        self.log.debug(pprint.pformat(event))
        # event.pop('type')
        if event.get('data'):
            formatted_data = json.dumps(event)
            self.send(text_data=formatted_data)

    def set_deadline_ids(self, data):
        job_name = data.get('job_name')
        ids = data.get('job_ids')

        job = Job.objects.filter(name=job_name).first()
        if not job:
            return
        if ids:
            job.deadline_id = ids
            job.save()

    def set_new_status(self, data):
        job_name = data.get('job_name')
        job = Job.objects.filter(name=job_name).first()

        if not job:
            return

        if job.status.name == 'deleted':
            return

        status_name = data.get('status')
        status = JobStatus.objects.filter(name=status_name).first()
        if not status:
            return

        job.status = status
        job.save()

