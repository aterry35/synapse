# Changelog

## 2026-02-03
- Added dynamic LLM routing for Gemini, GPT, and Claude. (`app/core/llm_manager.py`)
- Added interactive LLM selection + API key setup that writes `.env`. (`app/core/llm_setup.py`)
- Skipped interactive LLM setup when `.env` is already configured in non-interactive runs. (`app/core/llm_setup.py`)
- Switched deals plugin to use the dynamic LLM manager; removed unsafe `eval` fallback; added strict JSON parsing and validation. (`app/plugins/deals/deals_plugin.py`)
- Implemented Slickdeals scraping and improved price parsing. (`app/plugins/deals/deals_plugin.py`)
- Switched GCLI to use the dynamic LLM manager; removed Gemini-only wiring. (`app/plugins/gcli/sdlc_workflow.py`)
- Replaced LLM-generated script execution with JSON file map parsing and safe file writes. (`app/plugins/gcli/sdlc_workflow.py`)
- Fixed build loop to return a JSON message to prevent `/gcli approve` crashes. (`app/plugins/gcli/sdlc_workflow.py`)
- Tightened system command execution to explicit `/sysctl run|exec` and removed `shell=True`. (`app/plugins/system_control/system_plugin.py`)
- Updated dependencies for new LLM providers and required packages; removed duplicates. (`requirements.txt`)
- Added multi-LLM keys to environment template. (`example.env`)
- Updated setup documentation for multi-LLM support. (`SETUP_GUIDE.md`)
- Added LLM setup invocation to startup script. (`start_synapse.sh`)
- Updated local `.env` with LLM provider + API keys (local only; values not recorded here).
