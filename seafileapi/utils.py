from functools import wraps
import random
import string
from typing import Any, List, Dict, Union, Callable
from urllib.parse import urlencode

from seafileapi.exceptions import ClientHttpError, DoesNotExist


def randstring(length: int) -> str:
    if length == 0:
        return ''.join(random.choice(string.ascii_lowercase) for _ in range(random.randint(1, 30)))
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))


def urljoin(base: str, *args) -> str:
    url = base
    if url[-1] != '/':
        url += '/'
    for arg in args:
        arg = arg.strip('/')
        url += arg + '/'
    if '?' in url:
        url = url[:-1]
    return url


def raise_does_not_exist(msg) -> Callable:
    """Decorator to turn a function that get a http 404 response to a
    :exc:`DoesNotExist` exception."""
    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientHttpError as e:
                if e.code == 404:
                    raise DoesNotExist(msg)
                else:
                    raise
        return wrapped
    return decorator


def to_utf8(obj) -> Any:
    return obj


def querystr(**kwargs) -> str:
    return '?' + urlencode(kwargs)


def utf8lize(obj: Any) -> Union[List, Dict, Any]:
    if isinstance(obj, dict):
        return {k: to_utf8(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [to_utf8(x) for x in obj]

    return obj


def is_ascii(text) -> bool:
    try:
        text.encode('ascii')
    except UnicodeEncodeError:
        return False
    return True
