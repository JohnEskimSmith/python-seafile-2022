import io
import os
import posixpath
import re
from typing import Optional, Union, Any

from seafileapi.utils import querystr, utf8lize

ZERO_OBJ_ID = '0000000000000000000000000000000000000000'


class _SeafDirentBase:
    """Base class for :class:`SeafFile` and :class:`SeafDir`.

    It provides implementation of their common operations.
    """
    isdir = None

    def __init__(self, repo, path, object_id, size=0):
        """
        :param:`path` the full path of this entry within its repo, like
        "/documents/example.md"

        :param:`size` The size of a file. It should be zero for a dir.
        """
        self.client = repo.client
        self.repo = repo
        self.path = path
        self.id = object_id
        self.size = size

    @property
    def name(self):
        return posixpath.basename(self.path)

    def list_revisions(self):
        pass

    def delete(self):
        suffix = 'dir' if self.isdir else 'file'
        url = f'/api2/repos/{self.repo.id}/{suffix}/' + querystr(p=self.path)
        resp = self.client.delete(url)
        return resp

    def rename(self, newname) -> bool:
        """Change file/folder name to newname
        """
        suffix = 'dir' if self.isdir else 'file'
        url = f'/api2/repos/{self.repo.id}/{suffix}/' + querystr(p=self.path, reloaddir='true')
        postdata = {'operation': 'rename',
                    'newname': newname}
        response = self.client.post(url, data=postdata)
        succeeded = False
        if response:
            if response.status_code == 200:
                if self.isdir:
                    new_dirent = self.repo.get_dir(os.path.join(os.path.dirname(self.path), newname))
                else:
                    new_dirent = self.repo.get_file(os.path.join(os.path.dirname(self.path), newname))
                for key in self.__dict__.keys():
                    self.__dict__[key] = new_dirent.__dict__[key]
                succeeded = True
        return succeeded

    def _copy_move_task(self, operation, dirent_type, dst_dir, dst_repo_id=None):
        url = '/api/v2.1/copy-move-task/'
        src_repo_id = self.repo.id
        src_parent_dir = os.path.dirname(self.path)
        src_dirent_name = os.path.basename(self.path)
        dst_repo_id = dst_repo_id
        dst_parent_dir = dst_dir
        operation = operation
        dirent_type = dirent_type
        postdata = {'src_repo_id': src_repo_id,
                    'src_parent_dir': src_parent_dir,
                    'src_dirent_name': src_dirent_name,
                    'dst_repo_id': dst_repo_id,
                    'dst_parent_dir': dst_parent_dir,
                    'operation': operation,
                    'dirent_type': dirent_type}
        return self.client.post(url, data=postdata)

    def copyTo(self, dst_dir, dst_repo_id=None) -> bool:
        """Copy file/folder to other directory (also to a different repo)
        """
        if dst_repo_id is None:
            dst_repo_id = self.repo.id

        dirent_type = 'dir' if self.isdir else 'file'
        resp = self._copy_move_task('copy', dirent_type, dst_dir, dst_repo_id)
        if resp:
            return resp.status_code == 200
        return False

    def moveTo(self, dst_dir, dst_repo_id=None):
        """Move file/folder to other directory (also to a different repo)
        """
        if dst_repo_id is None:
            dst_repo_id = self.repo.id

        dirent_type = 'dir' if self.isdir else 'file'
        response = self._copy_move_task('move', dirent_type, dst_dir, dst_repo_id)

        succeeded = False
        if response:
            if response.status_code == 200:
                new_repo = self.client.repos.get_repo(dst_repo_id)
                dst_path = os.path.join(dst_dir, os.path.basename(self.path))
                if self.isdir:
                    new_dirent = new_repo.get_dir(dst_path)
                else:
                    new_dirent = new_repo.get_file(dst_path)
                if new_dirent:
                    for key in self.__dict__.keys():
                        self.__dict__[key] = new_dirent.__dict__[key]
                    succeeded = True
        return succeeded

    def get_share_link(self,
                       can_edit=False,
                       can_download=True,
                       password=None,
                       expire_days=None,
                       direct_link=True) -> Optional[str]:

        url = '/api/v2.1/share-links/'
        post_data = {
            "repo_id": self.repo.id,
            "path": self.path,
            "permissions": {
                "can_edit": can_edit,
                "can_download": can_download
            }
        }
        if password:
            post_data['password'] = password
        if expire_days:
            post_data['expire_days'] = expire_days
        response = self.client.post(url, data=post_data)
        if response:
            try:
                data = response.json()
                link = data['link']
                if direct_link:
                    link = link + '?dl=1'
                return link
            except Exception as e:
                print(e, flush=True)


