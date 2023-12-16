from dataclasses import dataclass
from functools import wraps
import traceback


@dataclass(frozen=True, order=True)
class HTTPException(Exception):
    message: str
    status_code: int


def error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            return result

        except HTTPException as e:
            return e.message, e.status_code

        except Exception as e:
            print(traceback.format_exc())
            return str(e), 500

    return decorated_function
