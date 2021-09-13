import os
import json

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import View, ListView, FormView
from django.http import JsonResponse
from django.urls import reverse
from django.template.loader import render_to_string

from job.models import *
from job.forms import *
from system.dbx_utils import DropboxHandler
from job import utils as job_utils

from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from users.decorators import blocked_validation


def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgb(hx):
    return int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)


class JobListView(ListView):
    model = Job
    paginate_by = 10
    context_object_name = 'jobs'
    template_name = 'job/job_list.html'
    ordering = '-date_created'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        deleted_status = JobStatus.objects.filter(name='deleted').first()
        self.queryset = Job.objects.filter(user=self.request.user).exclude(status=deleted_status)

        return super(JobListView, self).get_queryset()

    def get(self, request, *args, **kwargs):
        deleted_status = JobStatus.objects.filter(name='deleted').first()
        rendering_status = JobStatus.objects.filter(name='rendering').first()
        completed_status = JobStatus.objects.filter(name='completed').first()
        failed_status = JobStatus.objects.filter(name='failed').first()

        count_all = Job.objects.filter(user=self.request.user).exclude(status=deleted_status).count()
        count_rendering = Job.objects.filter(user=self.request.user, status=rendering_status).count()
        count_completed = Job.objects.filter(user=self.request.user, status=completed_status).count()
        count_failed = Job.objects.filter(user=self.request.user, status=failed_status).count()

        self.extra_context = {'count_all': count_all,
                              'count_rendering': count_rendering,
                              'count_completed': count_completed,
                              'count_failed': count_failed}

        if self.request.user.profile.balance <= 0:
            message = 'Your current balance is negative, add credit to continue using services. '\
                      'some job functionalities are disabled.'

            messages.error(self.request, message)

        return super(JobListView, self).get(request, args, kwargs)


