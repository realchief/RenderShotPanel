from system.models import Setting


def get_system_setting():
    target_config = None
    configs = Setting.objects.all()
    for cfg in configs:
        if cfg.is_active:
            target_config = cfg
            break

    return target_config
