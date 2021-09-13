import json
import re

from django.db import models
from django import forms
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _
from job.models import *


class QualityModes(models.TextChoices):
    MAX_SAMPLES = 'maximum_samples', _('Maximum Samples')
    CUSTOM_CONTROL = 'custom_control', _('Custom Control')


class KeyShotJobForm(forms.Form):

    software = forms.ModelChoiceField(label=_("Software"),
                                      queryset=Software.objects.all(),
                                      initial=Software.objects.first,
                                      widget=forms.Select(
                                      attrs={'class': "form-control",
                                             'id': 'software_list_input'}))

    version = forms.ModelChoiceField(label=_("Version"),
                                     queryset=SoftwareVersion.objects.exclude(access_type=SoftwareVersionStatus.API),
                                     initial=SoftwareVersion.objects.first,
                                     widget=forms.Select(
                                     attrs={'class': "form-control",
                                            'id': 'version_list_input'}))

    file_storage = forms.ModelChoiceField(label=_("Storage"),
                                          queryset=FileStorage.objects.all(),
                                          initial=FileStorage.objects.first,
                                          widget=forms.Select(
                                          attrs={'class': "form-control",
                                                 'id': 'storage_list_input'}))

    render_plan = forms.ModelChoiceField(label=_("Render Plan"),
                                         empty_label="Select a Render Plan",
                                         queryset=RenderPlan.objects.exclude(admin_only=True).order_by('display_name'),
                                         initial=RenderPlan.objects.exclude(admin_only=True).order_by('display_name').first,
                                         widget=forms.Select(
                                         attrs={'class': "form-control",
                                                'id': 'render_plan_list_input'}))

    output_format = forms.ModelChoiceField(label=_("Output Format"),
                                           empty_label="Select an Output Format",
                                           queryset=OutputFormat.objects.all(),
                                           initial=OutputFormat.objects.first,
                                           widget=forms.Select(
                                           attrs={'class': "form-control",
                                                  'id': 'output_format_list_input'}))

    file_path = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'file_path_input'}))
    file_link = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'file_link_input'}))
    file_id = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'file_id_input'}))
    file_size = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'file_size_input'}))
    file_name = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'file_name_input'}))

    frame_list = forms.CharField(label=_("Frame List"),
                                 required=False,
                                 widget=forms.Select(attrs={'class': "form-control select2_frame_list",
                                                            'id': 'frame_list',
                                                            'multiple': True,
                                                            'tags': True}))

    image_width = forms.IntegerField(label=_("Image Width"),
                                     required=True,
                                     min_value=10,
                                     widget=forms.NumberInput(
                                     attrs={'autocomplete': 'image_width',
                                            'class': "form-control",
                                            'placeholder': 'Image Width',
                                            'id': 'image_width'}))

    image_height = forms.IntegerField(label=_("Image Height"),
                                      required=True,
                                      min_value=10,
                                      widget=forms.NumberInput(
                                      attrs={'autocomplete': 'image_height',
                                             'class': "form-control",
                                             'placeholder': 'Image Height',
                                             'id': 'image_height'}))

    quality_mode = forms.ChoiceField(label=_("Quality Mode"),
                                     required=True,
                                     choices=QualityModes.choices,
                                     widget=forms.Select(
                                     attrs={'autocapitalize': 'none',
                                            'autocomplete': 'quality_mode',
                                            'class': "form-control",
                                            'id': 'quality_mode'})
                                     )

    max_samples = forms.IntegerField(label=_("Samples"),
                                     min_value=1,
                                     required=False,
                                     widget=forms.NumberInput(
                                     attrs={'autocomplete': 'max_samples',
                                            'class': "form-control max_samples",
                                            'placeholder': 'Samples',
                                            'id': 'max_samples'}))

    custom_samples = forms.IntegerField(label=_("Samples"),
                                        min_value=1,
                                        required=False,
                                        widget=forms.NumberInput(
                                        attrs={'autocomplete': 'custom_samples',
                                               'class': "form-control custom_samples",
                                               'placeholder': 'Samples',
                                               'id': 'custom_samples'}))

    ray_bounces = forms.IntegerField(label=_("Ray Bounces"),
                                     min_value=1,
                                     required=False,
                                     widget=forms.NumberInput(
                                     attrs={'autocomplete': 'custom_samples',
                                            'class': "form-control custom_samples",
                                            'placeholder': 'Ray Bounces',
                                            'id': 'ray_bounces'}))

    anti_aliasing_quality = forms.IntegerField(label=_("Anti Aliasing Quality"),
                                               min_value=1,
                                               required=False,
                                               widget=forms.NumberInput(
                                               attrs={'autocomplete': 'anti_aliasing_quality',
                                                      'class': "form-control custom_samples",
                                                      'placeholder': 'Anti Aliasing Quality',
                                                      'id': 'anti_aliasing_quality'}))

    shadow_quality = forms.FloatField(label=_("Shadow Quality"),
                                      min_value=1,
                                      required=False,
                                      widget=forms.NumberInput(
                                      attrs={'autocomplete': 'shadow_quality',
                                             'class': "form-control custom_samples",
                                             'placeholder': 'Shadow Quality',
                                             'id': 'shadow_quality'}))

    educational = forms.BooleanField(label=_("Educational File"), required=False, widget=forms.CheckboxInput(
        attrs={'class': "custom-control-input", 'id': "educational"}))

    cameras = forms.CharField(label=_("Camera/s"),
                              required=False,
                              widget=forms.Select(attrs={'class': "form-control select2_cameras",
                                                         'id': 'cameras',
                                                         'multiple': True,
                                                         'tags': True}))

    def __init__(self, *args, **kwargs):
        super(KeyShotJobForm, self).__init__(*args, **kwargs)


