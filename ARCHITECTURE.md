# AI Browser Agent — Technical Architecture

## Overview

A PyQt6 desktop application that embeds a full Chromium browser (via QtWebEngine) with an AI chat sidebar. The AI agent (Google Gemini Flash) can **see** the browser via screenshots and **control** it via JavaScript injection — with visible cursor movement, element highlighting, and typing animations so the user watches the AI work in real time.

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
│
├── ui/                       # View layer (PyQt6 widgets)
│   ├── main_window.py        # QMainWindow with QSplitter
│   ├── browser_panel.py      # URL bar, nav buttons, tabs, QWebEngineView
│   ├── chat_panel.py         # Message list, composer, typing indicator
│   ├── chat_message_widget.py # Message bubbles with animations
│   ├── tab_bar.py            # Tab management
│   └── styles.py             # QSS theme + animation helpers
│
├── browser/                  # Browser engine layer
│   ├── engine.py             # QWebEngineProfile, cookie persistence, UA spoofing
│   ├── page_controller.py    # Async Python ↔ JavaScript bridge
│   ├── screenshot.py         # QWebEngineView → base64 JPEG
│   └── js_scripts.py         # All injectable JS with visual animations
│
├── agent/                    # AI agent layer
│   ├── state.py              # BrowserAgentState (extends AgentState)
│   ├── graph.py              # StateGraph construction + ReAct compilation
│   ├── tools.py              # 11 browser tool functions (closure factory)
│   └── prompts.py            # System prompt with state interpolation
│
└── bridge/                   # Coordination layer
    ├── agent_controller.py   # Orchestrates: chat → agent → browser → UI
    └── signals.py            # Qt signals for thread-safe updates
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                             │
│  User types: "Apply to this job for me"                            │
│  ChatPanel.message_submitted signal emits                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENT CONTROLLER                                │
│                                                                     │
│  1. Capture screenshot: QWebEngineView.grab() → QPixmap → JPEG     │
│     → base64 encode (~40-80KB)                                     │
│                                                                     │
│  2. Capture page state: run GET_PAGE_INFO JS → {url, title}        │
│                                                                     │
│  3. Capture interactive elements: run GET_INTERACTIVE_ELEMENTS JS   │
│     → list of {tag, selector, text} for all buttons/inputs/links   │
│                                                                     │
│  4. Build messages:                                                 │
│     [Message.text_message("Apply to this job for me"),              │
│      Message.image_message(screenshot_base64, "image/jpeg")]        │
│                                                                     │
│  5. Call: compiled_graph.ainvoke(input_data, config)                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENTFLOW ReAct GRAPH                           │
│                                                                     │
│  ┌──────────┐    conditional    ┌──────────┐                       │
│  │   MAIN   │───────edges──────▶│   TOOL   │                       │
│  │  (Agent) │◀─────────────────│ (ToolNode)│                       │
│  └────┬─────┘                   └──────────┘                       │
│       │                                                             │
│       ▼                                                             │
│  Agent receives:                                                    │
│  • System prompt with {current_url}, {interactive_elements}        │
│  • User message + screenshot (Gemini sees the page via vision)     │
│                                                                     │
│  Agent decides: "I need to click the Apply button"                 │
│  Agent returns: tool_call(click_element, selector="#apply-btn")    │
│                                                                     │
│  Router (_should_use_tools):                                        │
│  • Has tool_calls? → route to TOOL node                            │
│  • Last msg is tool result? → route back to MAIN                   │
│  • No tool calls? → END                                            │
│                                                                     │
│  Loop continues until agent gives final text response              │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION                                    │
│                                                                     │
│  ToolNode dispatches to: click_element(selector="#apply-btn")      │
│                                                                     │
│  Tool function (closure) calls:                                     │
│    → page_controller.click("#apply-btn")                           │
│      → _ensure_visuals() — inject visual layer if not present      │
│      → run_js(CLICK_ELEMENT % selector)                            │
│                                                                     │
│  JavaScript executes on the live browser page (see below)          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│               VISUAL AUTOMATION (JavaScript)                        │
│                                                                     │
│  1. HIGHLIGHT: Purple glow border around target element             │
│     box-shadow: 0 0 12px rgba(124,111,247,0.4)                    │
│                                                                     │
│  2. CURSOR MOVE: SVG cursor glides smoothly to element center      │
│     easeInOut animation over 600ms using requestAnimationFrame     │
│                                                                     │
│  3. ACTION LABEL: Floating bar shows "Clicking: Apply Now"         │
│     positioned at bottom center of viewport                         │
│                                                                     │
│  4. CLICK RIPPLE: Expanding circle animation at click point        │
│     width: 0→50px, opacity: 1→0 over 400ms                        │
│                                                                     │
│  5. DISPATCH EVENTS: pointerdown → mousedown → mouseup → click    │
│     on the actual DOM element (triggers real page behavior)         │
│                                                                     │
│  6. CLEANUP: Hide highlight and label after 300ms                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESULT → UI                                      │
│                                                                     │
│  Tool returns: "Clicked button element: Apply Now"                 │
│  Agent takes another screenshot to verify, then responds:           │
│  "Done! I've submitted your application."                          │
│                                                                     │
│  AgentController emits Qt signals:                                  │
│    signals.tool_call_started → ChatPanel.append_tool_message()     │
│    signals.tool_result_received → ChatPanel.append_tool_message()  │
│    signals.assistant_message_complete → ChatPanel.append_message() │
│    signals.agent_busy(False) → ChatPanel.set_busy(False)           │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Technical Mechanisms

