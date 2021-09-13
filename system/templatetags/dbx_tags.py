from django.template import Library
from system.dbx_utils import DropboxHandler

register = Library()


@register.simple_tag
def dbx_user_outputs_link(user):
    dbx = DropboxHandler(user)
    user_outputs_link = dbx.get_user_outputs_link()
    return user_outputs_link or "#"


@register.simple_tag
def dbx_job_output_link(user, job_name):
    dbx = DropboxHandler(user)
    job_output_link = dbx.get_job_output_link(job_name)
    return job_output_link


@register.simple_tag
def dbx_rendershare_win_download_link(user):
    dbx = DropboxHandler(user)
    os_type = 'win'
    package_type = 'installer'
    param = f'{os_type}_{package_type}_url'
    link = dbx.get_rendershare_installers(package_type=package_type, os_type=os_type).get(param)
    return link or "#"


@register.simple_tag
def dbx_rendershare_mac_download_link(user):
    dbx = DropboxHandler(user)
    os_type = 'mac'
    package_type = 'installer'
    param = f'{os_type}_{package_type}_url'
    link = dbx.get_rendershare_installers(package_type=package_type, os_type=os_type).get(param)
    return link or "#"


@register.simple_tag
def dbx_get_user_outputs_share_link(user):
    url = user.profile.dropbox_outputs_share_link
    if url:
        return url

    dbx = DropboxHandler(user)
    url = dbx.get_user_outputs_share_link()
    if url:
        user.profile.dropbox_outputs_share_link = url
        user.save()

    return url or "#"



