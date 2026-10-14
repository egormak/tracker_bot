from unittest.mock import patch

import requests

import config
from tracker import client_header, timer


def _install_with(captured):
    """Install the hook over a fake Session.request and return a restore function."""
    original = requests.Session.request

    def fake_request(self, method, url, **kwargs):
        captured.append((url, kwargs.get("headers")))
        return requests.Response()

    requests.Session.request = fake_request
    client_header._installed = False
    client_header.install()

    def restore():
        requests.Session.request = original
        client_header._installed = False

    return restore


def test_header_added_only_for_tracker_server():
    captured = []
    restore = _install_with(captured)
    try:
        app_url = config.config["app_url"]
        requests.get(f"{app_url}/api/v1/records")
        requests.post(f"{app_url}/api/v1/timer/run/start", json={}, headers={"X-Other": "1"})
        requests.get("https://example.invalid/elsewhere")
    finally:
        restore()

    assert captured[0][1] == {"X-Tracker-Client": "bot"}
    assert captured[1][1] == {"X-Other": "1", "X-Tracker-Client": "bot"}
    assert not captured[2][1]


def test_install_twice_wraps_once():
    captured = []
    restore = _install_with(captured)
    try:
        wrapped = requests.Session.request
        client_header.install()
        assert requests.Session.request is wrapped
    finally:
        restore()


def test_start_origin_is_sent_only_when_given():
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        timer.TimerStart("games", target_duration=15, origin="break")
        timer.TimerStart("work")
        mock_post.return_value.json.return_value = {"status": "success"}
        timer.start_task("video", target_duration=10, origin="combo")

    bodies = [call.kwargs["json"] for call in mock_post.call_args_list]
    assert bodies == [
        {"task_name": "games", "target_duration": 15, "origin": "break"},
        {"task_name": "work"},
        {"task_name": "video", "target_duration": 10, "origin": "combo"},
    ]
