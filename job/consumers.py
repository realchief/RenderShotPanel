import requests
import logging
import pprint

from channels.generic.websocket import WebsocketConsumer

from job.models import *
from job.forms import KeyShotJobForm
from job import utils as job_utils
from system.dbx_utils import DropboxHandler


class SocketMessage:
    _tags = 'alert '
    message = ''

    warning = "alert-warning alert-fade"
    error = "alert-danger alert-fade"
    info = "alert-info alert-fade"
    success = "alert-success alert-fade"

    def __str__(self):
        return self.message

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        self._tags += " ".join(tags)


def add_message(message, level):
    message_class = SocketMessage()
    message_class.tags = [level, ]
    message_class.message = message
    return message_class


def get_json_messages(messages):
    message_html = render_to_string('utils/messages.html', context={'messages': messages})
    message_data = {'action': 'show_messages', 'html': message_html}
    return json.dumps(message_data)


class JobsConsumer(WebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super(JobsConsumer, self).__init__()
        self.log = logging.getLogger('JobsSocket')
        self.group_name = 'jobs'
        self.actions = {'request_delete_jobs': self.request_delete_jobs,
                        'request_suspend_jobs': self.request_suspend_jobs,
                        'request_pause_resume': self.request_pause_resume,
                        'request_delete_job': self.request_delete_job,
                        'get_job_details': self.get_job_details,
                        'get_job_error_reports': self.get_job_error_reports,
                        'get_change_plan': self.get_change_plan,
                        'request_change_plan': self.request_change_plan,
                        'get_resubmit_job': self.get_resubmit_job,
                        'request_resubmit_job': self.request_resubmit_job,
                        'update_version_dependencies': self.update_version_dependencies,
                        'get_select_file_modal': self.get_select_file_modal}

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

        if self.scope['user'].is_anonymous:
            self.log.debug(f'anonymous user detected. closing socket.')
            self.send(text_data=json.dumps({'message': "Access token could not be validated."}))
            self.close(3001)
            return
        if not isinstance(self.scope['user'], User):
            self.log.debug(f'user is not a valid system User instance. closing socket.')
            self.send(text_data=json.dumps({'message': "Access token could not be validated."}))
            self.close(3001)
            return

        socket_conn = SocketConnection.objects.create(user=self.scope["user"],
                                                      channel=self.channel_name,
                                                      group=self.group_name)
        socket_conn.save()

        self.send(text_data=json.dumps({'message': 'connected'}))

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

        if isinstance(self.scope["user"], User):
            socket_conn = SocketConnection.objects.filter(user=self.scope["user"],
                                                          group=self.group_name,
                                                          channel=self.channel_name).first()
            if socket_conn:
                socket_conn.delete()

        self.send(text_data=json.dumps({'message': 'disconnected'}))

    def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        self.log.debug(pprint.pformat(data))
        action = self.actions.get(data.get('type', ''), '')
        if action:
            action(data)

    def send_message(self, event):
        self.send(text_data=json.dumps(event))

    def get_status(self, **kwargs):
        return JobStatus.objects.filter(**kwargs).first() or None

    def get_plan(self, **kwargs):
        return RenderPlan.objects.filter(**kwargs).first() or None

    def get_jobs(self, data, messages, invalid_status=None):
        jobs = []
        for item in data.get('jobs'):
            if not item:
                continue

            job = Job.objects.filter(user=self.scope["user"], name=item).first()
            if not job:
                messages.append(add_message(f'Job {item} is no longer exist.', SocketMessage.warning))
                continue

            if invalid_status and job.status == invalid_status:
                messages.append(add_message(f'Job is already {invalid_status.display_name}.', SocketMessage.warning))
                continue

            jobs.append(job)

        if not jobs:
            return self.send(text_data=get_json_messages(messages))

        return jobs

    def get_job(self, data):
        messages = []
        job_name = data.get('job_name', '')
        if not job_name:
            messages.append(add_message(f'Job {job_name} could not be found.', SocketMessage.error))
            return self.send(text_data=get_json_messages(messages))

        job = Job.objects.filter(name=job_name).first()
        if not job:
            messages.append(add_message(f'Job {job_name} is not exist.', SocketMessage.error))
            return self.send(text_data=get_json_messages(messages))

        return job

    def batch_change_plan(self, jobs, messages, target_plan):
        if not target_plan or not isinstance(target_plan, RenderPlan):
            return

        for job in jobs:
            if not job.status.is_upgradable:
                messages.append(add_message(f'Job {job.name} plan can not be changed at this point.',
                                            SocketMessage.warning))
            else:
                job.render_plan = target_plan
                job.save(operator='web_user')
                messages.append(add_message(f'Plan changed to {job.render_plan.display_name}.', SocketMessage.success))

    def batch_change_status(self, jobs, messages, target_status):
        if not target_status or not isinstance(target_status, JobStatus):
            return

        for job in jobs:
            if target_status == self.get_status(name='deleted') and not job.status.is_deletable:
                err_message = add_message(f'Job {job.name} can not be {target_status.display_name} at this point.',
                                          SocketMessage.warning)
                self.send(text_data=get_json_messages([err_message]))
                continue
            if target_status == self.get_status(name='suspending') and not job.status.is_suspendable:
                err_message = add_message(f'Job {job.name} can not be {target_status.display_name} at this point.',
                                          SocketMessage.warning)
                self.send(text_data=get_json_messages([err_message]))
                continue

            job.status = target_status
            job.save(operator='web_user')
            success_message = add_message(f'Job {job.name} is {target_status.display_name}.', SocketMessage.success)
            self.send(text_data=get_json_messages([success_message]))

    def batch_toggle_status(self, jobs, messages, base_status_list, target_status):
        for job in jobs:
            toggled = False
            new_status = job.status

            if job.status in base_status_list:
                job.status = target_status
                new_status = target_status
                toggled = True

            if toggled:
                job.save(operator='web_user')
                messages.append(add_message(f'Job {job.name} is {new_status.display_name}.', SocketMessage.success))

    def request_delete_jobs(self, data):
        messages = []
        target_status = self.get_status(name='deleted')
        jobs = self.get_jobs(data, messages, invalid_status=target_status)
        self.batch_change_status(jobs, messages, target_status)

        # return self.send(text_data=get_json_messages(messages))

    def request_suspend_jobs(self, data):
        messages = []
        target_status = self.get_status(name='suspending')
        jobs = self.get_jobs(data, messages, invalid_status=target_status)
        self.batch_change_status(jobs, messages, target_status)

        # return self.send(text_data=get_json_messages(messages))

    def request_pause_resume(self, data):
        messages = []
        jobs = self.get_jobs(data, messages)
        target_job = jobs[0]

        if target_job.status in JobStatus.objects.filter(is_suspendable=True):
            self.batch_change_status(jobs, messages, self.get_status(name='suspending'))
        elif target_job.status == self.get_status(name='suspended'):
            self.batch_change_status(jobs, messages, self.get_status(name='resuming'))

        # return self.send(text_data=get_json_messages(messages))

    def request_delete_job(self, data):
        return self.request_delete_jobs(data)

    def get_job_details(self, data):
        job = self.get_job(data)
        if not isinstance(job, Job):
            return

        tasks = job.jobtask_set.order_by('deadline_task_id').all()
        html = render_to_string('job/job_details_modal.html',
                                context={'job': job,
                                         'tasks': tasks})
        data = {'action': 'set_job_details', 'html': html}
        return self.send(text_data=json.dumps(data))

    def get_job_error_reports(self, data):
        job = self.get_job(data)
        if not isinstance(job, Job):
            return

        errors = job.error.all()
        html = render_to_string('job/job_error_modal.html',
                                context={'job': job,
                                         'errors': errors})
        data = {'action': 'set_job_error_reports', 'html': html}
        return self.send(text_data=json.dumps(data))

    def get_change_plan(self, data):
        job = self.get_job(data)
        if not isinstance(job, Job):
            return

        plans = []
        if job.data.get('session_data'):
            plans = RenderPlan.objects.filter(name__istartswith='v2')
        else:
            plans = job.software_version.render_plans

        html = render_to_string('job/change_plan_modal.html', context={'job': job, 'plans': plans})
        data = {'action': 'set_change_plan', 'html': html}
        return self.send(text_data=json.dumps(data))

    def request_change_plan(self, data):
        messages = []
        job = self.get_job(data)
        if not isinstance(job, Job):
            return
        target_plan = self.get_plan(display_name=data.get('plan_name', ''), pk=data.get('plan_id', ''))
        self.batch_change_plan([job, ], messages, target_plan)

        return self.send(text_data=get_json_messages(messages))

    def get_resubmit_job(self, data):
        job = self.get_job(data)
        if not isinstance(job, Job):
            return

        html = render_to_string('job/resubmit_job_modal.html', context={'job': job})
        data = {'action': 'set_resubmit_job', 'html': html}
        return self.send(text_data=json.dumps(data))

    def request_resubmit_job(self, data):
        self.log.debug(data)
        messages = []
        job = self.get_job(data)
        if not isinstance(job, Job):
            return

        frame_list = data.get('frame_list', '')
        frame_list_message = 'Entered frame list is not valid.'
        if not frame_list:
            messages.append(add_message(frame_list_message, SocketMessage.error))
            self.log.debug(f'{frame_list_message} >> {frame_list}')
            return self.send(text_data=get_json_messages(messages))

        result = job_utils.validate_frame_list(frame_list.split(","))
        if isinstance(result, str):
            messages.append(add_message(frame_list_message, SocketMessage.error))
            self.log.debug(f'{result} >> {frame_list}')
            return self.send(text_data=get_json_messages(messages))

        if job.file_storage.name.lower() == "dropbox":
            dbx_download_link = job.data.get('file_info').get('absolute_url')
            if not dbx_download_link:
                message = 'Source file download link is not valid.'
                messages.append(add_message(message, SocketMessage.error))
                self.log.debug(f'{message} >> {dbx_download_link}')
                return self.send(text_data=get_json_messages(messages))

            request_data = requests.head(dbx_download_link)
            if request_data.status_code != 200:
                message = 'Source file download link is expired.'
                messages.append(add_message(message, SocketMessage.error))
                self.log.debug(f'{message} >> {request_data.status_code}')
                return self.send(text_data=get_json_messages(messages))

        initial = {'user': self.scope["user"],
                   'name': job.data.get('file_info').get('file_name'),
                   'frame_list': [frame_list, ],
                   'render_plan': job.render_plan,
                   'file_storage': job.file_storage,
                   'output_format': job.output_format,
                   'status': JobStatus.objects.filter(name='submitted').first(),
                   'software_version': job.software_version,
                   'data': job.data
                   }
        new_job = Job.objects.create(**initial)
        new_job.save(operator='web_user')

        message = f'New job submitted {new_job.name}.'
        messages.append(add_message(message, SocketMessage.success))
        self.log.debug(f'{message} >> {new_job}')
        return self.send(text_data=get_json_messages(messages))

    def update_version_dependencies(self, data):
        data = data['data']
        keyshot_form = KeyShotJobForm()
        software = Software.objects.filter(name=data['software'])
        if not software:
            return
        software = software.first()
        version = software.softwareversion_set.filter(version=data['version'])
        if not version:
            return
        version = version.first()

        # update render plan
        keyshot_form.fields['render_plan'].queryset = version.render_plans
        render_plan_field = keyshot_form.fields['render_plan'].widget.render("render_plan", '')
        data['action'] = 'update_render_plan'
        data['data'] = render_plan_field
        self.send(text_data=json.dumps(data))

        # update output format
        keyshot_form.fields['output_format'].queryset = version.output_formats
        output_format_field = keyshot_form.fields['output_format'].widget.render("output_format", '')
        data['action'] = 'update_output_format'
        data['data'] = output_format_field
        self.send(text_data=json.dumps(data))

        # update file_storage
        keyshot_form.fields['file_storage'].queryset = version.file_storages
        file_storage_field = keyshot_form.fields['file_storage'].widget.render("file_storage", '')
        data['action'] = 'update_storage'
        data['data'] = file_storage_field
        self.send(text_data=json.dumps(data))

    def get_select_file_modal(self, data):

        dbx = DropboxHandler(self.scope["user"])
        user_files = dbx.get_list_of_source_files(['.ksp'])

        for file_meta in user_files:
            if isinstance(job_utils.validate_file_name(file_meta.name), str):
                file_meta.is_downloadable = False
            else:
                file_meta.is_downloadable = True

        html = render_to_string('job/select_file_modal.html', context={'user_files': reversed(user_files)})
        data = {'action': 'set_select_file_modal', 'html': html}
        return self.send(text_data=json.dumps(data))
