import pytest
from pydantic import ValidationError

from repositories.exceptions import ModelValidationException
from repositories.models import Change, PromptFixRequest, PromptFixRequestOutput


def test_defaults_are_watch_and_30():
    req = PromptFixRequest(script="hi")
    assert req.mode == "watch"
    assert req.length == 30


def test_sell_requires_audience_and_cta():
    with pytest.raises(ModelValidationException):
        PromptFixRequest(mode="sell", script="hi", target_audience="coaches")
    with pytest.raises(ModelValidationException):
        PromptFixRequest(mode="sell", script="hi", call_to_action="follow me")


def test_sell_accepts_both():
    req = PromptFixRequest(
        mode="sell",
        script="hi",
        target_audience="new coaches",
        call_to_action="follow me",
    )
    assert req.target_audience == "new coaches"
    assert req.call_to_action == "follow me"


def test_watch_mode_nulls_audience_and_cta():
    req = PromptFixRequest(mode="watch", script="hi", target_audience="x", call_to_action="y")
    assert req.target_audience is None
    assert req.call_to_action is None


def test_whitespace_only_script_rejected():
    with pytest.raises(ValidationError):
        PromptFixRequest(script="   ")


def test_whitespace_audience_rejected_in_sell():
    with pytest.raises(ModelValidationException):
        PromptFixRequest(mode="sell", script="hi", target_audience="   ", call_to_action="x")


@pytest.mark.parametrize("bad_length", [15, 45, 120, "30"])
def test_invalid_length_rejected(bad_length):
    with pytest.raises(ValidationError):
        PromptFixRequest(script="hi", length=bad_length)


def test_invalid_mode_rejected():
    with pytest.raises(ValidationError):
        PromptFixRequest(mode="other", script="hi")


def test_change_rejects_end_before_start():
    with pytest.raises(ModelValidationException):
        Change(start_char=10, end_char=5, reason="x")


def test_output_defaults():
    out = PromptFixRequestOutput(script="s", info="i")
    assert out.error is None
    assert out.changes == []


def test_output_parses_from_json():
    raw = (
        '{"script": "s", "info": "i", "error": null, '
        '"changes": [{"start_char": 0, "end_char": 1, "reason": "r"}]}'
    )
    out = PromptFixRequestOutput.model_validate_json(raw)
    assert out.changes[0].reason == "r"
