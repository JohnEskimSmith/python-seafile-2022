import requests
import re
from typing import Optional, Callable
from sys import exit

from seafileapi.utils import urljoin, is_ascii
from seafileapi.exceptions import ClientHttpError
from seafileapi.repos import Repos


request_filename_pattern = re.compile(b'filename\*=.*')

seahub_api_auth_token = 40


class SeafileApiClient:
    """Wraps seafile web api"""
    def __init__(self, server: str,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 token: Optional[str] = None,
                 verify_ssl: bool = True):
        """Wraps various basic operations to interact with seahub http api.
        """
        self.server = server
        self.username = username
        self.password = password
        self._token = token
        self.verify_ssl = verify_ssl
        self.default_timeout = 120
        self.repos = Repos(self)
        self.groups = Groups(self)

        if token is None:
            self._get_token()

    def _get_token(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        url = urljoin(self.server, '/api2/auth-token/')
        try:
            with requests.post(url, data=data, verify=self.verify_ssl, timeout=self.default_timeout) as resp:
                if resp.status_code != 200:
                    raise ClientHttpError(resp.status_code, resp.content)
                try:
                    _token = resp.json()
                except Exception as e:
                    print(e, flush=True)
                else:
                    self._token = _token.get('token', '')
                    if len(self._token) != seahub_api_auth_token:
                        exit('The length of seahub api auth token should be 40')
        except Exception as e:
            exit(e)

    def __str__(self):
        return 'SeafileApiClient[server=%s, user=%s]' % (self.server, self.username)

    __repr__ = __str__

    def get(self, *args, **kwargs):
        return self._send_request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._send_request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._send_request('PUT', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._send_request('DELETE', *args, **kwargs)

    def _rewrite_request(self, *args, **kwargs):
        def func(prepared_request):
            if 'files' in kwargs:
                file = kwargs['files'].get('file', None)
                if file and isinstance(file[0], str):
                    filename = file[0]
                    if not is_ascii(filename):
                        filename = (filename + '"\r').encode('utf-8')
                        prepared_request.body = request_filename_pattern.sub(b'filename="' + filename, prepared_request.body, count=1)

            return prepared_request
        return func

    def _send_request(self, method: str, url: str, *args, **kwargs) -> Optional[requests.Response]:
        if not url.startswith('http'):
            url = urljoin(self.server, url)

        headers = kwargs.get('headers', {})
        headers.setdefault('Authorization', 'Token ' + self._token)
        kwargs['headers'] = headers

        expected = kwargs.pop('expected', 200)
        if not hasattr(expected, '__iter__'):
            expected = (expected, )

        # my some dirty hack to rewrite post body
        kwargs['auth']: Optional[Callable] = self._rewrite_request(*args, **kwargs)  # hack to rewrite post body

        kwargs['method'] = method
        kwargs['url'] = url
        kwargs['verify'] = self.verify_ssl
        kwargs['timeout'] = self.default_timeout
        try:
            resp = requests.request(*args, **kwargs)
        except Exception as e:
            print(e, flush=True)
        else:
            if resp.status_code not in expected:
                msg = 'Expected %s, but get %s' % \
                      (' or '.join(map(str, expected)), resp.status_code)
                raise ClientHttpError(resp.status_code, msg)
            return resp


class Groups:
    def __init__(self, client):
        pass

    def create_group(self, name):
        pass
