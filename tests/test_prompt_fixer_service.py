import asyncio

import pytest

import services.prompt_fixer_service as pfs_module
from repositories.models import PromptFixRequest, PromptFixRequestOutput
from services.exceptions import InvalidModelOutputException
from services.prompt_fixer_service import PromptFixerService
from utils import FakeLLMClient

_VALID_OUTPUT = '{"script": "fixed", "info": "ok", "error": null, "changes": []}'

_TEMPLATE = (
    "<role>ROLE TEXT</role>\n\n"
    "<script_writing_guidelines>TODO</script_writing_guidelines>\n\n"
    "<output_format>OUTPUT FORMAT</output_format>\n\n"
    "<security>SECURITY TEXT</security>\n\n"
    "<user_content>\n{{USER_CONTENT}}\n</user_content>"
)


def _setup(tmp_path, monkeypatch):
    (tmp_path / "script_fixer.txt").write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(pfs_module, "PROMPTS_DIR", tmp_path)


def _fix(tmp_path, monkeypatch, output=_VALID_OUTPUT, request=None):
    _setup(tmp_path, monkeypatch)
    fake = FakeLLMClient(output)
    service = PromptFixerService(fake)
    result = asyncio.run(service.fix(request or PromptFixRequest(script="hello")))
    return fake, result


def test_fix_returns_output_model(tmp_path, monkeypatch):
    fake, result = _fix(tmp_path, monkeypatch)
    assert isinstance(result, PromptFixRequestOutput)
    assert result.script == "fixed"
    assert result.info == "ok"
    assert result.error is None
    assert result.changes == []
    assert fake.last_response_format is PromptFixRequestOutput


def test_fix_parses_fenced_json(tmp_path, monkeypatch):
    fenced = '```json\n{"script": "fixed", "info": "x", "error": null, "changes": []}\n```'
    _, result = _fix(tmp_path, monkeypatch, output=fenced)
    assert result.script == "fixed"


def test_fix_raises_on_invalid_output(tmp_path, monkeypatch):
    with pytest.raises(InvalidModelOutputException):
        _fix(tmp_path, monkeypatch, output="not json")


def test_watch_prompt_structure(tmp_path, monkeypatch):
    fake, _ = _fix(tmp_path, monkeypatch, request=PromptFixRequest(script="hello world"))
    prompt = fake.last_prompt
    assert "<role>ROLE TEXT</role>" in prompt
    assert "<security>SECURITY TEXT</security>" in prompt
    assert "{{USER_CONTENT}}" not in prompt
    assert "<context>" in prompt
    assert "<mode>watch</mode>" in prompt
    assert "<length>30</length>" in prompt
    assert "<user_script>\nhello world\n</user_script>" in prompt
    assert "target_audience" not in prompt
    assert "call_to_action" not in prompt


def test_sell_prompt_includes_audience_and_cta(tmp_path, monkeypatch):
    request = PromptFixRequest(
        mode="sell",
        script="hi",
        length=60,
        target_audience="new coaches",
        call_to_action="book a call",
    )
    fake, _ = _fix(tmp_path, monkeypatch, request=request)
    prompt = fake.last_prompt
    assert "<mode>sell</mode>" in prompt
    assert "<length>60</length>" in prompt
    assert "<target_audience>new coaches</target_audience>" in prompt
    assert "<call_to_action>book a call</call_to_action>" in prompt
