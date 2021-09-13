import logging
import ast
from pprint import pformat

from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404

from job.models import *
from job.serializers import *


class JobAPI(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super(JobAPI, self).__init__()
        self.log = logging.getLogger('JobAPI')

    def get_object(self, job_name):
        try:
            return Job.objects.get(name=job_name)
        except Job.DoesNotExist:
            raise Http404

    def get(self, request, *args, **kwargs):
        job = self.get_object(request.data.get('job_name', ''))
        serializer = JobSerializer(job)
        return Response(serializer.data)

    def build_frame_list(self, frames):
        if isinstance(frames, list):
            return frames
        elif isinstance(frames, str):
            frames = frames.split(',')
            return frames

    def post(self, request, *args, **kwargs):

        job_data = json.loads(request.data.get('data'))
        posted_system_info = job_data.get('System_Info')
        posted_plugin_info = job_data.get('Plugin_Info')
        posted_job_info = job_data.get('Job_Info')

        file_path = posted_system_info.get('link')
        file_name_with_ext = os.path.basename(file_path)
        file_name, ext = os.path.splitext(file_name_with_ext)

        software = Software.objects.filter(name=posted_system_info.get('render_soft')).first()
        version = SoftwareVersion.objects.filter(version=posted_system_info.get('keyshot_version'),
                                                 plugin_name='RBKeyshot').first()
        file_storage = FileStorage.objects.filter(name='RenderShare').first()

        # get and validate render plan
        render_plan = RenderPlan.objects.filter(pk=posted_system_info.get('render_plan')).first()
        unlimited_allowed = not self.request.user.profile.rate_multiplier
        if render_plan.name == 'unlimited' and not unlimited_allowed:
            self.log.warning(f'unlimited plan selected but not authorized : {render_plan.name} >> {unlimited_allowed}')
            render_plan = RenderPlan.objects.filter(name='animation_slow').first()
            self.log.debug(f'auto switching plan to {render_plan}')

        output_format = OutputFormat.objects.filter(extension=posted_system_info.get('output_format')).first()
        frame_list = self.build_frame_list(posted_job_info.get('Frames'))

        system_info = dict(plugin_name=version.plugin_name,
                           plugin_version=version.version,
                           render_plan=render_plan.name,
                           username=request.user.username,
                           output_format=output_format.extension,
                           storage_type=file_storage.name)

        job_info = dict(job_name=file_name,
                        job_type='',
                        chunk_size=request.user.profile.chunk_size_override,
                        machine_limit=render_plan.deadline_machine_limit,
                        priority=render_plan.deadline_priority,
                        pool=version.deadline_pool,
                        group=version.deadline_group,
                        frame_list=frame_list)

        plugin_info = {k: v for (k, v) in posted_plugin_info.items()}

        file_info = dict(file_name=file_name,
                         id='',
                         size='',
                         relative_url=file_path,
                         absolute_url='')

        job_schema = dict()
        job_schema['system_info'] = system_info
        job_schema['job_info'] = job_info
        job_schema['plugin_info'] = plugin_info
        job_schema['file_info'] = file_info

        initial = {
            'user': self.request.user,
            'name': file_name,
            'frame_list': frame_list,
            'render_plan': render_plan,
            'file_storage': file_storage,
            'output_format': output_format,
            'status': JobStatus.objects.filter(name='submitted').first(),
            'progress': float(),
            'software_version': version,
            'data': job_schema,
        }

        job = Job.objects.create(**initial)
        job.save(operator='api')

        serializer = JobSerializer(job)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        job = self.get_object(request.data.get('job_name', ''))

        data = request.data.dict()
        self.log.debug(pformat(data))

        self.log.debug(f"requested job found : {job.name}")
        if job.status == JobStatus.objects.filter(name='deleted').first():
            self.log.warning(f"job is already deleted, returning : {job.name} >> {job.status}")
            serializer = JobSerializer(job)
            return Response(serializer.data)

        new_status = data.get('status')
        if new_status in [status.name for status in JobStatus.objects.all()]:
            new_status_object = JobStatus.objects.filter(name=new_status).first()
            if job.status.name == 'deleted':
                self.log.debug(f"do not update status, job is deleted : {job.name} >> {job.status.name}")
            elif job.status.name == 'resuming' and not new_status_object.name == 'rendering':
                self.log.debug(f"rendering status expected {job.name} >> {new_status}")
                if new_status_object.name in ['failed', 'completed']:
                    job.status = new_status_object
                    self.log.debug(f"set new status : {job.name} >> {new_status}")
            elif job.status.name == 'suspending' and not new_status_object.name == 'suspended':
                self.log.debug(f"suspended status expected {job.name} >> {new_status}")
                if new_status_object.name in ['failed', 'completed']:
                    job.status = new_status_object
                    self.log.debug(f"set new status : {job.name} >> {new_status}")
            else:
                job.status = new_status_object
                self.log.debug(f"set new status : {job.name} >> {new_status}")

        new_progress = data.get('progress')
        if new_progress:
            job.progress = new_progress
            self.log.debug(f"set new progress : {job.name} >> {new_progress}")

        new_deadline_id = data.get('deadline_id')
        if new_deadline_id:
            job.deadline_id = new_deadline_id
            self.log.debug(f"set new deadline_id : {job.name} >> {new_deadline_id}")

        new_deadline_tasks_count = data.get('tasks_count')
        if new_deadline_tasks_count and int(new_deadline_tasks_count) != int(job.deadline_tasks_count):
            job.jobtask_set.all().delete()
            job.cost = float()
            self.log.debug(f"tasks discrepancy triggered : {job.deadline_tasks_count} >> {new_deadline_tasks_count}")

        if new_deadline_tasks_count:
            job.deadline_tasks_count = new_deadline_tasks_count
            self.log.debug(f"set new deadline_tasks_count : {job.name} >> {new_deadline_tasks_count}")

        new_errors = data.get('errors')
        if new_errors:
            add_errors = []
            new_errors = json.loads(data.get('errors'))
            self.log.debug(f"list of errors sent : {pformat(new_errors)}")
            for error_id, error_message in new_errors.items():
                # ultimately we need to filter this per software
                for error in JobError.objects.all():
                    if error.error in error_message:
                        add_errors.append(error)
                        self.log.info(f'job error found {error.error}.')

            if add_errors:
                self.log.info(f'adding {len(add_errors)} to job.')
                job.error.add(*add_errors)

        new_tasks = data.get('tasks')
        if new_tasks:
            total_cost = float()
            new_tasks = json.loads(data.get('tasks'))
            for task_id, task_data in new_tasks.items():
                task_id = int(task_id)
                new_cpu_usage = task_data.get('cpu_usage')
                new_frame_list = task_data.get('frame_list')

                new_render_time = float(task_data.get('render_time'))
                # exception handling for bad render time data from deadline
                if new_render_time > 2000:
                    self.log.debug(f"bad deadline render time report : {job.name} >> {new_render_time}")
                    continue

                new_render_time_string = task_data.get('render_time_string')
                new_cost = new_render_time * job.render_plan.rate_per_min
                total_cost += new_cost

                exist_task = job.jobtask_set.filter(deadline_task_id=task_id).first()
                if exist_task:
                    exist_task.cost = new_cost
                    exist_task.cpu_usage = new_cpu_usage
                    exist_task.frame_list = new_frame_list
                    exist_task.render_time = new_render_time
                    exist_task.render_time_string = new_render_time_string

                    exist_task.save()
                else:
                    initial = {'job': job,
                               'deadline_task_id': task_id,
                               'cost': new_cost,
                               'cpu_usage': new_cpu_usage,
                               'frame_list': new_frame_list,
                               'render_time': new_render_time,
                               'render_time_string': new_render_time_string}

                    new_task = JobTask.objects.create(**initial)
                    new_task.save()

            if int(new_deadline_tasks_count) == 1:
                job_current_cost = float()
            else:
                job_current_cost = job.cost

            if job.is_gpu:
                total_cost = total_cost * 3

            job.cost = job_current_cost + total_cost

        # suspend job if user balance is not positive
        user_balance = job.user.profile.balance
        if 0 > job.user.profile.balance and not job.status.name == 'deleted':
            job.status = JobStatus.objects.filter(name='suspended').first()
            self.log.debug(f"suspended job  for negative credit : {job.name} >> {job.status} >> {user_balance}")

        job.save(operator='api')
        serializer = JobSerializer(job)
        return Response(serializer.data)


class SubmitSessionAPI(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response({})

    def post(self, request, *args, **kwargs):

        logging.info(f"{type(request.data['data'])} : {request.data['data']}")

        data = {}
        try:
            data = json.loads(str(request.data['data']))
        except Exception as err:
            logging.error(f"could not load session data with json : {err}")

        if not data:
            try:
                data = ast.literal_eval(str(request.data['data']))
            except Exception as err:
                logging.error(f"could not load session data with ast : {err}")

        if not data:
            try:
                data = eval(str(request.data['data']))
            except Exception as err:
                logging.error(f"could not load session data with eval : {err}")

        if not data:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        submit_session = SubmitSession.objects.create(user=request.user, data=data)
        submit_session.save()

        serializer = SubmitSessionSerializer(submit_session)
        return Response(serializer.data)
