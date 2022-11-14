from urllib.parse import urlencode
from typing import Optional, List

from seafileapi.repo import Repo
from seafileapi.utils import raise_does_not_exist

class Repos:

    def __init__(self, client: "SeafileApiClient"):
        self.client = client

    def create_repo(self, name: str, password: Optional[str] = None):
        data = {'name': name}
        if password:
            data['passwd'] = password

        response = self.client.post('/api2/repos/', data=data)
        if response:
            try:
                data = response.json()
                if 'repo_id' in data:
                    return self.get_repo(data['repo_id'])
            except Exception as e:
                print(e, flush=True)

    @raise_does_not_exist('The requested library does not exist')
    def get_repo(self, repo_id):
        """Get the repo which has the id `repo_id`.

        Raises :exc:`DoesNotExist` if no such repo exists.
        """
        response = self.client.get(f'/api2/repos/{repo_id}')
        if response:
            try:
                repo_json = response.json()
                return Repo.from_json(self.client, repo_json)
            except Exception as e:
                print(e, flush=True)

    def list_repos(self, type=None) -> Optional[List[Repo]]:
        query = ''
        if type:
            query = '?' + urlencode(dict(type=type))
        response = self.client.get(f'/api2/repos/{query}')
        if response:
            try:
                repos_json = response.json()
                return [Repo.from_json(self.client, j) for j in repos_json]
            except Exception as e:
                print(e, flush=True)