class SubmitJobView(FormView):
    template_name = 'job/submit_job.html'
    form_class = KeyShotJobForm
    success_url = 'job_list'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.extra_context = {'user': self.request.user}
        if self.request.user.profile.balance <= 0:
            messages.error(self.request, 'Your current balance is negative, add credit to continue using services.')

        return super(SubmitJobView, self).get(request, args, kwargs)

    def get_initial(self):

        last_job = Job.objects.filter(user=self.request.user, software_version__plugin_name='RBOnKeyshot').last()
        if last_job and not last_job.data.get('session_id'):
            initial = {
                'software': last_job.software_version.software or Software.objects.first(),
                'version': last_job.software_version or SoftwareVersion.objects.first(),
                'file_storage': last_job.file_storage or FileStorage.objects.first(),
                'render_plan': last_job.render_plan or RenderPlan.objects.first(),
                'output_format': last_job.output_format or OutputFormat.objects.first(),
                'frame_list': last_job.frame_list,
                'image_width': last_job.data.get('plugin_info').get('image_width'),
                'image_height': last_job.data.get('plugin_info').get('image_height'),
                'quality_mode': last_job.data.get('plugin_info').get('quality_mode'),
                'max_samples': last_job.data.get('plugin_info').get('max_samples'),
                'custom_samples': last_job.data.get('plugin_info').get('custom_samples'),
                'ray_bounces': last_job.data.get('plugin_info').get('ray_bounces'),
                'anti_aliasing_quality': last_job.data.get('plugin_info').get('anti_aliasing_quality'),
                'shadow_quality': last_job.data.get('plugin_info').get('shadow_quality'),
                'educational': last_job.data.get('plugin_info').get('educational'),
                'cameras': last_job.data.get('plugin_info').get('cameras'),
            }
        else:
            initial = {}

        return initial

    def form_valid(self, form):

        frame_list = self.request.POST.getlist('frame_list')
        if not frame_list:
            messages.error(self.request, 'Frame List not provided.')
            return redirect('submit_job')

        frame_list_result = job_utils.validate_frame_list(frame_list)
        if isinstance(frame_list_result, str):
            messages.error(self.request, frame_list_result)
            return redirect('submit_job')

        cameras = self.request.POST.getlist('cameras')
        if cameras:
            for camera in cameras:
                camera_name_result = job_utils.validate_file_name(camera)
                if isinstance(camera_name_result, str):
                    messages.error(self.request, camera_name_result)
                    return redirect('submit_job')

        file_path = form.cleaned_data.get('file_path')
        file_link = form.cleaned_data.get('file_link')

        if file_path:
            dbx = DropboxHandler(self.request.user)
            file_meta_data = dbx.get_file_matadata(file_path)
            download_link = dbx.get_download_link(file_path)
            file_name = file_meta_data._name_value
            file_id = file_meta_data.id
            file_size = file_meta_data.size
            relative_url = file_meta_data.path_display
            absolute_url = download_link
        elif file_link:
            file_name = form.cleaned_data.get('file_name')
            file_id = form.cleaned_data.get('file_id')
            file_size = form.cleaned_data.get('file_size')
            relative_url = ''
            absolute_url = form.cleaned_data.get('file_link')
        else:
            messages.error(self.request, 'Source file for the job is not selected or not a valid file.')
            return redirect('submit_job')

        file_name_result = job_utils.validate_file_name(file_name)
        if isinstance(file_name_result, str):
            messages.error(self.request, file_name_result)
            return redirect('submit_job')

        software = form.cleaned_data.get('software')
        version = form.cleaned_data.get('version')
        file_storage = form.cleaned_data.get('file_storage')
        render_plan = form.cleaned_data.get('render_plan')
        output_format = form.cleaned_data.get('output_format')

        system_info = dict(plugin_name=version.plugin_name,
                           plugin_version=version.version,
                           render_plan=render_plan.name,
                           username=self.request.user.username,
                           output_format=output_format.extension,
                           storage_type=file_storage.name)

        job_info = dict(job_name='',
                        chunk_size=self.request.user.profile.chunk_size_override,
                        machine_limit=render_plan.deadline_machine_limit,
                        priority=render_plan.deadline_priority,
                        job_type='',
                        pool=version.deadline_pool,
                        group=version.deadline_group,
                        frame_list=frame_list)

        plugin_info = dict(image_width=form.cleaned_data.get('image_width'),
                           image_height=form.cleaned_data.get('image_height'),
                           quality_mode=form.cleaned_data.get('quality_mode'),
                           max_samples=form.cleaned_data.get('max_samples'),
                           custom_samples=form.cleaned_data.get('custom_samples'),
                           ray_bounces=form.cleaned_data.get('ray_bounces'),
                           anti_aliasing_quality=form.cleaned_data.get('anti_aliasing_quality'),
                           shadow_quality=form.cleaned_data.get('shadow_quality'),
                           educational=form.cleaned_data.get('educational'),
                           cameras=cameras)

        file_info = dict(file_name=file_name,
                         id=file_id,
                         size=file_size,
                         relative_url=relative_url,
                         absolute_url=absolute_url)

        job_schema = dict()
        job_schema['system_info'] = system_info
        job_schema['job_info'] = job_info
        job_schema['plugin_info'] = plugin_info
        job_schema['file_info'] = file_info

        initial = {'user': self.request.user,
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
        job.save(operator='web_user')

        if self.request.POST["submit-action"] == "publish-continue":
            messages.success(self.request, 'The new job submitted successfully.')
            return redirect('submit_job')
        else:
            return redirect('job_list')

    def form_invalid(self, form):
        messages.error(self.request, 'Something went wrong with submission!\n '
                                     'make sure all inputs are filled out correctly')
        return redirect('submit_job')


class SubmitFileSelectView(FormView):
    template_name = 'job/submit_file_select.html'
    form_class = SubmitFileSelectForm

    def __init__(self, **kwargs):
        self.session = None
        super(SubmitFileSelectView, self).__init__(**kwargs)

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        file_data = form.cleaned_data['file_data']

        try:
            file_data = json.loads(file_data)
        except:
            pass

        if isinstance(file_data, dict) and 'relative_url' not in file_data:
            dbx_submit_session = SubmitSession.objects.create(user=self.request.user,
                                                              data={'file_data': file_data})
            dbx_submit_session.save()
            return redirect(reverse('advanced_keyshot_submitter', args=[dbx_submit_session.session_id, ]))

        relative_url = file_data.get('relative_url')
        sessions = SubmitSession.objects.filter(user=self.request.user)
        for session in sessions:
            if relative_url and session.data.get('package_path'):
                if os.path.basename(relative_url) == os.path.basename(session.data.get('package_path')):
                    return redirect(reverse('advanced_keyshot_submitter', args=[session.session_id, ]))

        if relative_url:
            dbx_submit_session = SubmitSession.objects.create(user=self.request.user, data={'file_data': file_data})
            dbx_submit_session.save()
            return redirect(reverse('advanced_keyshot_submitter', args=[dbx_submit_session.session_id, ]))

        messages.error('Invalid submission detected, please try again!')
        return redirect('submit_file_select')

    def form_invalid(self, form):
        errors = json.loads(form.errors.as_json())
        for field, errors in errors.items():
            for error in errors:
                messages.error(self.request, f'{field.replace("_", " ").title()} : {error["message"]}')
        return redirect('submit_file_select')


class AdvancedSubmitterView(FormView):
    template_name = 'job/advanced_keyshot_submitter.html'
    form_class = AdvancedKeyShotJobForm
    success_url = 'job_list'

    def __init__(self, **kwargs):
        self.session = None
        super(AdvancedSubmitterView, self).__init__(**kwargs)

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        session_id = kwargs.get('session_id')
        self.session = SubmitSession.objects.filter(user=self.request.user, session_id=session_id).last()

        self.initial = {}
        # form_instance = self.get_form(form_class=self.form_class)
        form_instance = self.get_form()
        self.reset_form(form_instance)

        if not session_id:
            return redirect('submit_file_select')

        if not self.session:
            messages.error(self.request, 'Session data could not be fetched!')
            return redirect('submit_file_select')

        if self.session.data.get('file_data'):
            if self.session.data.get('file_data').get('name'):
                source_file_name = self.session.data.get('file_data').get('name')
                self.initial['source_file_name'] = os.path.basename(source_file_name)
            elif self.session.data.get('file_data').get('relative_url'):
                relative_url = self.session.data.get('file_data').get('relative_url')
                self.initial['source_file_name'] = os.path.basename(relative_url)
        else:
            self.set_initial(form_instance)
            messages.success(self.request, 'Session data fetched successfully!')

        return super(AdvancedSubmitterView, self).get(request, args, kwargs)

    def reset_form(self, form):
        form.declared_fields['multi_studios'].choices = []
        form.declared_fields['multi_cameras'].choices = []
        form.declared_fields['multi_model_sets'].choices = []
        form.declared_fields['multi_image_styles'].choices = []
        form.declared_fields['multi_environments'].choices = []
        form.declared_fields['lighting_preset'].choices = LightingPreset.choices

    def set_initial(self, form_instance):
        """
        Returns the initial data to use for forms on this view.
        """

        data = self.session.data
        host_submitter = data.get('host_submitter')
        host_application = data.get('host_application')
        lighting_preset_data = data.get('lighting_preset_data')
        animation_data = data.get('animation_data')
        studios_data = data.get('studios_data')
        configuration_data = data.get('configuration_data')
        cameras_data = data.get('cameras_data')
        model_sets_data = data.get('model_sets_data')
        environment_data = data.get('environment_data')
        image_style_data = data.get('image_style_data')
        render_options_data = data.get('render_options_data')
        materials_data = data.get('materials_data')

        errors = []
        warnings = []
        non_recognized = {}

        keyshot_version = data.get('keyshot_version')[0]
        version_object = SoftwareVersion.objects.filter(version=keyshot_version,
                                                        access_type=SoftwareVersionStatus.WEBANDAPI).first()
        if version_object and keyshot_version:
            self.initial.update({'keyshot_version': version_object})
        else:
            non_recognized.update(keyshot_version)

        render_engine = data.get('render_engine')
        render_engine = {'render_engine': render_engine}
        if render_engine:
            self.initial.update(render_engine)
        else:
            non_recognized.update(render_engine)

        source_file_name = data.get('package_path')
        if source_file_name:
            self.initial['source_file_name'] = os.path.basename(source_file_name)
        else:
            errors.append('Source file could not be recognized.')

        output_file_name = {'output_file_name': data.get('scene_name')}
        if output_file_name['output_file_name']:
            self.initial.update(output_file_name)
        else:
            non_recognized.update(output_file_name)

        image_width = data.get('scene_info').get('render_width')
        image_width = {'image_width': image_width}
        if image_width:
            self.initial.update(image_width)
        else:
            non_recognized.update(image_width)

        image_height = data.get('scene_info').get('render_height')
        image_height = {'image_height': image_height}
        if image_height:
            self.initial.update(image_height)
        else:
            non_recognized.update(image_height)

        progressive_max_samples = render_options_data.get('progressive_max_samples')
        progressive_max_samples = {'progressive_max_samples': progressive_max_samples}
        if isinstance(progressive_max_samples['progressive_max_samples'], (int, float)):
            self.initial.update(progressive_max_samples)
        else:
            non_recognized.update(progressive_max_samples)

        engine_maxs_pixel_blur = render_options_data.get('engine_pixel_blur')
        engine_maxs_pixel_blur = {'engine_maxs_pixel_blur': engine_maxs_pixel_blur}
        if isinstance(engine_maxs_pixel_blur['engine_maxs_pixel_blur'], (int, float)):
            self.initial.update(engine_maxs_pixel_blur)
        else:
            non_recognized.update(engine_maxs_pixel_blur)

        # custom quality data
        dict_attrs = {'advanced_samples': render_options_data.get('advanced_samples'),
                      'engine_anti_aliasing': render_options_data.get('engine_anti_aliasing'),
                      'engine_caustics_quality': render_options_data.get('engine_caustics_quality'),
                      'engine_dof_quality': render_options_data.get('engine_dof_quality'),
                      'engine_global_illumination': render_options_data.get('engine_global_illumination'),
                      'engine_ray_bounces': render_options_data.get('engine_ray_bounces'),
                      'engine_global_illumination_bounces': render_options_data.get('engine_indirect_bounces'),
                      'engine_pixel_blur': render_options_data.get('engine_pixel_blur'),
                      'engine_shadow_quality': render_options_data.get('engine_shadow_quality')}

        for attr, value in dict_attrs.items():
            attr_data = {attr: value}
            if isinstance(value, (int, float)):
                self.initial.update(attr_data)
            else:
                non_recognized.update(attr_data)

        dict_attrs = {'engine_sharp_shadows': render_options_data.get('engine_sharp_shadows'),
                      'engine_sharper_texture_filtering': render_options_data.get('engine_sharper_texture_filtering'),
                      'engine_global_illumination_cache': render_options_data.get('engine_global_illumination_cache')}

        for attr, value in dict_attrs.items():
            attr_data = {attr: value}
            if isinstance(value, bool):
                self.initial.update(attr_data)
            else:
                non_recognized.update(attr_data)

        # animation data
        anim_frames = animation_data.get('animation_info').get('frames')
        anim_frame_list = {'anim_frame_list': f'0'}
        if anim_frames:
            self.initial.update({'active_render_mode': RenderMode.ANIMATION})
            anim_frame_list = {'anim_frame_list': f'0-{anim_frames}'}
        else:
            self.initial.update({'active_render_mode': RenderMode.STILL})

        if isinstance(anim_frame_list['anim_frame_list'], str):
            self.initial.update(anim_frame_list)
        else:
            non_recognized.update(anim_frame_list)

        anim_video_output_file_name = {'anim_video_output_file_name': data.get('scene_name')}
        if anim_video_output_file_name['anim_video_output_file_name']:
            self.initial.update(anim_video_output_file_name)
        else:
            non_recognized.update(anim_video_output_file_name)

        # render pass and layer data
        dict_attrs = {'pass_output_diffuse_pass': render_options_data.get('output_diffuse_pass'),
                      'pass_output_reflection_pass': render_options_data.get('output_reflection_pass'),
                      'pass_output_clown_pass': render_options_data.get('output_clown_pass'),
                      'pass_output_direct_lighting_pass': render_options_data.get('output_direct_lighting_pass'),
                      'pass_output_refraction_pass': render_options_data.get('output_refraction_pass'),
                      'pass_output_depth_pass': render_options_data.get('output_depth_pass'),
                      'pass_output_indirect_lighting_pass': render_options_data.get('output_indirect_lighting_pass'),
                      'pass_output_shadow_pass': render_options_data.get('output_shadow_pass'),
                      'pass_output_normals_pass': render_options_data.get('output_normals_pass'),
                      'pass_output_caustics_pass': render_options_data.get('output_caustics_pass'),
                      'pass_output_ambient_occlusion_pass': render_options_data.get('output_ambient_occlusion_pass'),
                      'rlyr_output_render_layers': render_options_data.get('output_render_layers'),
                      'rlyr_output_alpha_channel': render_options_data.get('output_alpha_channel')}

        for attr, value in dict_attrs.items():
            attr_data = {attr: value}
            if isinstance(value, bool):
                self.initial.update(attr_data)
            else:
                non_recognized.update(attr_data)

        # image style data
        dict_attrs = {'imgstyl_override': image_style_data.get('imgstyl_override'),
                      'imgstyl_kind': image_style_data.get('kind'),
                      'imgstyl_bloom': image_style_data.get('bloom'),
                      'imgstyl_color': image_style_data.get('color'),
                      'imgstyl_curve': image_style_data.get('curve'),
                      'imgstyl_denoise': image_style_data.get('denoise'),
                      'imgstyl_vignette': image_style_data.get('vignette'),
                      'imgstyl_chromatic_aberration': image_style_data.get('chromatic_aberration'),
                      }

        for attr, value in dict_attrs.items():
            attr_data = {attr: value}
            if isinstance(value, (bool, int)):
                self.initial.update(attr_data)
            else:
                non_recognized.update(attr_data)

        # populate multi-materials
        scene_materials = []
        for idx, material in materials_data.get('data').items():
            if material.get('multi_material'):
                scene_materials.append(material.get('name'))

        for material in scene_materials:
            self.initial.update({'mtl_multi_material_name': (material, material)})

        # populate studios
        active_studio = studios_data.get('active_studio')
        scene_studios = studios_data.get('studios')

        form_instance.declared_fields['multi_studios'].choices = BaseChoices.choices
        for studio in scene_studios:
            form_instance.declared_fields['multi_studios'].choices.append((studio, studio))

        active_studio_choice = (active_studio, active_studio)
        if active_studio and active_studio_choice not in form_instance.declared_fields['multi_studios'].choices:
            form_instance.declared_fields['multi_studios'].choices.append(active_studio_choice)
            # self.initial.update({'multi_studios': [active_studio, ]})

        # populate cameras
        active_camera = cameras_data.get('camera')
        scene_cameras = cameras_data.get('cameras')

        form_instance.declared_fields['multi_cameras'].choices = BaseChoices.choices
        for camera in scene_cameras:
            if camera == 'last_active':
                continue
            form_instance.declared_fields['multi_cameras'].choices.append((camera, camera))
        # if active_camera:
        #     self.initial.update({'multi_cameras': [active_camera, ]})

        # populate model sets
        form_instance.declared_fields['multi_model_sets'].choices = BaseChoices.choices
        scene_model_sets = model_sets_data.get('model_sets')
        for model_set in scene_model_sets:
            if model_set == 'Default':
                continue
            form_instance.declared_fields['multi_model_sets'].choices.append((model_set, model_set))

        form_instance.declared_fields['multi_image_styles'].choices = BaseChoices.choices
        # populate image styles
        active_image_style = image_style_data.get('active_image_style')
        scene_image_styles = image_style_data.get('image_styles')
        for image_style in scene_image_styles:
            if image_style == 'Default':
                continue
            form_instance.declared_fields['multi_image_styles'].choices.append((image_style, image_style))

        active_image_style_choice = (active_image_style, active_image_style)
        if active_image_style and active_image_style_choice not in form_instance.declared_fields['multi_image_styles'].choices:
            form_instance.declared_fields['multi_image_styles'].choices.append(active_image_style_choice)

        # if active_image_style:
        #     self.initial.update({'multi_image_styles': [active_image_style, ]})

        form_instance.declared_fields['multi_environments'].choices = BaseChoices.choices
        # populate environments
        active_environment = environment_data.get('active_environment')
        active_environment_data = {}
        for idx, data in environment_data.get('data').items():
            if data.get('name') == active_environment:
                active_environment_data = data

        scene_environments = environment_data.get('environments')
        for environment in scene_environments:
            form_instance.declared_fields['multi_environments'].choices.append((environment, environment))

        active_environment_choice = (active_environment, active_environment)
        if active_environment and active_environment_choice not in form_instance.declared_fields['multi_environments'].choices:
            form_instance.declared_fields['multi_environments'].choices.append(active_environment_choice)

        # if active_environment:
        #     self.initial.update({'multi_environments': [active_environment, ]})

        external_files = data.get('external_files', [])
        external_files_choices = [(item, item) for item in external_files]

        # environments data
        if active_environment_data:
            dict_attrs = {'env_brightness': active_environment_data.get('brightness'),
                          'env_size': active_environment_data.get('size'),
                          'env_height': active_environment_data.get('height'),
                          'env_rotation': active_environment_data.get('rotation'),
                          'env_ground_shadows': active_environment_data.get('ground_shadows'),
                          'env_occlusion_ground_shadows': active_environment_data.get('occlusion_ground_shadows'),
                          'env_ground_reflections': active_environment_data.get('ground_reflections'),
                          'env_flatten_ground': active_environment_data.get('flatten_ground'),
                          'env_ground_size': active_environment_data.get('ground_size')
                          }

            for attr, value in dict_attrs.items():
                attr_data = {attr: value}
                if isinstance(value, (bool, int, float)):
                    self.initial.update(attr_data)
                else:
                    non_recognized.update(attr_data)

            # populate env_lighting_environment
            active_lighting_environment = active_environment_data.get('lighting_environment')
            form_instance.declared_fields['env_lighting_environment'].choices = external_files_choices

            if active_lighting_environment:
                form_instance.declared_fields['env_lighting_environment'].choices.append((active_lighting_environment,
                                                                                          active_lighting_environment))
                self.initial.update({'env_lighting_environment': [active_lighting_environment, ]})

            # populate env_backplate_image
            active_backplate_image = active_environment_data.get('backplate_image')
            form_instance.declared_fields['env_backplate_image'].choices = external_files_choices

            if active_lighting_environment:
                form_instance.declared_fields['env_backplate_image'].choices.append((active_backplate_image,
                                                                                     active_backplate_image))
                self.initial.update({'env_backplate_image': [active_backplate_image, ]})

            env_background_color = active_environment_data.get('background_color')
            if env_background_color:
                env_background_color = rgb_to_hex(*env_background_color)

            env_background_color = {'env_background_color': env_background_color}
            if isinstance(env_background_color['env_background_color'], str):
                self.initial.update(env_background_color)
            else:
                non_recognized.update(env_background_color)

        # populate lighting_preset
        active_lighting_preset = lighting_preset_data.get('lighting_preset')
        scene_lighting_presets = lighting_preset_data.get('lighting_presets')
        for lighting_preset in scene_lighting_presets:
            item = (lighting_preset, lighting_preset)
            if item not in form_instance.declared_fields['lighting_preset'].choices:
                form_instance.declared_fields['lighting_preset'].choices.append(item)
        if active_lighting_preset:
            self.initial.update({'lighting_preset': [active_lighting_preset, ]})

        active_quality_mode = render_options_data.get('render_mode')
        active_quality_mode = {'active_quality_mode': active_quality_mode}
        if isinstance(active_quality_mode['active_quality_mode'], int):
            self.initial.update(active_quality_mode)
        else:
            non_recognized.update(active_quality_mode)

    def get_options(self, form, option):
        target_options = []
        selected_options = form.cleaned_data.get(f'multi_{option}')

        if not selected_options:
            return target_options

        if BaseChoices.ALL in selected_options:
            options = []
            if f'multi_{option}' == 'multi_cameras':
                options = self.session.data.get('cameras_data').get('cameras')
            elif f'multi_{option}' == 'multi_model_sets':
                options = self.session.data.get('model_sets_data').get('model_sets')
            elif f'multi_{option}' == 'multi_image_styles':
                options = self.session.data.get('image_style_data').get('image_styles')
                active_image_style = self.session.data.get('image_style_data').get('active_image_style')
                if active_image_style:
                    options.append(active_image_style)
            elif f'multi_{option}' == 'multi_environments':
                options = self.session.data.get('environment_data').get('environments')
                active_environment = self.session.data.get('environment_data').get('active_environment')
                if active_environment:
                    options.append(active_environment)
            elif f'multi_{option}' == 'multi_studios':
                options = self.session.data.get('studios_data').get('studios')
                active_studio = self.session.data.get('studios_data').get('active_studio')
                if active_studio:
                    options.append(active_studio)
            target_options.extend(options)
        else:
            target_options.extend(selected_options)

        form.cleaned_data[f'multi_{option}'] = target_options
        return target_options

    def get_clean_name(self, name):
        new_name = 'untitled'
        try:
            name, _ = os.path.splitext(name)
        except:
            return new_name

        new_name = name
        for bad_chr in ['#', '%', ':', '£', '¬', '?', '\\', '/', "'", '"', '<', '>', '|', ' ', '.']:
            new_name = new_name.replace(bad_chr, '')

        return new_name

    def form_valid(self, form):

        session_id = self.kwargs.get('session_id')
        self.session = SubmitSession.objects.filter(user=self.request.user, session_id=session_id).last()

        data = {}
        data.update({'session_id': str(self.session.session_id),
                     'session_data': self.session.data})


        source_file_name = form.cleaned_data.get('source_file_name')
        job_name = self.get_clean_name(source_file_name)

        frame_list = '0'

        # check and validate multi mode setting
        active_render_mode = form.cleaned_data['active_render_mode']
        if form.cleaned_data.get('multi_override'):
            if active_render_mode == RenderMode.STILL:
                multi_task_options = {MultiTaskMode.STUDIOS: MultiTaskMode.STUDIOS.label,
                                      MultiTaskMode.CAMERAS: MultiTaskMode.CAMERAS.label,
                                      MultiTaskMode.MODELSETS: MultiTaskMode.MODELSETS.label,
                                      MultiTaskMode.IMAGESTYLES: MultiTaskMode.IMAGESTYLES.label,
                                      MultiTaskMode.ENVIRONMENTS: MultiTaskMode.ENVIRONMENTS.label}

                options = self.get_options(form,
                                           multi_task_options.get(form.cleaned_data.get('active_multi_task_mode')))

                if len(options):
                    frame_list = f'0-{len(options) - 1}'

        if active_render_mode == RenderMode.ANIMATION:
            frame_list = form.cleaned_data.get('anim_frame_list', frame_list or '0')

        render_plan = form.cleaned_data.pop('render_plan')
        keyshot_version = form.cleaned_data.pop('keyshot_version')

        data.update(form.cleaned_data)
        initial = {'user': self.request.user,
                   'name': job_name,
                   'render_plan': render_plan,
                   'frame_list': [frame_list, ],
                   'status': JobStatus.objects.filter(name='submitted').first(),
                   'software_version': keyshot_version,
                   'data': data}

        job = Job.objects.create(**initial)
        job.save(operator='web_user')

        if self.request.POST["submit-action"] == "publish-continue":
            messages.success(self.request, f'The new job submitted successfully : {job.name}')
            return redirect(self.request.path_info)
        else:
            return redirect('job_list')

    def form_invalid(self, form):
        errors = json.loads(form.errors.as_json())
        for field, errors in errors.items():
            for error in errors:
                messages.error(self.request, f'{field.replace("_", " ").title()} : {error["message"]}')

        return super(AdvancedSubmitterView, self).form_invalid(form)


def job_output_url(request):
    dbx = DropboxHandler(request.user)
    job_name = request.GET.get('job_name', '')

    if job_name:
        job = Job.objects.filter(name=job_name).first()

        if not job.user == request.user:
            return JsonResponse({"url": "#"})

        if not job:
            return JsonResponse({"url": "#"})
        url = dbx.get_job_output_link(job_name)
    else:
        url = dbx.get_user_outputs_link()

    return JsonResponse({"url": url})


def get_file_select(request):

    dbx = DropboxHandler(request.user)
    user_files = dbx.get_list_of_source_files(['.ksp'])

    for file_meta in user_files:
        if isinstance(job_utils.validate_file_name(file_meta.name), str):
            file_meta.is_downloadable = False
        else:
            file_meta.is_downloadable = True

    html = render_to_string('job/temp_select_file_modal.html', context={'user_files': reversed(user_files)})
    return JsonResponse({"data": html})
