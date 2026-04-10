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
- **11 Browser Tools** — navigate, click, type, scroll, extract text, take screenshots, press keys, wait for elements, and more
- **Skill System** — extensible skills (code review, debugging, security review, test generation, refactoring)
- **User Agent Spoofing** — HTTP header, JS property, and Client Hints API level spoofing
- **Local Model Support** — works with Ollama/LM Studio via OpenAI-compatible API

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| UI Framework | PyQt6 | Desktop application widgets |
| Browser Engine | PyQt6-WebEngine (Chromium) | Full web browsing |
| Async Bridge | qasync | Shared event loop for PyQt6 + asyncio |
| AI Framework | 10xscale-agentflow | ReAct agent graph orchestration |
| LLM | Google Gemini 3 Flash | Multimodal vision + tool calling |
| Browser Control | JavaScript injection | DOM manipulation on live pages |

## Project Structure

```
browser_agent/
├── app.py                    # Application bootstrap + wiring
├── config.py                 # AppConfig (pydantic-settings)
├── ui/                       # View layer (PyQt6 widgets)
│   ├── main_window.py        # QMainWindow with QSplitter
│   ├── browser_panel.py      # URL bar, nav buttons, tabs, QWebEngineView
│   ├── chat_panel.py         # Message list, composer, typing indicator
│   ├── chat_message_widget.py # Message bubbles with animations
│   ├── tab_bar.py            # Tab management
│   └── styles.py             # QSS theme + animation helpers
├── browser/                  # Browser engine layer
│   ├── engine.py             # QWebEngineProfile, cookie persistence, UA spoofing
│   ├── page_controller.py    # Async Python ↔ JavaScript bridge
│   ├── screenshot.py         # QWebEngineView → base64 JPEG
│   └── js_scripts.py         # Injectable JS with visual animations
├── agent/                    # AI agent layer
│   ├── state.py              # BrowserAgentState (extends AgentState)
│   ├── graph.py              # StateGraph construction + ReAct compilation
│   ├── tools.py              # 11 browser tool functions (closure factory)
│   └── prompts.py            # System prompt with state interpolation
├── bridge/                   # Coordination layer
│   ├── agent_controller.py   # Orchestrates: chat → agent → browser → UI
│   └── signals.py            # Qt signals for thread-safe updates
├── skills/                   # Skill recording & playback
├── recording/                # Session recording & export
├── storage/                  # Conversation & memory persistence
├── voice/                    # Voice engine
├── autonomous/               # Rules engine for autonomous actions
├── multiagent/               # Multi-agent coordination
└── predictive/               # User pattern tracking
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

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_api_key_here
```

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

| Tool | Parameters | Description |
|------|-----------|-------------|
| `navigate_to` | `url` | Navigate browser to URL |
| `click_element` | `selector` | Click with animated cursor + ripple |
| `type_text` | `selector`, `text` | Character-by-character typing animation |
| `scroll_page` | `direction`, `pixels` | Smooth scroll with visual label |
| `press_key` | `key` | Keyboard press (Enter, Tab, Escape...) |
| `extract_text` | `selector` | Read text content from element |
| `take_screenshot` | — | Capture page for AI vision analysis |
| `get_page_elements` | — | List all interactive elements |
| `go_back` | — | Browser history back |
| `go_forward` | — | Browser history forward |
| `wait_for_element` | `selector`, `timeout` | Wait for dynamic content |

## License

MIT
