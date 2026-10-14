"""Names this client in every request to tracker-server.

The server stores the `X-Tracker-Client` header on task records and in the weekly usage
counters. The tracker modules call `requests.get/post/...` directly, so the header is added
at the `requests.Session.request` level instead of in each call.
"""
import requests

import config

CLIENT_HEADER = "X-Tracker-Client"
CLIENT_NAME = "bot"

_installed = False


def install() -> None:
    """Add the client header to requests that go to the tracker server. Safe to call twice."""
    global _installed
    if _installed:
        return
    _installed = True

    app_url = config.config["app_url"]
    original = requests.Session.request

    def request(self, method, url, **kwargs):
        if isinstance(url, str) and url.startswith(app_url):
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault(CLIENT_HEADER, CLIENT_NAME)
            kwargs["headers"] = headers
        return original(self, method, url, **kwargs)

    requests.Session.request = request
