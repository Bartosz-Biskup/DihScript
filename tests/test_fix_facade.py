import asyncio

import pytest

import services.prompt_fixer_service as pfs_module
from repositories.models import Subscriber, PromptFixRequestOutput
from services.exceptions import ModelProviderException, NotFoundException
from services.fix_facade import FixRequest, FixFacade
from services.prompt_fixer_service import PromptFixerService
from services.subscriber_service import SubscriberService
from utils import FakeLLMClient, LLMServiceThatRaises, FakeSubscriberRepo

_VALID_OUTPUT = PromptFixRequestOutput(
    script="fixed",
    info="ok",
    error=None,
    changes=[]
)

_TEMPLATE = (
    "<role>ROLE</role>\n\n"
    "<script_writing_guidelines>TODO</script_writing_guidelines>\n\n"
    "<output_format>OUTPUT FORMAT</output_format>\n\n"
    "<security>SECURITY</security>\n\n"
    "<user_content>\n{{USER_CONTENT}}\n</user_content>"
)


def make_subscriber(name: str = "Anna", email: str = "anna@example.com", run_count: int = 0) -> Subscriber:
    return Subscriber(name=name, email=email, run_count=run_count)


def build_service(tmp_path, monkeypatch, repo, llm_output=_VALID_OUTPUT):
    (tmp_path / "script_fixer.txt").write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(pfs_module, "PROMPTS_DIR", tmp_path)

    fixer = PromptFixerService(FakeLLMClient(llm_output))
    subscribers = SubscriberService(repo)
    return FixFacade(fixer, subscribers)


def test_fix_script_returns_output_and_increments_run_count(tmp_path, monkeypatch):
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(tmp_path, monkeypatch, repo)

    output = asyncio.run(service.fix(FixRequest(email="anna@example.com", script="hi")))

    assert output.script == "fixed"
    assert repo.get_by_email("anna@example.com").run_count == 1


def test_fix_script_unknown_email_raises_without_calling_llm(tmp_path, monkeypatch):
    llm = FakeLLMClient(_VALID_OUTPUT)
    (tmp_path / "script_fixer.txt").write_text(_TEMPLATE, encoding="utf-8")
    monkeypatch.setattr(pfs_module, "PROMPTS_DIR", tmp_path)

    fixer = PromptFixerService(llm)
    service = FixFacade(fixer, SubscriberService(FakeSubscriberRepo()))

    with pytest.raises(NotFoundException):
        asyncio.run(service.fix(FixRequest(email="missing@example.com", script="hi")))

    assert llm.last_prompt is None


def test_fix_script_failure_does_not_increment_run_count(tmp_path, monkeypatch):
    repo = FakeSubscriberRepo([make_subscriber()])
    service = build_service(tmp_path, monkeypatch, repo, llm_output="not json")
    monkeypatch.setattr(service._fixer, "_llm", LLMServiceThatRaises())

    with pytest.raises(ModelProviderException, match="provider is unreachable"):
        asyncio.run(service.fix(FixRequest(email="anna@example.com", script="hi")))

    assert repo.get_by_email("anna@example.com").run_count == 0