### 1. Async Event Loop Bridge (qasync)

PyQt6 has its own event loop. AgentFlow is async (asyncio). These cannot coexist natively. `qasync` solves this by replacing Python's asyncio event loop with one that processes **both** Qt events and asyncio futures on the same thread.

```
┌─────────────────────────────────────────────┐
│           qasync.QEventLoop                 │
│                                             │
│  Processes:                                 │
│  • Qt signals/slots (button clicks, etc.)   │
│  • asyncio coroutines (agent execution)     │
│  • asyncio.Future (JS callback bridge)      │
│                                             │
│  Single thread — no race conditions         │
└─────────────────────────────────────────────┘
```

```python
# app.py — bootstrap
app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)      # replaces asyncio default loop
asyncio.set_event_loop(loop)

# Now @asyncSlot() works in Qt slots:
@asyncSlot(str)
async def on_message(text):
    await controller.handle_user_message(text)  # runs on same thread

window.chat_panel.message_submitted.connect(on_message)
loop.run_forever()
```

### 2. JavaScript ↔ Python Bridge

Qt's `page.runJavaScript(code, callback)` is callback-based. We bridge it to asyncio using `Future`:

```python
# page_controller.py
async def run_js(self, script: str):
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    def callback(result):
        if not future.done():
            loop.call_soon_threadsafe(future.set_result, result)

    page.runJavaScript(script, callback)
    return await future  # suspends coroutine until JS returns
```

This works because qasync processes both the Qt callback and the asyncio future on the same thread.

### 3. Screenshot → Gemini Vision Pipeline

```
QWebEngineView.grab()                    # → QPixmap (raw render)
  .scaled(1280, 1280, KeepAspectRatio)   # → resize for token efficiency
  .save(QBuffer, "JPEG", quality=70)     # → compressed bytes (~40-80KB)
  base64.b64encode(bytes)                # → string for API transport

Message.image_message(                   # AgentFlow message wrapper
    image_base64=b64_string,
    mime_type="image/jpeg"
)

# AgentFlow internal conversion:
#   → _image_block_to_openai() → {"type": "image_url", "url": "data:image/jpeg;base64,..."}
#   → _image_part_to_google() → detects data: prefix, decodes base64
#   → types.Part.from_bytes(data=raw_bytes, mime_type="image/jpeg")
#   → Sent to Gemini Flash as inline image content
```

### 4. Visual Automation Layer

A JavaScript overlay system injected into every page at `DocumentCreation` time:

| Component | Element | Purpose |
|-----------|---------|---------|
| AI Cursor | SVG `<div>` at z-index 2147483647 | Purple arrow that glides to targets |
| Highlight | `<div>` with border + glow | Shows which element AI is targeting |
| Ripple | `<div>` with CSS transition | Click feedback animation |
| Action Label | `<div>` at bottom center | Shows "Clicking: Apply Now" |

**Animation**: Cursor movement uses easeInOut interpolation over ~600ms via `requestAnimationFrame`:
```javascript
for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const ease = t < 0.5 ? 2*t*t : 1 - Math.pow(-2*t+2, 2) / 2;
    cursor.style.left = (startX + (endX - startX) * ease) + 'px';
    cursor.style.top  = (startY + (endY - startY) * ease) + 'px';
    await new Promise(r => requestAnimationFrame(r));
}
```

**Typing animation**: Characters appear one at a time (~50ms each), using native property setters to trigger React/Vue reactivity:
```javascript
const nativeSetter = Object.getOwnPropertyDescriptor(
    HTMLInputElement.prototype, 'value'
)?.set;
nativeSetter.call(el, currentVal);  // bypasses framework wrappers
el.dispatchEvent(new Event('input', {bubbles: true}));
```

Visuals are **hidden before screenshots** sent to Gemini (so the AI sees the clean page).

### 5. Tool Closure Factory Pattern

