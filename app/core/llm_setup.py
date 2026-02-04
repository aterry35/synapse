import os
import sys
from getpass import getpass

from dotenv import load_dotenv

PROVIDERS = {
    "1": {"id": "gemini", "label": "Gemini", "env": "GOOGLE_API_KEY"},
    "2": {"id": "gpt", "label": "GPT (OpenAI)", "env": "OPENAI_API_KEY"},
    "3": {"id": "claude", "label": "Claude (Anthropic)", "env": "ANTHROPIC_API_KEY"},
}

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def _read_env_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return f.read().splitlines()


def _write_env(path, updates):
    lines = _read_env_lines(path)
    found = {k: False for k in updates.keys()}

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0]
        if key in updates:
            lines[i] = f"{key}={updates[key]}"
            found[key] = True

    for key, value in updates.items():
        if not found[key]:
            lines.append(f"{key}={value}")

    with open(path, "w") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def _prompt_choice():
    print("Select LLM provider:")
    for k in sorted(PROVIDERS.keys()):
        p = PROVIDERS[k]
        print(f"{k}) {p['label']}")

    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice in PROVIDERS:
            return PROVIDERS[choice]
        print("Invalid choice. Please select 1, 2, or 3.")


def _prompt_api_key(provider):
    key_name = provider["env"]
    existing = os.getenv(key_name)
    if existing:
        prompt = f"Enter API key for {provider['label']} (press Enter to keep existing): "
        new_key = getpass(prompt).strip()
        return new_key if new_key else existing

    while True:
        new_key = getpass(f"Enter API key for {provider['label']}: ").strip()
        if new_key:
            return new_key
        print("API key cannot be empty.")


def main():
    load_dotenv(ENV_PATH)
    provider_id = os.getenv("LLM_PROVIDER", "").strip().lower()
    provider_by_id = {v["id"]: v for v in PROVIDERS.values()}
    if provider_id in provider_by_id:
        provider = provider_by_id[provider_id]
        key_name = provider["env"]
        if os.getenv(key_name):
            print(f"Current LLM provider: {provider['label']}")
            if not sys.stdin.isatty():
                return
            
            confirm = input(f"Keep using {provider['label']}? [Y/n]: ").strip().lower()
            if confirm in ("", "y", "yes"):
                return
    provider = _prompt_choice()
    api_key = _prompt_api_key(provider)

    updates = {
        "LLM_PROVIDER": provider["id"],
        provider["env"]: api_key
    }
    _write_env(ENV_PATH, updates)
    print(f"LLM provider set to {provider['label']}.")


if __name__ == "__main__":
    main()
