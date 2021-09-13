from rest_framework import serializers
from system.models import Setting
from job.models import FileStorage


class ClientAppSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ['client_app_setting', ]


class SystemStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ['system_status', ]


class FileStorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileStorage
        fields = ['setting', ]