AgentFlow's `ToolNode` introspects function signatures to build tool schemas for Gemini. Browser tools need access to `PageController`, `ScreenshotCapture`, and `BrowserEngine` — but ToolNode expects plain functions. Solution: a factory that returns closures.

```python
# agent/tools.py
def create_browser_tools(page_controller, screenshot, engine) -> list[Callable]:

    async def click_element(selector: str) -> str:
        """Click an element on the page by CSS selector."""
        result = await page_controller.click(selector)  # captured via closure
        return result

    async def type_text(selector: str, text: str) -> str:
        """Type text into an input field."""
        result = await page_controller.type_text(selector, text)
        return result

    return [click_element, type_text, ...]
    # ToolNode sees: click_element(selector: str) -> str
    # Gemini sees: {"name": "click_element", "parameters": {"selector": {"type": "string"}}}
```

AgentFlow uses `call_sync_or_async()` internally, which auto-detects async functions and awaits them.

### 6. ReAct Agent Graph

The agent follows the **ReAct (Reasoning + Acting)** pattern:

```
                ┌─────────────┐
                │  __start__  │
                └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
         ┌─────│    MAIN     │◄────────┐
         │     │   (Agent)   │         │
         │     └──────┬──────┘         │
         │            │                │
         │     _should_use_tools()     │
         │       │           │         │
         │   has tools    no tools     │
         │       │           │         │
         │       ▼           ▼         │
         │  ┌────────┐  ┌────────┐    │
         │  │  TOOL  │  │  END   │    │
         │  │(ToolNode)  └────────┘    │
         │  └────┬───┘                 │
         │       │                     │
         │       └─────────────────────┘
         │
         └──── (conditional routing based on last message)
```

The routing function:
```python
def _should_use_tools(state: AgentState) -> str:
    last = state.context[-1]
    if last.tools_calls and last.role == "assistant":
        return "TOOL"        # agent wants to call a tool
    if last.role == "tool":
        return "MAIN"        # tool result ready, let agent continue
    return END               # agent gave final text answer
```

### 7. Session Persistence

```python
profile = QWebEngineProfile("BrowserAgentProfile")
profile.setPersistentCookiesPolicy(ForcePersistentCookies)
profile.setPersistentStoragePath("~/.../BrowserAgent/profile")
```

This stores cookies, localStorage, sessionStorage, and cache to disk. When the user logs into WhatsApp Web and closes the app, the session is preserved on restart.

### 8. User Agent Spoofing

Sites like WhatsApp check the browser version at multiple levels. We override all of them:

| Level | Mechanism | What it spoofs |
|-------|-----------|----------------|
| HTTP Header | `profile.setHttpUserAgent()` | Server-side checks |
| JS Property | `Object.defineProperty(navigator, 'userAgent')` | `navigator.userAgent` |
| Client Hints API | Override `navigator.userAgentData` | `navigator.userAgentData.brands` |

The JS override is injected via `QWebEngineScript` at `DocumentCreation` in `MainWorld` — before any page script executes.

### 9. Thread Safety via Qt Signals

The agent runs as an asyncio task. UI updates must happen on the Qt main thread. Qt signals are thread-safe by design:

```
AgentController (async task)          ChatPanel (Qt main thread)
        │                                      │
        │  signals.tool_call_started ─────────▶│ append_tool_message()
        │  signals.assistant_message ─────────▶│ append_assistant_message()
        │  signals.agent_busy(False) ─────────▶│ set_busy(False)
        │                                      │
```

All signal emissions in `AgentController` are automatically queued and delivered on the Qt thread.

## Available Browser Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `navigate_to` | `url: str` | Navigate browser to URL |
| `click_element` | `selector: str` | Click with animated cursor + ripple |
| `type_text` | `selector: str, text: str` | Character-by-character typing animation |
| `scroll_page` | `direction: str, pixels: int` | Smooth scroll with visual label |
| `press_key` | `key: str` | Keyboard press (Enter, Tab, Escape...) |
| `extract_text` | `selector: str` | Read text content from element |
| `take_screenshot` | — | Capture page for Gemini vision analysis |
| `get_page_elements` | — | List all interactive elements |
| `go_back` | — | Browser history back |
| `go_forward` | — | Browser history forward |
| `wait_for_element` | `selector: str, timeout: int` | Wait for dynamic content |

## Running

```bash
pip install -r requirements.txt
python run.py
```

## Dependencies

- **PyQt6 + PyQt6-WebEngine** — Desktop UI + embedded Chromium
- **qasync** — asyncio + Qt event loop bridge
- **10xscale-agentflow** — AI agent framework (ReAct graph, tool execution, streaming)
- **google-genai** — Gemini Flash API client
- **pydantic-settings** — Configuration management
- **python-dotenv** — .env file loading
