import os
from unittest.mock import MagicMock, patch

import pytest

from agisdk.REAL.browsergym.webclones.base import get_run_id_from_api


@pytest.fixture(autouse=True)
def restore_real_api_base():
    original = os.environ.get("REAL_API_BASE")
    try:
        if "REAL_API_BASE" in os.environ:
            del os.environ["REAL_API_BASE"]
        yield
    finally:
        if original is None:
            os.environ.pop("REAL_API_BASE", None)
        else:
            os.environ["REAL_API_BASE"] = original


def _mock_response():
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"newRunId": "dummy"}
    return response


def test_default_domain_is_used_when_env_not_set():
    with patch("agisdk.REAL.browsergym.webclones.base.requests.get") as mock_get:
        mock_get.return_value = _mock_response()

        get_run_id_from_api("API", "my model", "my run")

        expected = (
            "https://www.realevals.ai/api/runKey?"
            "api_key=API&model_name=my%20model&run_name=my%20run"
        )
        mock_get.assert_called_once_with(expected, timeout=10)


def test_domain_can_be_overridden_with_env():
    os.environ["REAL_API_BASE"] = "https://custom.example.com"
    with patch("agisdk.REAL.browsergym.webclones.base.requests.get") as mock_get:
        mock_get.return_value = _mock_response()

        get_run_id_from_api("API", "foo", "bar")

        expected = "https://custom.example.com/api/runKey?api_key=API&model_name=foo&run_name=bar"
        mock_get.assert_called_once_with(expected, timeout=10)