class RenderEngine(models.IntegerChoices):
    INTERIOR = 1, 'CPU (Interior Mode)'
    INTERIOR_GPU = 4, 'GPU (Interior Mode)'
    PRODUCT = 0, 'CPU (Product Mode)'
    PRODUCT_GPU = 3, 'GPU (Product Mode)'


class OutputFormatOptions(models.TextChoices):
    EXR = 2, 'EXR'
    JPEG = 0, 'JPEG'
    PNG = 5, 'PNG'
    PSD16 = 8, 'PSD16'
    PSD32 = 7, 'PSD32'
    PSD8 = 6, 'PSD8'
    TIFF32 = 3, 'TIFF32'
    TIFF8 = 1, 'TIFF8'


class VideoOutputFormat(models.TextChoices):
    MP4 = 0, 'MP4'
    MOV = 1, 'MOV'
    AVI = 2, 'AVI'
    FLV = 3, 'FLV'


class LightingPreset(models.TextChoices):

    PerformanceMode = 'Performance Mode', 'Performance Mode'
    Basic = 'Basic', 'Basic'
    Product = 'Product', 'Product'
    Interior = 'Interior', 'Interior'
    Jewelry = 'Jewelry', 'Jewelry'
    Custom = '-', 'Custom'


class ImageStyleMode(models.IntegerChoices):
    BASIC = 0, 'Basic'
    PHOTOGRAPHIC = 1, 'Photographic'


class XRCenterType(models.TextChoices):
    CAMERA = 4, 'Camera'
    CAMERA_PIVOT = 5, 'Camera Pivot'
    ENVIRONMENT = 1, 'Environment'
    OBJECT = 2, 'Object'


class XRType(models.TextChoices):
    CUSTOM = 5, 'Custom'
    HEMISPHERICAL = 3, 'Hemispherical'
    SPHERICAL = 2, 'Spherical'
    TUMBLE = 4, 'Tumble'
    TURNTABLE = 1, 'Turntable'


class BaseChoices(models.TextChoices):
    ALL = 'all', 'All'


