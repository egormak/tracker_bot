from unittest.mock import patch, MagicMock
from tracker import timer, rest, const

def test_timer_adjust():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res = timer.TimerAdjust("coding", 5)
        assert "Adjusted timer for 'coding' by +5 min" in res
        mock_post.assert_called_once_with(const.TIMER_RUN_ADJUST, json={"task_name": "coding", "delta_minutes": 5})

def test_rest_get():
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"rest_time": 3000})
        res = rest.GetRest()
        assert "Available rest time: 30.0 minutes" in res
        mock_get.assert_called_once_with(const.REST_GET_URI)
