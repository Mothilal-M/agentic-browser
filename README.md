# Agentic Browser

A PyQt6 desktop application that embeds a full Chromium browser with an AI-powered chat sidebar. The AI agent (Google Gemini Flash) can **see** the page via screenshots and **control** it via JavaScript injection — with animated cursor movement, element highlighting, and typing animations so you can watch the AI work in real time.

```
+----------------------------------------------+--------------------+
| CHROMIUM BROWSER (QtWebEngine)               | AI CHAT SIDEBAR    |
| [←] [→] [↻] [⌂] [https://example.com     ] |                    |
| ─────────────────────────────────────────────| ✦ AI Chat    Ready |
|                                              |                    |
|   Real browser: tabs, cookies, JS, logins    | [You] Apply to     |
|   User interacts directly                    |  this job for me   |
|   AI controls via JS injection with          |                    |
|   animated cursor + highlights               | [Tool] click       |
|                                              |  → Apply button    |
|        ◆ ← AI cursor (animated)              |                    |
|   ┌─────────────┐                            | [Tool] type_text   |
|   │ Apply Now ▓ │ ← highlight glow           |  → John Doe        |
|   └─────────────┘                            |                    |
|                                              | [AI] Done! I've    |
|                                              |  submitted your    |
|                                              |  application.      |
+----------------------------------------------+--------------------+
```

## Features

- **Full Chromium Browser** — tabs, cookies, localStorage, login sessions preserved across restarts
- **AI Vision** — Gemini Flash sees the page via screenshots and understands page context
- **Visual Automation** — animated cursor movement, click ripples, element highlighting, character-by-character typing
- **ReAct Agent Loop** — Reasoning + Acting pattern with tool calling for multi-step browser tasks
- **29+ Browser Tools** — navigate, click, type, scroll, extract text, screenshots, shadow DOM, iframes, CAPTCHA detection, autofill, and more
- **Smart Error Recovery** — 5-tier fallback chain: CSS selector, wait+retry, text match, aria-label, scroll+retry
- **Skill System** — record, save, and replay browser workflows with one click
- **Session Recording** — record AI sessions and export as HTML reports or JSON
- **Long-Term Memory** — remembers user preferences, credentials, and patterns across sessions
- **User Profile** — auto-fills forms with saved personal info (name, email, phone, etc.)
- **Voice Control** — speech-to-text input and text-to-speech output via Web Speech API
- **Automation Rules** — schedule recurring tasks (e.g., "check email every 30 minutes")
- **Multi-Agent Coordination** — breaks complex goals into sub-tasks dispatched to specialist agents (Researcher, FormFiller, Navigator, Monitor)
- **Predictive Suggestions** — learns browsing patterns and suggests actions based on time-of-day and day-of-week
- **Action Guardrails** — detects sensitive actions (payments, deletions) and requests confirmation before executing
- **User Agent Spoofing** — HTTP header, JS property, and Client Hints API level spoofing
- **Local Model Support** — works with Ollama/LM Studio via OpenAI-compatible API
- **Incognito Mode** — off-the-record browsing with no persistent storage

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| UI Framework | PyQt6 | Desktop application widgets |
| Browser Engine | PyQt6-WebEngine (Chromium) | Full web browsing |
| Async Bridge | qasync | Shared event loop for PyQt6 + asyncio |
| AI Framework | 10xscale-agentflow | ReAct agent graph orchestration |
| LLM | Google Gemini 3 Flash | Multimodal vision + tool calling |
| Browser Control | JavaScript injection | DOM manipulation on live pages |
| Storage | SQLite | Conversations, memory, skills, rules, patterns |

## Project Structure

