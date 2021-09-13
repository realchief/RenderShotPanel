from rest_framework import serializers
from job.models import Job, SubmitSession


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'

    def to_representation(self, instance):
        data = super(JobSerializer, self).to_representation(instance)
        data['user'] = instance.user.username
        data['status'] = instance.status.name
        data['software_version'] = instance.software_version.version
        data['render_plan'] = instance.render_plan.name
        if instance.output_format:
            data['output_format'] = instance.output_format.extension
        if instance.file_storage:
            data['file_storage'] = instance.file_storage.name
        return data


class SubmitSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubmitSession
        fields = ['session_id', 'data', 'user']