class QualityMode(models.IntegerChoices):
    MAX_SAMPLES = 2, 'Max Samples'
    CUSTOM = 0, 'Custom Control'


class RenderMode(models.IntegerChoices):
    STILL = 0, 'still'
    ANIMATION = 1, 'anim'
    XR = 2, 'xr'
    CONFIGURATOR = 3, 'configurator'
    MULTIMATERIAL = 4, 'multimaterial'


class MultiTaskMode(models.IntegerChoices):
    STUDIOS = 0, 'studios'
    CAMERAS = 1, 'cameras'
    MODELSETS = 2, 'model_sets'
    IMAGESTYLES = 3, 'image_styles'
    ENVIRONMENTS = 4, 'environments'


def custom_label(label, column=3):
    return mark_safe(f'<label class="col-{column} col-form-label">{label}</label>')


def custom_boolean_label(label, input_id):
    return mark_safe(f'<label class="custom-control-label" for="{input_id}">{label}</label>')


class CustomMultipleChoiceField(forms.MultipleChoiceField):
    def validate(self, value):
        pass


class CustomChoiceField(forms.ChoiceField):
    def validate(self, value):
        pass


def validate_frame_list(value):

    if value.isdigit():
        return

    if not value.replace('-', '').replace('x', '').replace(',', '').isdigit():
        raise ValidationError('Frame List format is not valid.', params={'value': value}, )

    chunks = value.split(',')
    bad_chunks = []
    for chunk in chunks:
        if chunk.isdigit():
            continue

        if re.compile(r"^(\d+)-(\d+)$").findall(chunk):
            continue

        if re.compile(r"^(\d+)-(\d+)x(\d+)$").findall(chunk):
            continue

        bad_chunks.append(chunk)

    if bad_chunks:
        raise ValidationError(f'Frame List format is not valid : {bad_chunks}', params={'value': value}, )


