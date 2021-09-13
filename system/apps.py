from django.apps import AppConfig


class SystemConfig(AppConfig):
    name = 'system'

    def ready(self):
        try:
            from system.models import SocketConnection
            SocketConnection.objects.all().delete()
        except Exception as err:
            pass