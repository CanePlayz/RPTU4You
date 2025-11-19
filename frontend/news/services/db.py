from functools import wraps

from django.db import connection


def close_db_connection(func):
    """Decorator that ensures Django closes the DB connection after the wrapped call."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            connection.close()

    return wrapper
