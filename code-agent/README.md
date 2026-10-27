# GitHub AI Coding Agent Package

A fully autonomous, ReAct-based AI agent that explores, modifies, tests, and verifies code inside your GitHub repository.

## Setup Instructions

1. **Add the Agent Files:**
   Place `agent.py`, `tools.py`, `memory.py`, `AGENT.md`, and `requirements.txt` in the root of your repository.
2. **Add the Workflow:**
   Place `agent.yml` inside `.github/workflows/`.
3. **Configure Secrets:**
   Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.
   - Name: `AGENT_API_KEY`
   - Secret: Your OpenAI or compatible LLM API Key.
   *(Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions).*
4. **Grant Permissions:**
   Go to **Settings** -> **Actions** -> **General**. Under **Workflow permissions**, ensure "Read and write permissions" is selected so the agent can post comments and save its memory state.

## How to Trigger

- **Via Issue or PR Comment:** Comment `/agent [your instruction]` on any Issue or Pull Request.
  *Example:* `/agent read main.py and fix the bug with the data parsing loop. Run tests to verify.`
- **Via Actions Tab:** Go to the Actions tab, select "AI Coding Agent", click "Run workflow", and type your task directly into the prompt.

---
*Package as received from Gemini Pro via Cyrus, 2026-10-26. Manager's installation
notes and safety fixes are recorded in this folder's AGENT.md and in the adapted
workflow at `../../.github/workflows/agent.yml`.*
