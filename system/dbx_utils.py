import os
import logging

import dropbox
import dropbox.exceptions
import packaging.version

from job.models import FileStorage

logger = logging.getLogger('DBX')


class DropboxHandler:
    def __init__(self, user):
        self.user = user
        self.dropbox = None
        self._timeout = 60

        self._token = ''
        self._sources_root = ''
        self._outputs_root = ''
        self._utilities_root = ''

        self._set_db_data()
        self._init_dropbox()

    def _set_db_data(self):
        try:
            self.dropbox_storage = FileStorage.objects.filter(name='RenderShare').first()
            self._token = self.dropbox_storage.setting.get('token')
            self._sources_root = self.dropbox_storage.setting.get('sources_root')
            self._outputs_root = self.dropbox_storage.setting.get('outputs_root')
            self._utilities_root = self.dropbox_storage.setting.get('utilities_root')
        except Exception as err:
            logger.exception(err)

    def _init_dropbox(self):
        try:
            self.dropbox = dropbox.Dropbox(self._token, timeout=self._timeout)
        except Exception as err:
            logger.exception(err)
            self.dropbox = None

    def get_rendershare_installers(self, package_type, os_type, version=''):

        if package_type == 'updater':
            ext = '.zip'
        elif os_type == 'win':
            ext = '.exe'
        elif os_type == 'mac':
            ext = '.dmg'
        else:
            logger.warning(f"os type is not supported : {os_type}")
            return {}

        package_dir = os.path.join(self._utilities_root,
                                   f'rendershare_{package_type}',
                                   os_type)

        data = {f'{os_type}_{package_type}_url': '',
                f'{os_type}_{package_type}_version': ''}

        request_version = version

        version_entries = []
        try:
            version_entries = self.dropbox.files_list_folder(package_dir).entries
        except Exception as err:
            logger.exception(err)

        if not version_entries:
            logger.warning(f"render share {package_type} folder is empty , no version found : {package_dir}")
            return data

        version_dict = dict()
        for entry in version_entries:
            version_dict[entry.name] = entry

        if request_version and request_version in version_dict.keys():
            target_version = request_version
        else:
            target_version = sorted(version_dict.keys(), key=packaging.version.parse)[-1]

        if not target_version:
            logger.warning(f"requested version could not be found : {request_version} - {target_version}")
            return data
        else:
            o_target_version = version_dict.get(target_version)
            logger.info(f"target version found : {target_version} - {o_target_version.path_display}")

        if o_target_version:
            data[f'{os_type}_{package_type}_url'] = self.get_download_link(os.path.join(o_target_version.path_display,
                                                                                        f'{package_type}{ext}'))
            data[f'{os_type}_{package_type}_version'] = o_target_version.name

        logger.info(f"{package_type}s found : {data}")
        return data

    def get_list_of_source_files(self, formats):
        list_of_files = []
        try:
            admin_entries = self.dropbox.files_list_folder(self._sources_root).entries
        except Exception as e:
            logger.exception(e)
            return list_of_files

        if self.user.username not in [entry.name for entry in admin_entries]:
            logger.warning(f"{self.user.username} have no dropbox folder")
            return list_of_files

        path = os.path.join(self._sources_root, self.user.username).replace('\\', "/")
        try:
            for entry in self.dropbox.files_list_folder(path).entries:
                sub_path = os.path.join(self._sources_root, self.user.username, entry.name).replace('\\', "/")
                for sub_entry in self.dropbox.files_list_folder(sub_path).entries:
                    name, ext = os.path.splitext(sub_entry.name)
                    if ext in formats:
                        list_of_files.append(sub_entry)
        except Exception as e:
            logger.exception(e)
            return list_of_files

        return list_of_files

    def get_list_of_output_folders(self):
        folders = []
        entries = []
        try:
            entries = self.dropbox.files_list_folder(self.get_user_outputs_path()).entries
        except Exception as e:
            logger.exception(e)

        if entries:
            folders = [entry.name for entry in entries]
        logger.warning(f"{len(entries)} found in {self.user.username} output directory.")
        return folders

    def get_user_outputs_path(self):
        return os.path.join(self._outputs_root, self.user.username).replace('\\', "/")

    def get_job_output_path(self, job_name):
        return os.path.join(self.get_user_outputs_path(), job_name).replace('\\', "/")

    def get_share_link(self, path):
        exist_links = self.dropbox.sharing_get_shared_links(path=path)
        revoke_url = ''
        if exist_links.links:
            logger.debug(f"shared link already exist {path}:{exist_links.links}")
            shared_link = exist_links.links[0]
            if shared_link.path == path:
                url = shared_link.url
                return url
            else:
                revoke_url = shared_link.url

        if revoke_url:
            logger.debug(f"revoking already exist url {revoke_url}")
            self.dropbox.sharing_revoke_shared_link(revoke_url)

        exist_links = self.dropbox.sharing_get_shared_links(path=path)
        if exist_links.links:
            logger.debug(f"get shared links for {path} {exist_links.links[0].url}")
            return exist_links.links[0].url
        else:
            logger.debug(f"ask for new share link for {path}")
            link = self.dropbox.sharing_create_shared_link_with_settings(path=path)
            return link.url

    def get_user_outputs_link(self):

        url = ''
        try:
            path = self.get_user_outputs_path()
            url = self.get_share_link(path)
            if not url:
                logger.debug(f"could not get shared link for {path}")
                return ''
        except Exception as err:
            logger.exception(err)
        return url

    def get_user_outputs_share_link(self):
        url = ''
        try:
            path = self.get_user_outputs_path()
            sharing_folder = self.dropbox.sharing_share_folder(path)
            if sharing_folder.is_complete():
                sharing_folder_data = sharing_folder.get_complete()
                url = sharing_folder_data.preview_url
        except dropbox.exceptions.ApiError as err:
            logger.exception(err)
        except Exception as err:
            logger.exception(err)
        return url

    def get_job_output_link(self, job_name):
        url = ''
        try:
            path = self.get_job_output_path(job_name)
            url = self.get_share_link(path)
            if not url:
                logger.debug(f"could not get job output link for {path}")
                return ''
        except Exception as err:
            logger.exception(err)
        return url

    def get_user_sources_path(self):
        return os.path.join(self._sources_root, self.user.username).replace('\\', "/")

    def get_user_paths(self):
        return [self.get_user_outputs_path(), self.get_user_sources_path()]

    def create_user_folders(self):
        paths = self.get_user_paths()
        logger.debug(f"creating {self.user.username} dropbox folders : {paths}")
        try:
            self.dropbox.files_create_folder_batch(paths)
        except Exception as err:
            logger.exception(err)

    def delete_user_folders(self):
        paths = self.get_user_paths()
        logger.debug(f"deleting {self.user.username} dropbox folders : {paths}")
        try:
            for path in paths:
                self.dropbox.files_delete_v2(path)
        except Exception as err:
            logger.exception(err)

    def get_file_matadata(self, file_path):
        meta_data = None
        try:
            meta_data = self.dropbox.files_get_metadata(file_path)
        except Exception as err:
            logger.exception(err)

        return meta_data

    def get_link_metadata(self, url):
        meta_data = None
        try:
            meta_data = self.dropbox.sharing_get_shared_link_metadata(url)
        except Exception as err:
            logger.exception(err)

        return meta_data

    def get_download_link(self, file_path):
        link = None
        try:
            link = self.dropbox.files_get_temporary_link(file_path).link
        except Exception as err:
            logger.exception(err)

        return link


if __name__ == "__main__":
    dbx = DropboxHandler()
    dbx.get_list_of_source_files()