class SeafDir(_SeafDirentBase):
    isdir = True

    def __init__(self, *args, **kwargs):
        super(SeafDir, self).__init__(*args, **kwargs)
        self.entries = None
        self.entries = kwargs.pop('entries', None)

    def ls(self, force_refresh=False):
        """List the entries in this dir.

        Return a list of objects of class :class:`SeafFile` or :class:`SeafDir`.
        """
        if self.entries is None or force_refresh:
            self.load_entries()

        return self.entries

    def share_to_user(self, email, permission) -> bool:
        url = f'/api2/repos/{self.repo.id}/dir/shared_items/' + querystr(p=self.path)
        putdata = {
            'share_type': 'user',
            'username': email,
            'permission': permission
        }
        response = self.client.put(url, data=putdata)
        if response:
            return response.status_code == 200
        else:
            print(f'errors with share: {email}, {permission}')
        return False

    def create_empty_file(self, name) -> Optional["SeafFile"]:
        """Create a new empty file in this dir.
        Return a :class:`SeafFile` object of the newly created file.
        """
        # TODO: file name validation
        path = posixpath.join(self.path, name)
        url = f'/api2/repos/{self.repo.id}/file/' + querystr(p=path, reloaddir='true')
        postdata = {'operation': 'create'}
        response = self.client.post(url, data=postdata)
        if response:
            try:
                self.id = response.headers['oid']
                self.load_entries(response.json())
                return SeafFile(self.repo, path, ZERO_OBJ_ID, 0)
            except Exception as e:
                print(e, flush=True)

    def mkdir(self, name) -> Optional["SeafDir"]:
        """Create a new sub folder right under this dir.

        Return a :class:`SeafDir` object of the newly created sub folder.
        """
        path = posixpath.join(self.path, name)
        url = f'/api2/repos/{self.repo.id}/dir/' + querystr(p=path, reloaddir='true')
        postdata = {'operation': 'mkdir'}
        response = self.client.post(url, data=postdata)
        if response:
            try:
                self.id = response.headers['oid']
                self.load_entries(response.json())
                return SeafDir(self.repo, path, ZERO_OBJ_ID)
            except Exception as e:
                print(e, flush=True)

    def upload(self, fileobj, filename: str, replace=False) -> Optional["SeafFile"]:
        """Upload a file to this folder.

        :param:fileobj :class:`File` like object
        :param:filename The name of the file

        Return a :class:`SeafFile` object of the newly uploaded file.
        """
        if isinstance(fileobj, str):
            fileobj = io.BytesIO(fileobj.encode('utf-8'))  # so so solutions
        upload_url = self._get_upload_link()
        if upload_url:
            files = {
                'file': (filename, fileobj),
                'parent_dir': self.path,
                'replace': 1 if replace else 0,
            }
            response = self.client.post(upload_url, files=files)
            if response:
                try:
                    if response.ok:
                        return self.repo.get_file(posixpath.join(self.path, filename))
                except Exception as e:
                    print(e)
            else:
                print(f'error with response upload: {filename}')
        else:
            print(f'error with upload_url for: {filename}')

    def upload_local_file(self, filepath, name=None, replace=False) -> Optional["SeafFile"]:
        """Upload a file to this folder.

        :param:filepath The path to the local file
        :param:name The name of this new file. If None, the name of the local file would be used.

        Return a :class:`SeafFile` object of the newly uploaded file.
        """
        try:
            name = name or os.path.basename(filepath)
            fp = open(filepath, 'rb')
            return self.upload(fp, name, replace)
        except Exception as e:
            print(e, flush=True)

    def _get_upload_link(self):
        url = f'/api2/repos/{self.repo.id}/upload-link/' + querystr(p=self.path)
        response = self.client.get(url)
        if response:
            try:
                data = response.text
                return re.match(r'"(.*)"', data).group(1)
            except Exception as e:
                print(e, flush=True)

    def get_uploadable_sharelink(self):
        """Generate a uploadable shared link to this dir.

        Return the url of this link.
        """
        pass

    def load_entries(self, dirents_json=None) -> None:
        if dirents_json is None:
            url = '/api2/repos/%s/dir/' % self.repo.id + querystr(p=self.path)
            dirents_json = self.client.get(url).json()

        self.entries = [self._load_dirent(entry_json) for entry_json in dirents_json]

    def _load_dirent(self, dirent_json) -> Union["SeafFile", "SeafDir"]:
        dirent_json = utf8lize(dirent_json)
        path = posixpath.join(self.path, dirent_json['name'])
        if dirent_json['type'] == 'file':
            return SeafFile(self.repo, path, dirent_json['id'], dirent_json['size'])
        else:
            return SeafDir(self.repo, path, dirent_json['id'], 0)

    @property
    def num_entries(self) -> int:
        if self.entries is None:
            self.load_entries()
        return len(self.entries) if self.entries is not None else 0

    def __str__(self):
        return 'SeafDir[repo=%s,path=%s,entries=%s]' % \
            (self.repo.id[:6], self.path, self.num_entries)

    __repr__ = __str__


class SeafFile(_SeafDirentBase):
    isdir = False

    def _get_delete_link(self) -> str:
        url: str = '/api2/repos/%s/file/' % self.repo.id + querystr(p=self.path)
        return url

    def delete_file(self) -> Optional[bytes]:
        url: str = self._get_delete_link()
        if response := self.client.delete(url):
            if response.ok:
               return response.content

    def update(self, fileobj) -> None:
        """Update the content of this file"""
        pass

    def __str__(self):
        return 'SeafFile[repo=%s,path=%s,size=%s]' % \
            (self.repo.id[:6], self.path, self.size)

    def _get_download_link(self):
        url = '/api2/repos/%s/file/' % self.repo.id + querystr(p=self.path)
        resp = self.client.get(url)
        return re.match(r'"(.*)"', resp.text).group(1)

    def get_content(self) -> bytes:
        """Get the content of the file"""
        url = self._get_download_link()
        return self.client.get(url).content

    __repr__ = __str__
