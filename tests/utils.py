class FakeLLMClient:
    def __init__(self, output: str = "") -> None:
        self.output = output
        self.last_prompt: str | None = None
        self.last_response_format: dict | None = None

    async def complete(self, prompt: str, response_format: dict | None = None) -> str:
        self.last_prompt = prompt
        self.last_response_format = response_format
        return self.output
