import os
import json
import logging

from django.http import FileResponse
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

from system.serializers import *
from system.models import SystemStatus
from system.dbx_utils import DropboxHandler
from system.utils import get_system_setting

from job.models import RenderPlan


class CalculateCost(APIView):

    def get(self, request, *args, **kwargs):

        logging.debug(request.GET)

        frames = request.GET.get('frames', None)
        try:
            frames = eval(frames)
        except:
            frames = frames

        render_time_per_frame = request.GET.get('rendertime', None)
        try:
            render_time_per_frame = eval(render_time_per_frame)
        except:
            render_time_per_frame = render_time_per_frame

        ghz = request.GET.get('ghz', None)
        try:
            ghz = eval(ghz)
        except:
            ghz = ghz

        cores = request.GET.get('cores', None)
        try:
            cores = eval(cores)
        except:
            cores = cores

        cpu_number = request.GET.get('cpu', None)
        try:
            cpu_number = eval(cpu_number)
        except:
            cpu_number = cpu_number

        errors = []
        if not frames or not isinstance(frames, int):
            errors.append(f"Frames number should be an integer value.")

        if not render_time_per_frame or not isinstance(render_time_per_frame, (int, float)):
            errors.append(f"Render time per frame should be an integer or float value.")

        if not ghz or not isinstance(ghz, (int, float)):
            errors.append(f"CPU frequency (GHZ) per core should be an integer or float value.")

        if not cores or not isinstance(cores, int):
            errors.append(f"CPU cores number should be an integer value.")

        if not cpu_number or not isinstance(cpu_number, int):
            errors.append(f"CPU sockets number should be an integer value.")

        calculate_data = {}
        if not errors:
            total_ghz = ghz * cores * cpu_number
            total_time_on_user_machine = frames * render_time_per_frame

            power_unit = 100 / total_ghz
            time_on_single_farm_machine = total_time_on_user_machine / power_unit

            render_plans = RenderPlan.objects.all().exclude(admin_only=True)

            for render_plan in render_plans:
                calculate_data[render_plan.display_name] = time_on_single_farm_machine * render_plan.rate_per_min

        html = render_to_string('system/calculate_cost_template.html',
                                context={"calculate_data": calculate_data, 'errors': errors})

        data = {'html': html}

        response = HttpResponse(json.dumps(data), content_type="application/json")
        response["Access-Control-Allow-Origin"] = '*'
        response["Access-Control-Allow-Methods"] = 'GET,PUT, OPTIONS'
        response["Access-Control-Max-Age"] = '1000'
        response["Access-Control-Allow-Headers"] = 'X-Requested-With, Content-Type'
        return response


class System(APIView):

    def get(self, request):
        setting = get_system_setting()
        setting_serializer = SystemStatusSerializer(setting)

        data = {'status': setting_serializer.data.get('system_status')}
        return Response(data)

    def post(self, request, *args, **kwargs):
        setting = get_system_setting()
        system_status = request.data.get('status')

        status_dict = {'online': SystemStatus.ONLINE,
                       'offline': SystemStatus.OFFLINE,
                       'maintenance': SystemStatus.MAINTENANCE}
        if system_status and system_status in SystemStatus.values:
            status_value = status_dict.get(system_status)
            if status_value:
                setting.system_status = status_value
                setting.save()

        setting_serializer = SystemStatusSerializer(setting)
        data = {'status': setting_serializer.data.get('system_status')}
        return Response(data)


class Dropbox(APIView):

    def get(self, request):
        dbx = FileStorage.objects.filter(name="RenderShare").first()
        dbx_serializer = FileStorageSerializer(dbx)

        data = {'settings': dbx_serializer.data.get('setting')}
        return Response(data)


class RenderShare(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        data = dict()
        admin = User.objects.filter(username='admin', is_superuser=True).first()
        dbx = DropboxHandler(request.user or admin)
        data.update(dbx.get_rendershare_installers(package_type='installer', os_type='win'))
        data.update(dbx.get_rendershare_installers(package_type='updater', os_type='win'))
        data.update(dbx.get_rendershare_installers(package_type='installer', os_type='mac'))
        data.update(dbx.get_rendershare_installers(package_type='updater', os_type='mac'))

        setting = get_system_setting()
        setting_serializer = ClientAppSettingSerializer(setting)
        data['settings'] = setting_serializer.data.get('client_app_setting') or dict()

        return Response(data)


class URLsAPI(APIView):

    def get(self, request, *args, **kwargs):
        current_site = get_current_site(request)
        job_list_url = reverse("job_list")

        return Response({'job_list_url': 'https://' + current_site.domain + job_list_url})


class LogAPI(APIView):

    authentication_classes = [authentication.TokenAuthentication]

    def post(self, request, *args, **kwargs):
        level = request.data.get('level')
        message = request.data.get('message')
        username = request.user.username or 'rendershare_admin'
        base_dir = getattr(settings, "BASE_DIR", '')

        logger = logging.getLogger(username)
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(os.path.join(base_dir, f"logs/rendershare/{username}.log"))
            formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s")

            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger_call = {"DEBUG": logger.debug,
                       "INFO": logger.info,
                       "WARNING": logger.warning,
                       "ERROR": logger.error,
                       }
        caller = logger_call.get(level, None)
        if not caller:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)

        caller(message)
        return Response(status=status.HTTP_202_ACCEPTED)


class KeyShotSubmitterAPI(APIView):

    def get(self, request, *args, **kwargs):
        submitter_file = os.path.join(os.path.dirname(__file__), 'submitters/keyshot_submitter.py')
        submitter = open(submitter_file, 'rb')
        return FileResponse(submitter)