class AdvancedKeyShotJobForm(forms.Form):

    # hidden fields
    active_render_mode = forms.IntegerField(widget=forms.HiddenInput, initial=RenderMode.STILL)

    active_quality_mode = forms.IntegerField(widget=forms.HiddenInput, initial=QualityMode.MAX_SAMPLES)

    active_multi_task_mode = forms.IntegerField(widget=forms.HiddenInput, initial=MultiTaskMode.STUDIOS)


    # generic options
    keyshot_version = forms.ModelChoiceField(label=custom_label("KeyShot Version"),
                                             queryset=SoftwareVersion.objects.exclude(access_type=SoftwareVersionStatus.API),
                                             initial=SoftwareVersion.objects.first,
                                             widget=forms.Select(attrs={'class': "custom-select"}))

    render_plan = forms.ModelChoiceField(label=custom_label("Job Priority"),
                                         empty_label=None,
                                         queryset=RenderPlan.objects.filter(name__istartswith='v2'),
                                         widget=forms.Select(attrs={'class': "custom-select"}))

    render_engine = forms.ChoiceField(label=custom_label("Render Engine"),
                                      widget=forms.Select(attrs={'class': "custom-select"}),
                                      initial=RenderEngine.PRODUCT,
                                      choices=RenderEngine.choices)
    
    source_file_name = forms.CharField(label=custom_label('Source File Name'),
                                       widget=forms.TextInput(attrs={'class': "form-control",
                                                                     'readonly':'readonly'}))

    output_file_name = forms.CharField(label=custom_label('Output File Name'),
                                       widget=forms.TextInput(attrs={'class': "form-control"}),
                                       initial='render_output')

    output_format = forms.ChoiceField(label=custom_label("Output Format"),
                                      widget=forms.Select(attrs={'class': "custom-select"}),
                                      initial=OutputFormatOptions.JPEG,
                                      choices=OutputFormatOptions.choices)

    image_width = forms.IntegerField(label=custom_label('Image Width'),
                                     widget=forms.NumberInput(attrs={'class': "form-control"}),
                                     min_value=50,
                                     initial=1280)

    image_height = forms.IntegerField(label=custom_label('Image Height'),
                                      widget=forms.NumberInput(attrs={'class': "form-control"}),
                                      min_value=50,
                                      initial=720)

    educational = forms.BooleanField(label=custom_boolean_label('Educational File', 'id_educational'),
                                     widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                     initial=False,
                                     required=False)

    quality_override = forms.BooleanField(label=custom_boolean_label('Select/Override Quality Settings',
                                                                     'id_quality_override'),
                                          widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                          required=False)
    # max samples options
    progressive_max_samples = forms.IntegerField(label=custom_label('Samples'),
                                                 widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                 initial=32,
                                                 min_value=0,
                                                 required=False)

    engine_maxs_pixel_blur = forms.FloatField(label=custom_label('Pixel Blur'),
                                              widget=forms.NumberInput(attrs={'class': "form-control"}),
                                              initial=1.0,
                                              min_value=0,
                                              required=False)

    # custom quality options
    advanced_samples = forms.IntegerField(label=custom_label('Samples'),
                                          widget=forms.NumberInput(attrs={'class': "form-control"}),
                                          initial=32,
                                          min_value=0,
                                          required=False)

    engine_anti_aliasing = forms.IntegerField(label=custom_label('Anti Aliasing'),
                                              widget=forms.NumberInput(attrs={'class': "form-control"}),
                                              initial=1,
                                              min_value=0,
                                              required=False)

    engine_caustics_quality = forms.FloatField(label=custom_label('Caustics'),
                                               widget=forms.NumberInput(attrs={'class': "form-control"}),
                                               initial=1.0,
                                               min_value=0,
                                               required=False)

    engine_dof_quality = forms.FloatField(label=custom_label('DOF'),
                                          widget=forms.NumberInput(attrs={'class': "form-control"}),
                                          initial=1.0,
                                          min_value=0,
                                          required=False)

    engine_global_illumination = forms.FloatField(label=custom_label('Global Illumination Quality'),
                                                  widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                  initial=1.0,
                                                  min_value=0,
                                                  required=False)

    engine_ray_bounces = forms.FloatField(label=custom_label('Ray Bounces'),
                                          widget=forms.NumberInput(attrs={'class': "form-control"}),
                                          initial=1.0,
                                          min_value=0,
                                          required=False)

    engine_global_illumination_bounces = forms.IntegerField(label=custom_label('Global Illumination Bounces'),
                                                            widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                            initial=2,
                                                            min_value=0,
                                                            required=False)

    engine_pixel_blur = forms.FloatField(label=custom_label('Pixel Blur'),
                                         widget=forms.NumberInput(attrs={'class': "form-control"}),
                                         initial=1.0,
                                         min_value=0,
                                         required=False)

    engine_shadow_quality = forms.FloatField(label=custom_label('Shadow'),
                                             widget=forms.NumberInput(attrs={'class': "form-control"}),
                                             initial=1.0,
                                             min_value=0,
                                             required=False)

    engine_sharp_shadows = forms.BooleanField(label=custom_boolean_label('Sharp Shadows', 'id_engine_sharp_shadows'),
                                              widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                              initial=True,
                                              required=False)

    engine_sharper_texture_filtering = forms.BooleanField(label=custom_boolean_label('Sharper Texture Filtering',
                                                                                     'id_engine_sharper_texture_filtering'),
                                                          widget=forms.CheckboxInput(
                                                              attrs={'class': 'custom-control-input'}),
                                                          required=False)

    engine_global_illumination_cache = forms.BooleanField(label=custom_boolean_label('Global Illumination Cache',
                                                                                     'id_engine_global_illumination_cache'),
                                                          widget=forms.CheckboxInput( attrs={'class': 'custom-control-input'}),
                                                          initial=True,
                                                          required=False)

    # animation render specific options
    anim_frame_list = forms.CharField(label=custom_label('Frame List'),
                                      strip=True,
                                      validators=[validate_frame_list, ],
                                      widget=forms.TextInput(attrs={'class': "form-control"}),
                                      required=False)

    anim_fps = forms.IntegerField(label=custom_label('FPS'),
                                  widget=forms.NumberInput(attrs={'class': "form-control"}),
                                  min_value=1,
                                  initial=30,
                                  required=False)

    anim_video_output = forms.BooleanField(label=custom_boolean_label('Create Video Output', 'id_anim_video_output'),
                                           widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                           initial=False,
                                           required=False)

    anim_video_output_format = forms.ChoiceField(label=custom_label("Video Output Format"),
                                                 widget=forms.Select(attrs={'class': "custom-select"}),
                                                 choices=VideoOutputFormat.choices,
                                                 required=False)

    anim_video_output_file_name = forms.CharField(label=custom_label('Output Video File Name'),
                                                  widget=forms.TextInput(attrs={'class': "form-control"}),
                                                  initial='video_output',
                                                  required=False)

    anim_video_output_fps = forms.IntegerField(label=custom_label('Video Output FPS'),
                                               widget=forms.NumberInput(attrs={'class': "form-control"}),
                                               min_value=1,
                                               initial=30,
                                               required=False)

    # xr render specific options
    xr_type = forms.ChoiceField(label=custom_label("KeyShotXR Mode"),
                                widget=forms.Select(attrs={'class': "custom-select"}),
                                initial=XRType.TURNTABLE,
                                choices=XRType.choices,
                                required=False)

    xr_center_type = forms.ChoiceField(label=custom_label("KeyShotXR Rotation Center"),
                                       widget=forms.Select(attrs={'class': "custom-select"}),
                                       choices=XRCenterType.choices,
                                       initial=XRCenterType.OBJECT,
                                       required=False)

    xr_viewport_width = forms.IntegerField(label=custom_label('Viewing Width'),
                                           widget=forms.NumberInput(attrs={'class': "form-control"}),
                                           min_value=20,
                                           initial=500,
                                           required=False)

    xr_viewport_height = forms.IntegerField(label=custom_label('Viewing Height'),
                                            widget=forms.NumberInput(attrs={'class': "form-control"}),
                                            min_value=20,
                                            initial=500,
                                            required=False)

    xr_horizontal_frames = forms.IntegerField(label=custom_label('Horizontal Frames'),
                                              widget=forms.NumberInput(attrs={'class': "form-control"}),
                                              min_value=1,
                                              initial=5,
                                              required=False)

    xr_vertical_frames = forms.IntegerField(label=custom_label('Vertical Frames'),
                                            widget=forms.NumberInput(attrs={'class': "form-control"}),
                                            min_value=1,
                                            initial=5,
                                            required=False)

    xr_horizontal_angel_begin = forms.IntegerField(label=custom_label('Horizontal Angel Begin'),
                                                   widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                   min_value=-360,
                                                   max_value=360,
                                                   initial=-180,
                                                   required=False)

    xr_horizontal_angel_end = forms.IntegerField(label=custom_label('Horizontal Angel End'),
                                                 widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                 min_value=-360,
                                                 max_value=360,
                                                 initial=180,
                                                 required=False)

    xr_vertical_angel_begin = forms.IntegerField(label=custom_label('Vertical Angel Begin'),
                                                 widget=forms.NumberInput(attrs={'class': "form-control"}),
                                                 min_value=-360,
                                                 max_value=360,
                                                 initial=-80,
                                                 required=False)

    xr_vertical_angel_end = forms.IntegerField(label=custom_label('Vertical Angel End'),
                                               widget=forms.NumberInput(attrs={'class': "form-control"}),
                                               min_value=-360,
                                               max_value=360,
                                               initial=80,
                                               required=False)

    # configuration render specific options
    cfg_web = forms.BooleanField(label=custom_boolean_label('Web Configurator', 'id_cfg_web'),
                                 widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                 initial=False,
                                 required=False)

    cfg_model_variations = forms.BooleanField(label=custom_boolean_label('Model Variations', 'id_cfg_model_variations'),
                                              widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                              initial=False,
                                              required=False)

    cfg_material_variations = forms.BooleanField(label=custom_boolean_label('Material Variations',
                                                                            'id_cfg_material_variations'),
                                                 widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                                 initial=False,
                                                 required=False)

    cfg_studio_variations = forms.BooleanField(label=custom_boolean_label('Studio Variations',
                                                                          'id_cfg_studio_variations'),
                                               widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                               initial=False,
                                               required=False)

    cfg_i_book = forms.BooleanField(label=custom_boolean_label('Create iBooks Widget', 'id_cfg_i_book'),
                                    widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                    initial=False,
                                    required=False)

    cfg_i_book_width = forms.IntegerField(label=custom_label('iBooks Width'),
                                          widget=forms.NumberInput(attrs={'class': "form-control"}),
                                          min_value=50,
                                          initial=1280,
                                          required=False)

    cfg_i_book_height = forms.IntegerField(label=custom_label('iBooks Height'),
                                           widget=forms.NumberInput(attrs={'class': "form-control"}),
                                           min_value=50,
                                           initial=720,
                                           required=False)

    # multi_material render specific options
    mtl_multi_material_name = forms.ChoiceField(label=custom_label('Multi-Material Name'),
                                                widget=forms.Select(attrs={'class': "custom-select"}),
                                                required=False)

    # render layers override settings
    rlyr_override = forms.BooleanField(label=custom_boolean_label('Override Render Layer Settings', 'id_rlyr_override'),
                                       widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                       initial=False,
                                       required=False)

    rlyr_output_render_layers = forms.BooleanField(label=custom_boolean_label('Output Render Layers',
                                                                              'id_rlyr_output_render_layers'),
                                                   widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                                   required=False)

    rlyr_output_alpha_channel = forms.BooleanField(label=custom_boolean_label('Output Alpha Channel',
                                                                              'id_rlyr_output_alpha_channel'),
                                                   widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
                                                   required=False)

    # render passes override settings
    pass_override = forms.BooleanField(label=custom_boolean_label('Override Render Pass Settings', 'id_pass_override'),
                                       widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                       required=False)

    pass_all_render_passes = forms.BooleanField(label=custom_boolean_label('All Render Passes',
                                                                           'id_pass_all_render_passes'),
                                                widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                required=False)

    pass_output_diffuse_pass = forms.BooleanField(label=custom_boolean_label('Diffuse',
                                                                             'id_pass_output_diffuse_pass'),
                                                  widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                  required=False)

    pass_output_reflection_pass = forms.BooleanField(label=custom_boolean_label('Reflection',
                                                                                'id_pass_output_reflection_pass'),
                                                     widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                     required=False)

    pass_output_clown_pass = forms.BooleanField(label=custom_boolean_label('Clown',
                                                                           'id_pass_output_clown_pass'),
                                                widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                required=False)

    pass_output_direct_lighting_pass = forms.BooleanField(label=custom_boolean_label('Lighting',
                                                                                     'id_pass_output_direct_lighting_pass'),
                                                          widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                          required=False)

    pass_output_refraction_pass = forms.BooleanField(label=custom_boolean_label('Refraction',
                                                                                'id_pass_output_refraction_pass'),
                                                     widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                     required=False)

    pass_output_depth_pass = forms.BooleanField(label=custom_boolean_label('Depth',
                                                                           'id_pass_output_depth_pass'),
                                                widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                required=False)

    pass_output_indirect_lighting_pass = forms.BooleanField(label=custom_boolean_label('Global Illumination',
                                                                                       'id_pass_output_indirect_lighting_pass'),
                                                            widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                            required=False)

    pass_output_shadow_pass = forms.BooleanField(label=custom_boolean_label('Shadow',
                                                                            'id_pass_output_shadow_pass'),
                                                 widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                 required=False)

    pass_output_normals_pass = forms.BooleanField(label=custom_boolean_label('Normals',
                                                                             'id_pass_output_normals_pass'),
                                                  widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                  required=False)

    pass_output_caustics_pass = forms.BooleanField(label=custom_boolean_label('Caustics',
                                                                              'id_pass_output_caustics_pass'),
                                                   widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                   required=False)

    pass_output_ambient_occlusion_pass = forms.BooleanField(label=custom_boolean_label('Ambient Occlusion',
                                                                                       'id_pass_output_ambient_occlusion_pass'),
                                                            widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                            required=False)

    # multi task options
    multi_override = forms.BooleanField(label=custom_boolean_label('Select/Override Default Scene State',
                                                                   'id_multi_override'),
                                        widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                        required=False)

    multi_studios = CustomMultipleChoiceField(label=custom_label('Studios'),
                                              choices=[BaseChoices.choices[0], ],
                                              widget=forms.SelectMultiple(attrs={'class': "custom-select"}),
                                              required=False)

    multi_cameras = CustomMultipleChoiceField(label=custom_label('Cameras'),
                                              choices=[BaseChoices.choices[0], ],
                                              widget=forms.SelectMultiple(attrs={'class': "custom-select"}),
                                              required=False)

    multi_model_sets = CustomMultipleChoiceField(label=custom_label('Model-Sets'),
                                                 choices=[BaseChoices.choices[0], ],
                                                 widget=forms.SelectMultiple(attrs={'class': "custom-select"}),
                                                 required=False)

    multi_image_styles = CustomMultipleChoiceField(label=custom_label('Image Styles'),
                                                   choices=[BaseChoices.choices[0], ],
                                                   widget=forms.SelectMultiple(attrs={'class': "custom-select"}),
                                                   required=False)

    multi_environments = CustomMultipleChoiceField(label=custom_label('Environments'),
                                                   choices=[BaseChoices.choices[0], ],
                                                   widget=forms.SelectMultiple(attrs={'class': "custom-select"}),
                                                   required=False)

    # environment override settings
    env_override = forms.BooleanField(label=custom_boolean_label('Override Environment Settings', 'id_env_override'),
                                      widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                      initial=False,
                                      required=False)

    lighting_override = forms.BooleanField(label=custom_boolean_label('Override Lighting Settings',
                                                                      'id_lighting_override'),
                                           widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                           required=False)

    lighting_preset = CustomChoiceField(label=custom_label("Lighting Preset"),
                                        widget=forms.Select(attrs={'class': "custom-select"}),
                                        choices=LightingPreset.choices,
                                        required=False)

    env_brightness = forms.FloatField(label=custom_label('Brightness'),
                                      widget=forms.NumberInput(attrs={'class': "form-control"}),
                                      min_value=0.0,
                                      initial=1.0,
                                      required=False)

    env_size = forms.FloatField(label=custom_label('Size'),
                                widget=forms.NumberInput(attrs={'class': "form-control"}),
                                min_value=0.001,
                                initial=10,
                                required=False)
    env_height = forms.FloatField(label=custom_label('Height'),
                                  widget=forms.NumberInput(attrs={'class': "form-control"}),
                                  min_value=-0.5,
                                  max_value=0.5,
                                  initial=0.0,
                                  required=False)
    env_rotation = forms.FloatField(label=custom_label('Rotation'),
                                    widget=forms.NumberInput(attrs={'class': "form-control"}),
                                    min_value=0.0,
                                    max_value=360.0,
                                    initial=0.0,
                                    required=False)

    env_lighting_environment = forms.ChoiceField(label=custom_label('Lighting Environment'),
                                                 choices=[(None, 'None'), ],
                                                 widget=forms.Select(attrs={'class': "custom-select"}),
                                                 required=False)

    env_background_color = forms.CharField(label=custom_label('Color'),
                                           initial='#cc00cc',
                                           widget=forms.TextInput(attrs={'type': "color"}),
                                           required=False)

    env_backplate_image = forms.ChoiceField(label=custom_label('Backplate Image'),
                                            choices=[(None, 'None'), ],
                                            widget=forms.Select(attrs={'class': "custom-select"}),
                                            required=False)

    env_ground_shadows = forms.BooleanField(label=custom_boolean_label('Ground Shadows', 'id_env_ground_shadows'),
                                            widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                            required=False)

    env_occlusion_ground_shadows = forms.BooleanField(label=custom_boolean_label('Occlusion Ground Shadows',
                                                                                 'id_env_occlusion_ground_shadows'),
                                                      widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                      required=False)

    env_ground_reflections = forms.BooleanField(label=custom_boolean_label('Ground Reflections',
                                                                           'id_env_ground_reflections'),
                                                widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                required=False)

    env_flatten_ground = forms.BooleanField(label=custom_boolean_label('Flatten Ground', 'id_env_flatten_ground'),
                                            widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                            required=False)

    env_ground_size = forms.FloatField(label=custom_label('Ground Size'),
                                       widget=forms.NumberInput(attrs={'class': "form-control"}),
                                       min_value=0.0, initial=10,
                                       required=False)

    # image-style override settings
    imgstyl_override = forms.BooleanField(label=custom_boolean_label('Override Image Style Settings',
                                                                     'id_imgstyl_override'),
                                          widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                          required=False)

    imgstyl_kind = forms.ChoiceField(label=custom_label("Image Style Mode"),
                                     widget=forms.Select(attrs={'class': "custom-select"}),
                                     choices=ImageStyleMode.choices,
                                     required=False)

    imgstyl_vignette = forms.BooleanField(label=custom_boolean_label('Vignette', 'id_imgstyl_vignette'),
                                          widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                          required=False)

    imgstyl_bloom = forms.BooleanField(label=custom_boolean_label('Bloom', 'id_imgstyl_bloom'),
                                       widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                       required=False)

    imgstyl_chromatic_aberration = forms.BooleanField(label=custom_boolean_label('Chromatic Aberration',
                                                                                 'id_imgstyl_chromatic_aberration'),
                                                      widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                                      required=False)

    imgstyl_color = forms.BooleanField(label=custom_boolean_label('Color (Photographic Mode Only)', 'id_imgstyl_color'),
                                       widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                       required=False)

    imgstyl_curve = forms.BooleanField(label=custom_boolean_label('Curve', 'id_imgstyl_curve'),
                                       widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                       required=False)

    imgstyl_denoise = forms.BooleanField(label=custom_boolean_label('Denoise', 'id_imgstyl_denoise'),
                                         widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                         required=False)

    use_network_rendering = forms.BooleanField(label=custom_boolean_label('Distributed Rendering',
                                                                          'id_use_network_rendering'),
                                               widget=forms.CheckboxInput(attrs={'class': "custom-control-input"}),
                                               required=False)

    def __init__(self, *args, **kwargs):
        super(AdvancedKeyShotJobForm, self).__init__(*args, **kwargs)


class SubmitFileSelectForm(forms.Form):

    file_data = forms.CharField(widget=forms.HiddenInput)
    file_storage = forms.ModelChoiceField(label=_("Storage"),
                                          queryset=FileStorage.objects.all(),
                                          initial=FileStorage.objects.first,
                                          widget=forms.Select(attrs={'class': "form-control"}))

    def __init__(self, *args, **kwargs):
        super(SubmitFileSelectForm, self).__init__(*args, **kwargs)
