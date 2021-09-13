import os
import json
import uuid

from django.urls import reverse
from django.template.loader import render_to_string
from django.forms.models import model_to_dict
from django.db import models
from django.db.models.signals import post_save, pre_delete, pre_save
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext_lazy as _

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from job import utils as job_utils
from payment.models import *
from system.models import SocketConnection
from rendershot_django.utils import post_message_to_slack


channel_layer = get_channel_layer()


class SoftwareVersionStatus(models.TextChoices):
    API = 'API', _('API')
    WEBANDAPI = 'web_and_api', _('Web and API')


class JobStatus(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)
    display_name = models.CharField(max_length=50, null=True, blank=True)
    admin_only = models.BooleanField(default=False, null=True)
    description = models.CharField(max_length=500, null=True, blank=True)
    is_suspendable = models.BooleanField(default=False, null=True)
    is_deletable = models.BooleanField(default=False, null=True)
    is_upgradable = models.BooleanField(default=False, null=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.display_name


class OutputFormat(models.Model):

    extension = models.CharField(max_length=10, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.extension


class FileFormat(models.Model):

    extension = models.CharField(max_length=10, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.extension


class RenderPlan(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)
    display_name = models.CharField(max_length=200, null=True, blank=True)
    rate_per_min = models.FloatField(default=0.0, null=True, blank=True)
    deadline_machine_limit = models.IntegerField(default=0, null=True)
    deadline_priority = models.IntegerField(default=1, null=True)
    admin_only = models.BooleanField(default=False, null=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.display_name


class FileStorage(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)
    setting = models.JSONField(max_length=5000, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.name


class Software(models.Model):

    name = models.CharField(max_length=50, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.name


class SoftwareVersion(models.Model):

    software = models.ForeignKey(Software, null=True, blank=True, on_delete=models.CASCADE)
    icon = models.FileField('Icon', upload_to='software/', blank=True,
                            null=True, default=f'/software/keyshot_logo.svg')
    version = models.CharField(max_length=50, null=True, blank=True)
    plugin_name = models.CharField(max_length=50, null=True, blank=True)
    file_format = models.ManyToManyField(FileFormat)
    output_format = models.ManyToManyField(OutputFormat)
    render_plan = models.ManyToManyField(RenderPlan)
    file_storage = models.ManyToManyField(FileStorage)
    access_type = models.CharField(max_length=100, null=True,
                                   choices=SoftwareVersionStatus.choices,
                                   default=SoftwareVersionStatus.WEBANDAPI)
    deadline_pool = models.CharField(max_length=50, null=True, blank=True)
    deadline_group = models.CharField(max_length=50, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.version

    @property
    def output_formats(self):
        return self.output_format.all()

    @property
    def render_plans(self):
        return self.render_plan.exclude(admin_only=True).order_by('display_name')

    @property
    def file_formats(self):
        return self.file_format.all()

    @property
    def file_storages(self):
        return self.file_storage.all()


class JobError(models.Model):
    software = models.ForeignKey(Software, null=True, blank=True, on_delete=models.RESTRICT)
    error = models.CharField(max_length=500, null=True, blank=True)
    title = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(max_length=2000, null=True, blank=True)
    solution = models.TextField(max_length=2000, null=True, blank=True)

    @classmethod
    def post_create(cls, sender, instance, created, *args, **kwargs):
        pass

    def __str__(self):
        return self.error


class Job(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True, blank=True)
    frame_list = ArrayField(models.CharField(max_length=50, blank=True, null=True))
    render_plan = models.ForeignKey(RenderPlan, null=True, blank=True, on_delete=models.RESTRICT)
    file_storage = models.ForeignKey(FileStorage, null=True, blank=True, on_delete=models.RESTRICT)
    output_format = models.ForeignKey(OutputFormat, null=True, blank=True, on_delete=models.RESTRICT)
    status = models.ForeignKey(JobStatus, null=True, blank=True, on_delete=models.RESTRICT)
    progress = models.FloatField(default=0.0, null=True, blank=True)
    software_version = models.ForeignKey(SoftwareVersion, null=True, blank=True, on_delete=models.RESTRICT)
    deadline_id = models.CharField(max_length=200, null=True, blank=True)
    data = models.JSONField(max_length=10000, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    deadline_tasks_count = models.IntegerField(default=0, null=True)
    cost = models.FloatField(default=0.0, null=True, blank=True)
    error = models.ManyToManyField(JobError, blank=True)

    def __init__(self, *args, **kwargs):
        self.operator = 'web_admin'
        self.status_signals = {'on_suspended': self.on_suspended,
                               'on_suspending': self.on_suspending,
                               'on_completed': self.on_completed,
                               'on_failed': self.on_failed,
                               'on_deleted': self.on_deleted,
                               'on_submitted': self.on_submitted,
                               'on_rendering': self.on_rendering,
                               'on_resuming': self.on_resuming,
                               }

        self.plan_signals = {'on_plan_changed': self.on_plan_changed,
                             }

        super(Job, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        pre_save_model = Job.objects.filter(pk=self.pk).first()

        if 'operator' in kwargs:
            self.operator = kwargs.pop('operator')

        super(Job, self).save(*args, **kwargs)

        call_status_signals = False
        call_plan_signals = False

        if not pre_save_model and self.status.name == 'submitted':
            call_status_signals = True
            self.user_socket_job_update('add_job')
        else:
            self.user_socket_job_update('update_job')

        if pre_save_model and pre_save_model.status.name != self.status.name:
            call_status_signals = True

        if call_status_signals:
            status_signal = self.status_signals.get(f'on_{self.status.name}', None)
            status_signal and status_signal()

        if pre_save_model and pre_save_model.render_plan.name != self.render_plan.name:
            call_plan_signals = True

        if call_plan_signals:
            plan_signal = self.plan_signals.get('on_plan_changed', None)
            plan_signal and plan_signal()

    @property
    def user_profile(self):
        return self.user.profile

    @classmethod
    def pre_save(cls, sender, instance, created=None, **kwargs):
        if created:
            return

        job_data = instance.data
        if job_data.get('session_id'):
            pass
        else:
            job_data['system_info']['plugin_name'] = instance.software_version.plugin_name
            job_data['system_info']['plugin_version'] = instance.software_version.version
            job_data['system_info']['render_plan'] = instance.render_plan.name
            job_data['system_info']['username'] = instance.user.username
            job_data['system_info']['output_format'] = instance.output_format.extension
            job_data['system_info']['storage_type'] = instance.file_storage.name
        instance.data = job_data

    @property
    def frames_count(self):
        tasks = self.jobtask_set.all()
        frames = 0
        for task in tasks:
            frames += len(eval(task.frame_list))

        return frames

    def count_by_status(self, status):
        return len(self.objects.filter(status=status))

    @property
    def count_rendering(self):
        return len(self.objects.filter(status=JobStatus.objects.filter(name='rendering').first()))

    @property
    def count_all(self):
        return len(self._meta.model.objects.all())

    @property
    def get_frame_list_display(self):
        if len(self.frame_list) > 1:
            return "Multiple Range"
        else:
            frame_list = ",".join(self.frame_list)
        return frame_list

    @property
    def image_width(self):
        render_width = self.data.get('image_width')
        if render_width:
            return render_width

        plugin_info = self.data.get('plugin_info')
        if not plugin_info:
            return

        image_width = plugin_info.get('image_width')
        if image_width:
            return image_width

        render_width = plugin_info.get('render_width')
        if render_width:
            return render_width

    @property
    def output_format_display(self):
        output_format = self.output_format
        if output_format:
            return output_format.extension

        formats = {2: 'EXR',
                   0: 'JPEG',
                   5: 'PNG',
                   8: 'PSD16',
                   7: 'PSD32',
                   6: 'PSD8',
                   3: 'TIFF32',
                   1: 'TIFF8'}

        output_format_index = self.data.get('output_format')
        if output_format_index is not None:
            return formats[int(output_format_index)]

    @property
    def image_height(self):
        render_height = self.data.get('image_height')
        if render_height:
            return render_height

        plugin_info = self.data.get('plugin_info')
        if not plugin_info:
            return

        image_height = plugin_info.get('image_height')
        if image_height:
            return image_height

        render_height = plugin_info.get('render_height')
        if render_height:
            return render_height

    @property
    def cameras(self):
        plugin_info = self.data.get('plugin_info')
        if not plugin_info:
            return

        cameras = plugin_info.get('cameras')
        if cameras:
            return cameras

    @property
    def render_engine(self):
        if not self.data.get('session_id'):
            return 'CPU'

        render_engine = self.data.get('render_engine')
        if render_engine in [0, '0']:
            return 'CPU (Product Mode)'
        elif render_engine in [1, '1']:
            return 'CPU (Interior Mode)'
        elif render_engine in [3, '3']:
            return 'GPU (Product Mode)'
        elif render_engine in [4, '4']:
            return 'GPU (Interior Mode)'

        return 'CPU'

    @property
    def is_gpu(self):
        if not self.data.get('session_id'):
            return False

        render_engine = self.data.get('render_engine')
        if not render_engine:
            return False

        if render_engine in [3, '3']:
            return True
        elif render_engine in [4, '4']:
            return True

        return False

    @property
    def session_id(self):
        return self.data.get('session_id', '')

    def on_suspended(self):
        if not self.operator == 'web_user':
            self.email_job_update()
        self.admin_socket_job_update(self.on_suspended.__name__)
        self.slack_job_update(self.on_suspended.__name__)

    def on_suspending(self):
        self.admin_socket_job_update(self.on_suspended.__name__)
        self.slack_job_update(self.on_suspending.__name__)

    def on_completed(self):
        self.email_job_update()
        self.slack_job_update(self.on_completed.__name__)

    def on_failed(self):
        # reset job cost on failed
        self.cost = float()
        self.save()

        self.email_job_update()
        self.slack_job_update(self.on_failed.__name__)

    def on_deleted(self):
        self.user_socket_job_update('delete_job')
        self.admin_socket_job_update(self.on_deleted.__name__)

    def on_rendering(self):
        pass

    def on_resuming(self):
        self.admin_socket_job_update(self.on_rendering.__name__)

    def on_submitted(self):
        # set job unique id
        job_data = self.data
        id_string = str(self.id)
        job_name = os.path.splitext(self.name)[0]
        self.name = "_".join([job_name, id_string])

        if job_data.get('session_id'):
            pass
        else:
            job_data['job_info']['job_name'] = job_name

        self.save()

        if self.data.get('session_id'):
            event = 'on_job_v2_submitted'
        else:
            event = self.on_submitted.__name__

        self.admin_socket_job_update(event)
        self.slack_job_update(event)

    def on_plan_changed(self):
        self.admin_socket_job_update(self.on_plan_changed.__name__)
        self.slack_job_update(self.on_plan_changed.__name__)

    def email_job_update(self):
        if self.user.profile.receive_job_email_notifs:
            from django.contrib.sites.models import Site
            current_site = Site.objects.get_current()
            site_name = current_site.name
            domain = current_site.domain

            context = {'subject': f'Job Update : {self.name}',
                       'description': f'New Update on {self.name}',
                       'paragraph_01': f'Your job {self.name} is {self.status.display_name}.',
                       'action_text': f'Job List',
                       'action_url': reverse("job_list"),
                       'current_site': current_site,
                       'domain': domain, 'site_name': site_name,
                       'protocol': 'https', }

            html = render_to_string('email/job_update_email.html',
                                    context=context)

            self.user.email_user(f'Update {self.name} is {self.status.display_name}',
                                 self.name, html_message=html)

    def slack_job_update(self, event):

        data = {}
        if self.data.get('session_id'):
            data.update({'user': self.user.username,
                         'name': self.name,
                         'frame_list': self.data['frame_list'],
                         'image_width': self.data['image_width'],
                         'image_height': self.data['image_height'],
                         'render_plan': self.data['render_plan'],
                         'session_id': self.data['session_id'],
                         })
        else:
            data.update({'user': self.user.username,
                         'name': self.name,
                         'frame_list': self.frame_list,
                         'render_plan': self.render_plan.display_name,
                         'file_storage': self.file_storage.name,
                         'output_format': self.output_format.extension,
                         'software': self.software_version.software.name,
                         'software_version': self.software_version.version})

        post_message_to_slack(event, event, data)

    def user_socket_job_update(self, event):
        socket_conn = SocketConnection.objects.filter(user=self.user, group='jobs')
        html = render_to_string('job/widgets/job_item.html', context={'job': self})
        data = {'type': 'send_message', 'action': event, 'job_id': self.id, 'html': html}
        for conn in socket_conn:
            async_to_sync(channel_layer.send)(conn.channel, data)

    def admin_socket_job_update(self, event):
        # remap job data to human readable values

        if self.data.get('session_id'):
            job_data = self.data

            # add extra job data from related models
            job_data['name'] = self.name
            job_data['user'] = self.user.username
            job_data['software_version'] = self.software_version.version
            job_data['group'] = self.software_version.deadline_group
            job_data['chunk_size'] = self.user.profile.chunk_size_override
            job_data['render_plan'] = self.render_plan.name
            job_data['machine_limit'] = self.render_plan.deadline_machine_limit
            job_data['priority'] = self.render_plan.deadline_priority
            job_data['deadline_id'] = self.deadline_id
            job_data['frame_list'] = self.frame_list

        else:
            job_data = model_to_dict(self)
            job_data['user'] = self.user.username
            job_data['status'] = self.status.name
            job_data['software_version'] = self.software_version.version
            job_data['render_plan'] = self.render_plan.name
            job_data['deadline_machine_limit'] = self.render_plan.deadline_machine_limit
            job_data['deadline_priority'] = self.render_plan.deadline_priority
            job_data['output_format'] = self.output_format.extension
            job_data['file_storage'] = self.file_storage.name

        # send to local farm and admin clients
        async_to_sync(channel_layer.group_send)('admin', {'type': 'send_message', 'action': event, 'data': job_data})

        if self.data.get('session_data') and self.data.get('session_data').get('file_data'):
            return

        if self.data.get('session_id') and event == 'on_job_v2_submitted':
            socket_conn = SocketConnection.objects.filter(user=self.user, group='client')
            data = {'type': 'send_message', 'event': 'job_session_submitted',
                    'data': {'username': self.user.username, 'session_id': self.data['session_id'],
                             'job_name': self.name, 'file_path': self.data.get('session_data').get('package_path')}}

            for conn in socket_conn:
                async_to_sync(channel_layer.send)(conn.channel, data)

            post_message_to_slack('on_job_session_submitted', 'job_session_submitted', data.get('data'))

    def resubmit(self):
        if self.data.get('session_id'):
            event = 'on_job_v2_submitted'
        else:
            event = self.on_submitted.__name__
        self.admin_socket_job_update(event)
        self.slack_job_update(event)

    def refund(self):
        entry = Payment.objects.create(user=self.user,
                                       amount=self.cost,
                                       status=PaymentStatus.COMPLETED,
                                       payment_id=self.name,
                                       type=PaymentTypes.CREDIT_REFUND)
        entry.save()

    def cost_balance(self, amount):
        if not amount:
            return

        entry = Payment.objects.create(user=self.user,
                                       amount=amount,
                                       status=PaymentStatus.COMPLETED,
                                       payment_id=self.name,
                                       type=PaymentTypes.COST_BALANCE)
        entry.save()


pre_save.connect(Job.pre_save, sender=Job)


class JobTask(models.Model):
    job = models.ForeignKey(Job, null=True, on_delete=models.CASCADE)
    cost = models.FloatField(default=0.0, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    cpu_usage = models.FloatField(default=0.0, null=True, blank=True)
    frame_list = models.CharField(max_length=3000, null=True, blank=True)
    render_time = models.FloatField(default=0.0, null=True, blank=True)
    render_time_string = models.CharField(max_length=200, null=True, blank=True)
    deadline_task_id = models.IntegerField(default=0, null=True)

    def __str__(self):
        return f"Task {self.id}"

    def frame_list_display(self):
        return job_utils.list_to_range(self.frame_list) or self.frame_list


class SubmitSession(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    session_id = models.UUIDField(default=uuid.uuid4, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} : {self.session_id}"
