import json
from django import forms
from django.contrib import admin
from advanced_filters.admin import AdminAdvancedFiltersMixin
from django.core.validators import RegexValidator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html
from django_admin_relation_links import AdminChangeLinksMixin
from django_json_widget.widgets import JSONEditorWidget
from django.utils.translation import gettext_lazy as _

from job.models import *


class JobCostActions(models.TextChoices):
    REFUND = 'refund', _('Refund Job')
    COST_BALANCE = 'cost_balance', _('Balance Job Cost')


class EditJobCostForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    cost_action = forms.ChoiceField(label=_("Cost Action"),
                                    choices=JobCostActions.choices,
                                    widget=forms.Select())
    amount = forms.FloatField(label=_("Amount"),
                              required=False,
                              validators=[RegexValidator(r'^[0-9+]', 'Only digit characters.'), ],
                              widget=forms.NumberInput())


class SoftwareVersionAdmin(admin.ModelAdmin):
    list_display = ['plugin_name',
                    'software',
                    'icon',
                    'version',
                    'access_type',
                    'deadline_pool',
                    'deadline_group']

    list_editable = [
                     'software',
                     'icon',
                     'version',
                     'access_type',
                     'deadline_pool',
                     'deadline_group']

    list_display_links = ['plugin_name']


class JobTaskInlineAdmin(admin.StackedInline):
    model = JobTask
    extra = 0


class SoftwareAdmin(admin.ModelAdmin):
    list_display = ['name']


def resubmit_job(modeladmin, request, queryset):
    for job in queryset:
        job.resubmit()


class JobAdmin(AdminChangeLinksMixin, AdminAdvancedFiltersMixin, admin.ModelAdmin):
    list_display = ['icon',
                    'name',
                    'user_link',
                    'user_profile_link',
                    'software_version',
                    'frame_list',
                    'render_plan',
                    'deadline_id',
                    'cost',
                    'status',
                    'progress',
                    'date_created',
                    'date_modified']
    list_filter = ['status', 'render_plan', 'software_version__software', 'file_storage']
    advanced_filter_fields = ('name', 'user__username', ('status__display_name', 'status'), 'deadline_id')
    inlines = [JobTaskInlineAdmin, ]
    actions = [resubmit_job, 'edit_cost']
    search_fields = ['user__username', 'deadline_id', 'name', 'status__name', 'date_created']
    resubmit_job.short_description = "Re-submit"
    change_links = ['user', 'user_profile']
    list_display_links = ['name']

    formfield_overrides = {models.JSONField: {'widget': JSONEditorWidget}, }

    def icon(self, obj):
        html = '<img src="{url}" width="{width}"height={height} />'
        return format_html(html.format(url=obj.software_version.icon.url, width=20, height=20))

    def edit_cost(self, request, queryset):
        if 'apply' in request.POST:
            cost_action = request.POST["cost_action"]

            try:
                amount = float(request.POST["amount"])
            except:
                amount = 0.0

            if cost_action == JobCostActions.REFUND:
                for item in queryset:
                    self.message_user(request, f"Refund has been made for {item.name} : {item.cost}")
                    item.refund()
            elif cost_action == JobCostActions.COST_BALANCE:
                for item in queryset:
                    item.cost_balance(amount)
                    self.message_user(request, f"Cost balanced on {item.name} : {item.cost}")

            return HttpResponseRedirect(request.get_full_path())

        form = EditJobCostForm(initial={'_selected_action': queryset.values_list('id', flat=True)})
        return render(request, "admin/edit_job_cost.html", {'items': queryset, 'form': form})


class RenderPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'id', 'rate_per_min', 'deadline_machine_limit', 'deadline_priority']
    list_editable = ['display_name', 'rate_per_min', 'deadline_machine_limit', 'deadline_priority']


class JobErrorAdmin(admin.ModelAdmin):
    list_display = ['software', 'error', 'description', 'solution']
    list_editable = ['error', 'description', 'solution']
    list_display_links = ['software']


class JobStatusAdmin(admin.ModelAdmin):
    list_display = ['name',
                    'display_name',
                    'admin_only',
                    'description',
                    'is_suspendable',
                    'is_deletable',
                    'is_upgradable']
    list_editable = ['display_name', 'description', 'is_suspendable', 'is_deletable', 'is_upgradable']
    list_display_links = ['name']


class JobTaskAdmin(admin.ModelAdmin):
    list_display = ['job',
                    'deadline_task_id',
                    'cost',
                    'cpu_usage',
                    'frame_list',
                    'render_time',
                    'render_time_string',
                    ]

    list_display_links = ['job']
    list_editable = ['cost']
    search_fields = ['job__name']


class SubmitSessionAdmin(AdminChangeLinksMixin, AdminAdvancedFiltersMixin, admin.ModelAdmin):
    list_display = ['session_id',
                    'user']
    list_filter = ['session_id', 'user']
    advanced_filter_fields = ('session_id', 'user__username')
    search_fields = ['user__username', 'session_id']
    change_links = ['user', 'user_profile']
    list_display_links = ['session_id']

    formfield_overrides = {models.JSONField: {'widget': JSONEditorWidget}, }


admin.site.register(FileFormat)
admin.site.register(OutputFormat)
admin.site.register(RenderPlan, RenderPlanAdmin)
admin.site.register(JobError, JobErrorAdmin)
admin.site.register(FileStorage)
admin.site.register(Software, SoftwareAdmin)
admin.site.register(SoftwareVersion, SoftwareVersionAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(JobTask, JobTaskAdmin)
admin.site.register(JobStatus, JobStatusAdmin)
admin.site.register(SubmitSession, SubmitSessionAdmin)
