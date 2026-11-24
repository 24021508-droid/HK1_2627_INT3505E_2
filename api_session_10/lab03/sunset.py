import logging
from datetime import datetime, timezone
from email.utils import format_datetime
from functools import wraps

from flask import current_app, request

log = logging.getLogger("sunset")


def deprecate_at(sunset_date, replacement=None):
    """Retire a Flask route at a timezone-aware datetime."""
    if sunset_date.utcoffset() is None:
        raise ValueError("sunset_date must include a timezone")

    sunset_date = sunset_date.astimezone(timezone.utc)
    sunset_header = format_datetime(sunset_date, usegmt=True)

    def decorate(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            log.warning("deprecated_call %s %s", request.path, request.remote_addr)

            if datetime.now(timezone.utc) >= sunset_date:
                result = {"error": "gone", "sunset": sunset_header,
                          "use_instead": replacement}, 410
            else:
                result = view(*args, **kwargs)

            response = current_app.make_response(result)
            response.headers["Sunset"] = sunset_header
            response.headers["Deprecation"] = "true"
            if replacement:
                response.headers.add("Link", f'<{replacement}>; rel="successor-version"')
            return response

        return wrapper

    return decorate
