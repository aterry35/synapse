import os

class LLMResponse:
    def __init__(self, text: str):
        self.text = text

class LLMManager:
    _instance = None

    def __init__(self):
        self.provider = None
        self.model_name = None
        self._client = None
        self._model = None
        self._configure_from_env()

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def _configure_from_env(self):
        provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
        self.provider = provider

        if provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set for Gemini.")
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self._model = genai.GenerativeModel(self.model_name)
            self._client = None
            return

        if provider == "gpt":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set for GPT.")
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            self._model = None
            return

        if provider == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set for Claude.")
            from anthropic import Anthropic
            self._client = Anthropic(api_key=api_key)
            self.model_name = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")
            self._model = None
            return

        raise ValueError(f"Unsupported LLM_PROVIDER '{provider}'.")

    def generate_content(self, prompt: str):
        if self.provider == "gemini":
            return self._model.generate_content(prompt)

        if self.provider == "gpt":
            # Prefer Responses API, fall back to Chat Completions if needed.
            try:
                resp = self._client.responses.create(
                    model=self.model_name,
                    input=prompt
                )
                return LLMResponse(resp.output_text)
            except Exception:
                resp = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = resp.choices[0].message.content if resp.choices else ""
                return LLMResponse(text or "")

        if self.provider == "claude":
            resp = self._client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )
            text = ""
            if resp.content and len(resp.content) > 0:
                text = resp.content[0].text
            return LLMResponse(text or "")

        raise ValueError(f"Unsupported LLM_PROVIDER '{self.provider}'.")
