from seafileapi.client import SeafileApiClient


def connect(server: str, username: str, password: str, token=None, verify_ssl=True) -> SeafileApiClient:
    client = SeafileApiClient(server, username, password, token, verify_ssl)
    return client
