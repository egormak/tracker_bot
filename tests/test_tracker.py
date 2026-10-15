from unittest.mock import patch, MagicMock
from tracker import timer, const

def test_timer_adjust():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        res = timer.TimerAdjust("coding", 5)
        assert "Adjusted timer for 'coding' by +5 min" in res
        mock_post.assert_called_once_with(const.TIMER_RUN_ADJUST, json={"task_name": "coding", "delta_minutes": 5})