```
browser_agent/
├── app.py                    # Application bootstrap + wiring
├── config.py                 # AppConfig (pydantic-settings)
├── ui/                       # View layer (PyQt6 widgets)
│   ├── main_window.py        # QMainWindow with QSplitter
│   ├── browser_panel.py      # URL bar, nav buttons, tabs, QWebEngineView
│   ├── chat_panel.py         # Message list, composer, overlay panels
│   ├── chat_message_widget.py # Message bubbles with animations
│   ├── skills_panel.py       # Saved workflows with one-click replay
│   ├── rules_panel.py        # Automation rules management
│   ├── thread_selector.py    # Chat history sidebar
│   ├── tab_bar.py            # Tab management
│   ├── tool_call_widget.py   # Collapsible tool call display
│   ├── markdown_renderer.py  # Markdown to HTML conversion
│   └── styles.py             # QSS dark theme + design tokens
├── browser/                  # Browser engine layer
│   ├── engine.py             # QWebEngineProfile, cookie persistence, UA spoofing
│   ├── page_controller.py    # Async Python ↔ JavaScript bridge
│   ├── screenshot.py         # QWebEngineView → base64 JPEG
│   └── js_scripts.py         # Injectable JS with visual animations
├── agent/                    # AI agent layer
│   ├── state.py              # BrowserAgentState (extends AgentState)
│   ├── graph.py              # StateGraph construction + ReAct compilation
│   ├── tools.py              # 29+ browser tool functions (closure factory)
│   ├── prompts.py            # System prompt with state interpolation
│   ├── vision.py             # Vision-first element detection
│   ├── error_recovery.py     # Smart fallback strategies
│   └── guardrails.py         # Action confirmation for sensitive operations
├── bridge/                   # Coordination layer
│   ├── agent_controller.py   # Orchestrates: chat → agent → browser → UI
│   ├── async_bridge.py       # qasync event loop setup
│   └── signals.py            # Qt signals for thread-safe updates
├── skills/                   # Skill recording & playback
│   ├── recorder.py           # Records tool calls during agent runs
│   ├── player.py             # Replays saved workflows step-by-step
│   ├── store.py              # SQLite CRUD for skills
│   └── models.py             # Skill and SkillStep dataclasses
├── recording/                # Session recording & export
│   ├── recorder.py           # Captures events + screenshots
│   ├── exporter.py           # Export to HTML report or JSON
│   └── models.py             # RecordedEvent dataclasses
├── storage/                  # Persistence layer
│   ├── conversation_db.py    # Thread and message storage
│   ├── memory_db.py          # Long-term facts with FTS5 search
│   └── user_profile.py       # Key-value profile for form auto-fill
├── autonomous/               # Automation
│   └── rules_engine.py       # Scheduled rule execution
├── multiagent/               # Multi-agent coordination
│   └── coordinator.py        # Task decomposition + specialist dispatch
├── predictive/               # Pattern learning
│   └── pattern_tracker.py    # Browsing pattern analysis + suggestions
└── voice/                    # Voice I/O
    └── engine.py             # Web Speech API STT + system TTS
```

## Getting Started

### Prerequisites

- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/apikey)

### Installation

```bash
git clone https://github.com/Mothilal-M/agentic-browser.git
cd agentic-browser
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy the example env file and add your API key:

```bash
cp .env.example .env
```

Edit `.env` and set your Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
```

See [.env.example](.env.example) for all available configuration options.

### Run

```bash
python run.py
```

### Using Local Models (Optional)

To run with Ollama or LM Studio instead of Gemini (no data sent to cloud):

```env
BROWSER_AGENT_MODEL=llava:13b
BROWSER_AGENT_PROVIDER=openai
BROWSER_AGENT_BASE_URL=http://localhost:11434/v1
BROWSER_AGENT_REASONING_EFFORT=low
```

## Browser Tools

### Core Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `navigate_to` | `url` | Navigate browser to URL |
| `click_element` | `selector` | Click with animated cursor + ripple |
| `type_text` | `selector`, `text` | Character-by-character typing animation |
| `scroll_page` | `direction`, `pixels` | Smooth scroll with visual label |
| `press_key` | `key` | Keyboard press (Enter, Tab, Escape...) |
| `extract_text` | `selector` | Read text content from element |
| `take_screenshot` | -- | Capture page for AI vision analysis |
| `get_page_elements` | -- | List all interactive elements |
| `go_back` / `go_forward` | -- | Browser history navigation |
| `wait_for_element` | `selector`, `timeout` | Wait for dynamic content |

### Smart Tools (Auto-Recovery)

| Tool | Description |
|------|-------------|
| `smart_click` | Click with 5-tier fallback: selector, wait+retry, text match, aria-label, scroll+retry |
| `smart_type` | Type with the same fallback chain |
| `click_by_description` | Click by visual description ("the blue Apply button") |
| `find_element_by_text` | Find element by visible text content |
| `understand_page` | Get structured page summary |

### Advanced Tools

| Tool | Description |
|------|-------------|
| `upload_file` | Upload a local file to a file input |
| `check_for_captcha` | Detect CAPTCHAs or 2FA prompts |
| `click_shadow_element` | Interact with Shadow DOM elements |
| `list_iframes` | List all iframes on the page |
| `autofill_form` | Fill multiple form fields at once |
| `execute_multi_agent_plan` | Break complex goals into specialist sub-tasks |

### Memory & Skills

| Tool | Description |
|------|-------------|
| `remember` / `recall` | Save and search long-term user facts |
| `get_my_profile` / `save_profile_field` | Access and update user profile |
| `list_skills` / `run_skill` | List and replay saved workflows |
| `save_current_as_skill` / `delete_skill` | Manage workflow skills |

## Testing

```bash
pip install pytest
python -m pytest tests/ -v
```

## License

MIT
