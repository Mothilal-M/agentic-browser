"""Injectable JavaScript snippets for browser control.

Includes a visual automation layer: animated cursor, element highlights,
typing animation — so the user can watch the AI work like a real person.
"""

# ─── Visual cursor + overlay system (injected once per page) ───────────────

INIT_VISUAL_LAYER = """
(function() {
    if (document.getElementById('__ai_cursor')) return;

    // --- Animated cursor ---
    const cursor = document.createElement('div');
    cursor.id = '__ai_cursor';
    cursor.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
        <path d="M5 3l14 8-6.5 2L9 19.5z" fill="#7c6ff7" stroke="#fff" stroke-width="1.5"/>
    </svg>`;
    Object.assign(cursor.style, {
        position: 'fixed', top: '0px', left: '0px', zIndex: '2147483647',
        pointerEvents: 'none', transition: 'none',
        filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.5))',
        display: 'none'
    });
    document.documentElement.appendChild(cursor);

    // --- Action label (shows what AI is doing) ---
    const label = document.createElement('div');
    label.id = '__ai_action_label';
    Object.assign(label.style, {
        position: 'fixed', bottom: '20px', left: '50%', transform: 'translateX(-50%)',
        zIndex: '2147483647', pointerEvents: 'none',
        background: 'rgba(124,111,247,0.95)', color: '#fff',
        padding: '8px 20px', borderRadius: '20px', fontSize: '13px',
        fontFamily: 'system-ui, sans-serif', fontWeight: '600',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)', display: 'none',
        transition: 'opacity 0.3s'
    });
    document.documentElement.appendChild(label);

    // --- Highlight overlay ---
    const highlight = document.createElement('div');
    highlight.id = '__ai_highlight';
    Object.assign(highlight.style, {
        position: 'fixed', zIndex: '2147483646', pointerEvents: 'none',
        border: '3px solid #7c6ff7', borderRadius: '4px',
        background: 'rgba(124,111,247,0.12)', display: 'none',
        boxShadow: '0 0 12px rgba(124,111,247,0.4)',
        transition: 'all 0.2s ease-out'
    });
    document.documentElement.appendChild(highlight);

    // --- Click ripple effect ---
    const ripple = document.createElement('div');
    ripple.id = '__ai_ripple';
    Object.assign(ripple.style, {
        position: 'fixed', zIndex: '2147483647', pointerEvents: 'none',
        width: '0px', height: '0px', borderRadius: '50%',
        background: 'rgba(124,111,247,0.5)', display: 'none',
        transition: 'width 0.4s ease-out, height 0.4s ease-out, opacity 0.4s ease-out',
        transform: 'translate(-50%, -50%)'
    });
    document.documentElement.appendChild(ripple);

    // Expose helper functions globally
    window.__ai = {
        cursor, label, highlight, ripple,

        showLabel(text) {
            label.textContent = text;
            label.style.display = 'block';
            label.style.opacity = '1';
        },

        hideLabel() {
            label.style.opacity = '0';
            setTimeout(() => { label.style.display = 'none'; }, 300);
        },

        async moveCursorTo(x, y, durationMs) {
            cursor.style.display = 'block';
            const startX = parseFloat(cursor.style.left) || window.innerWidth / 2;
            const startY = parseFloat(cursor.style.top) || window.innerHeight / 2;
            const steps = Math.max(Math.round(durationMs / 16), 10);

            for (let i = 0; i <= steps; i++) {
                const t = i / steps;
                const ease = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
                const cx = startX + (x - startX) * ease;
                const cy = startY + (y - startY) * ease;
                cursor.style.left = cx + 'px';
                cursor.style.top = cy + 'px';
                await new Promise(r => requestAnimationFrame(r));
            }
        },

        highlightElement(el) {
            const rect = el.getBoundingClientRect();
            Object.assign(highlight.style, {
                display: 'block',
                left: (rect.left - 4) + 'px',
                top: (rect.top - 4) + 'px',
                width: (rect.width + 8) + 'px',
                height: (rect.height + 8) + 'px'
            });
        },

        hideHighlight() {
            highlight.style.display = 'none';
        },

        showRipple(x, y) {
            Object.assign(ripple.style, {
                left: x + 'px', top: y + 'px',
                width: '0px', height: '0px', opacity: '1', display: 'block'
            });
            requestAnimationFrame(() => {
                Object.assign(ripple.style, {
                    width: '50px', height: '50px', opacity: '0'
                });
            });
            setTimeout(() => { ripple.style.display = 'none'; }, 500);
        },

        hideCursor() {
            cursor.style.display = 'none';
        }
    };
})()
"""

# ─── Click with visual: highlight → cursor move → ripple → click ──────────

CLICK_ELEMENT = """
(async function(selector) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify({success: false, error: 'Element not found: ' + selector});

    el.scrollIntoView({behavior: 'smooth', block: 'center'});
    await new Promise(r => setTimeout(r, 400));

    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    // Visual: highlight element
    if (window.__ai) {
        window.__ai.showLabel('Clicking: ' + (el.textContent || el.tagName).trim().substring(0, 40));
        window.__ai.highlightElement(el);
        await window.__ai.moveCursorTo(x, y, 600);
        await new Promise(r => setTimeout(r, 200));
        window.__ai.showRipple(x, y);
        await new Promise(r => setTimeout(r, 150));
    }

    // Actual click
    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
        el.dispatchEvent(new PointerEvent(type, {
            bubbles: true, cancelable: true, view: window,
            clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse'
        }));
    });

    await new Promise(r => setTimeout(r, 300));
    if (window.__ai) {
        window.__ai.hideHighlight();
        window.__ai.hideLabel();
    }

    return JSON.stringify({
        success: true,
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || '').trim().substring(0, 100)
    });
})(%s)
"""

# ─── Type with visual: highlight → cursor move → character-by-character ────

TYPE_TEXT = """
(async function(selector, text, clearFirst) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify({success: false, error: 'Element not found: ' + selector});

    el.scrollIntoView({behavior: 'smooth', block: 'center'});
    await new Promise(r => setTimeout(r, 300));

    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    // Visual: move cursor and highlight
    if (window.__ai) {
        window.__ai.showLabel('Typing: ' + text.substring(0, 50) + (text.length > 50 ? '...' : ''));
        window.__ai.highlightElement(el);
        await window.__ai.moveCursorTo(x, y, 500);
        window.__ai.showRipple(x, y);
        await new Promise(r => setTimeout(r, 200));
    }

    el.focus();
    el.click();

    if (clearFirst) {
        el.value = '';
        el.dispatchEvent(new Event('input', {bubbles: true}));
    }

    // Type character by character with animation
    const nativeSetter =
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set ||
        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;

    for (let i = 0; i < text.length; i++) {
        const char = text[i];
        const currentVal = el.value + char;

        if (nativeSetter) {
            nativeSetter.call(el, currentVal);
        } else {
            el.value = currentVal;
        }

        el.dispatchEvent(new KeyboardEvent('keydown', {key: char, bubbles: true}));
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {key: char, bubbles: true}));

        // Typing speed: ~50ms per char, faster for long texts
        const delay = text.length > 30 ? 20 : 50;
        await new Promise(r => setTimeout(r, delay));
    }

    el.dispatchEvent(new Event('change', {bubbles: true}));

    await new Promise(r => setTimeout(r, 200));
    if (window.__ai) {
        window.__ai.hideHighlight();
        window.__ai.hideLabel();
    }

    return JSON.stringify({success: true, value: el.value.substring(0, 100)});
})(%s, %s, %s)
"""

# ─── Scroll with visual cursor and label ───────────────────────────────────

SCROLL_PAGE = """
(async function(direction, pixels) {
    if (window.__ai) {
        window.__ai.showLabel('Scrolling ' + direction + '...');
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        await window.__ai.moveCursorTo(cx, cy, 300);
    }

    const amount = direction === 'up' ? -pixels : pixels;
    window.scrollBy({top: amount, behavior: 'smooth'});

    await new Promise(r => setTimeout(r, 600));
    if (window.__ai) window.__ai.hideLabel();

    return JSON.stringify({
        success: true,
        scrollY: Math.round(window.scrollY),
        scrollHeight: document.body.scrollHeight,
        innerHeight: window.innerHeight
    });
})(%s, %s)
"""

# ─── Press key with visual label ───────────────────────────────────────────

PRESS_KEY = """
(async function(key) {
    if (window.__ai) {
        window.__ai.showLabel('Pressing key: ' + key);
    }

    const el = document.activeElement || document.body;
    const opts = {key: key, code: 'Key' + key, bubbles: true, cancelable: true};

    el.dispatchEvent(new KeyboardEvent('keydown', opts));
    el.dispatchEvent(new KeyboardEvent('keypress', opts));
    el.dispatchEvent(new KeyboardEvent('keyup', opts));

    if (key === 'Enter' && el.form) {
        el.form.dispatchEvent(new Event('submit', {bubbles: true, cancelable: true}));
    }

    await new Promise(r => setTimeout(r, 500));
    if (window.__ai) window.__ai.hideLabel();

    return JSON.stringify({success: true, key: key});
})(%s)
"""

# ─── Get interactive elements (no visual needed) ──────────────────────────

GET_INTERACTIVE_ELEMENTS = """
(function() {
    const sel = 'a[href], button, input, textarea, select, [role="button"], [onclick], [tabindex]:not([tabindex="-1"])';
    const els = document.querySelectorAll(sel);
    const results = [];
    const seen = new Set();

    for (let i = 0; i < els.length && results.length < 50; i++) {
        const el = els[i];
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        if (rect.bottom < 0 || rect.top > window.innerHeight) continue;

        const tag = el.tagName.toLowerCase();
        const type = el.getAttribute('type') || '';
        const text = (el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim().substring(0, 80);
        const id = el.id ? '#' + el.id : '';
        const name = el.getAttribute('name') ? '[name="' + el.getAttribute('name') + '"]' : '';
        const cls = el.className && typeof el.className === 'string'
            ? '.' + el.className.trim().split(/\\s+/).slice(0, 2).join('.')
            : '';

        let selector = tag;
        if (id) selector = tag + id;
        else if (name) selector = tag + name;
        else if (cls) selector = tag + cls;

        const key = selector + '|' + text;
        if (seen.has(key)) continue;
        seen.add(key);

        results.push({
            index: results.length,
            tag: tag,
            type: type,
            text: text,
            selector: selector,
            href: el.href || ''
        });
    }

    return JSON.stringify(results);
})()
"""

# ─── Extract text (no visual needed) ──────────────────────────────────────

EXTRACT_TEXT = """
(function(selector) {
    const el = document.querySelector(selector);
    if (!el) return JSON.stringify({success: false, error: 'Element not found'});
    return JSON.stringify({
        success: true,
        text: el.innerText.substring(0, 5000)
    });
})(%s)
"""

# ─── Get page info (no visual needed) ─────────────────────────────────────

GET_PAGE_INFO = """
(function() {
    return JSON.stringify({
        url: window.location.href,
        title: document.title,
        scrollY: Math.round(window.scrollY),
        scrollHeight: document.body.scrollHeight,
        innerHeight: window.innerHeight,
        innerWidth: window.innerWidth
    });
})()
"""

# ─── Wait for element (no visual needed) ──────────────────────────────────

WAIT_FOR_ELEMENT = """
(function(selector, timeoutMs) {
    return new Promise(function(resolve) {
        const existing = document.querySelector(selector);
        if (existing) { resolve(JSON.stringify({success: true, found: true})); return; }

        const observer = new MutationObserver(function() {
            if (document.querySelector(selector)) {
                observer.disconnect();
                resolve(JSON.stringify({success: true, found: true}));
            }
        });
        observer.observe(document.body, {childList: true, subtree: true});

        setTimeout(function() {
            observer.disconnect();
            resolve(JSON.stringify({success: false, error: 'Timeout waiting for ' + selector}));
        }, timeoutMs);
    });
})(%s, %s)
"""

# ─── File upload — inject file into <input type="file"> ────────────────────

UPLOAD_FILE = """
(async function(selector, fileName, fileBase64, mimeType) {
    const el = document.querySelector(selector);
    if (!el || el.type !== 'file')
        return JSON.stringify({success: false, error: 'File input not found: ' + selector});

    if (window.__ai) {
        window.__ai.showLabel('Uploading: ' + fileName);
        window.__ai.highlightElement(el);
        await new Promise(r => setTimeout(r, 500));
    }

    const byteChars = atob(fileBase64);
    const bytes = new Uint8Array(byteChars.length);
    for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
    const file = new File([bytes], fileName, {type: mimeType});

    const dt = new DataTransfer();
    dt.items.add(file);
    el.files = dt.files;

    el.dispatchEvent(new Event('change', {bubbles: true}));
    el.dispatchEvent(new Event('input', {bubbles: true}));

    await new Promise(r => setTimeout(r, 300));
    if (window.__ai) { window.__ai.hideHighlight(); window.__ai.hideLabel(); }

    return JSON.stringify({success: true, fileName: fileName, size: bytes.length});
})(%s, %s, %s, %s)
"""

# ─── Detect CAPTCHA / 2FA elements ────────────────────────────────────────

DETECT_CAPTCHA = """
(function() {
    const signals = [];

    // reCAPTCHA
    if (document.querySelector('iframe[src*="recaptcha"]') ||
        document.querySelector('.g-recaptcha') ||
        document.querySelector('#recaptcha'))
        signals.push('recaptcha');

    // hCaptcha
    if (document.querySelector('iframe[src*="hcaptcha"]') ||
        document.querySelector('.h-captcha'))
        signals.push('hcaptcha');

    // Cloudflare Turnstile
    if (document.querySelector('iframe[src*="challenges.cloudflare"]') ||
        document.querySelector('.cf-turnstile'))
        signals.push('cloudflare_turnstile');

    // Generic CAPTCHA images/text
    if (document.querySelector('img[alt*="captcha" i]') ||
        document.querySelector('img[src*="captcha" i]') ||
        document.querySelector('[class*="captcha" i]'))
        signals.push('generic_captcha');

    // 2FA / OTP inputs
    const otpInputs = document.querySelectorAll(
        'input[name*="otp" i], input[name*="code" i], input[name*="2fa" i], ' +
        'input[autocomplete="one-time-code"], input[inputmode="numeric"][maxlength="6"]'
    );
    if (otpInputs.length > 0) signals.push('2fa_otp');

    // SMS verification text
    const bodyText = document.body.innerText.toLowerCase();
    if (bodyText.includes('verify your identity') || bodyText.includes('verification code') ||
        bodyText.includes('enter the code') || bodyText.includes('two-factor'))
        signals.push('2fa_text');

    return JSON.stringify({detected: signals.length > 0, signals: signals});
})()
"""

# ─── Shadow DOM piercing — query inside shadow roots ──────────────────────

QUERY_SHADOW_DOM = """
(function(selector) {
    function deepQuery(root, sel) {
        let result = root.querySelector(sel);
        if (result) return result;

        const allEls = root.querySelectorAll('*');
        for (const el of allEls) {
            if (el.shadowRoot) {
                result = deepQuery(el.shadowRoot, sel);
                if (result) return result;
            }
        }
        return null;
    }

    const el = deepQuery(document, selector);
    if (!el) return JSON.stringify({success: false, error: 'Element not found in shadow DOM'});

    const rect = el.getBoundingClientRect();
    return JSON.stringify({
        success: true,
        tag: el.tagName.toLowerCase(),
        text: (el.textContent || '').trim().substring(0, 100),
        x: Math.round(rect.left + rect.width / 2),
        y: Math.round(rect.top + rect.height / 2),
        visible: rect.width > 0 && rect.height > 0
    });
})(%s)
"""

# ─── Click inside shadow DOM using coordinates ────────────────────────────

CLICK_SHADOW_DOM = """
(async function(selector) {
    function deepQuery(root, sel) {
        let result = root.querySelector(sel);
        if (result) return result;
        const allEls = root.querySelectorAll('*');
        for (const el of allEls) {
            if (el.shadowRoot) {
                result = deepQuery(el.shadowRoot, sel);
                if (result) return result;
            }
        }
        return null;
    }

    const el = deepQuery(document, selector);
    if (!el) return JSON.stringify({success: false, error: 'Shadow element not found: ' + selector});

    el.scrollIntoView({behavior: 'smooth', block: 'center'});
    await new Promise(r => setTimeout(r, 300));

    const rect = el.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;

    if (window.__ai) {
        window.__ai.showLabel('Clicking (shadow): ' + (el.textContent || el.tagName).trim().substring(0, 40));
        window.__ai.highlightElement(el);
        await window.__ai.moveCursorTo(x, y, 600);
        window.__ai.showRipple(x, y);
        await new Promise(r => setTimeout(r, 200));
    }

    el.click();
    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
        el.dispatchEvent(new PointerEvent(type, {
            bubbles: true, cancelable: true, composed: true, view: window,
            clientX: x, clientY: y
        }));
    });

    await new Promise(r => setTimeout(r, 300));
    if (window.__ai) { window.__ai.hideHighlight(); window.__ai.hideLabel(); }

    return JSON.stringify({success: true, tag: el.tagName.toLowerCase(), text: (el.textContent || '').trim().substring(0, 100)});
})(%s)
"""

# ─── Get all iframe info ──────────────────────────────────────────────────

GET_IFRAMES = """
(function() {
    const frames = document.querySelectorAll('iframe');
    const results = [];
    frames.forEach((f, i) => {
        results.push({
            index: i,
            src: f.src || '',
            name: f.name || '',
            id: f.id || '',
            width: f.offsetWidth,
            height: f.offsetHeight,
            visible: f.offsetWidth > 0 && f.offsetHeight > 0
        });
    });
    return JSON.stringify(results);
})()
"""

# ─── Auto-fill form fields from a profile dict ───────────────────────────

AUTOFILL_FORM = """
(async function(fieldMap) {
    const map = JSON.parse(fieldMap);
    const results = [];

    for (const [selector, value] of Object.entries(map)) {
        const el = document.querySelector(selector);
        if (!el) { results.push({selector, success: false, error: 'not found'}); continue; }

        el.scrollIntoView({behavior: 'instant', block: 'center'});

        if (window.__ai) {
            window.__ai.highlightElement(el);
            const rect = el.getBoundingClientRect();
            await window.__ai.moveCursorTo(rect.left + rect.width/2, rect.top + rect.height/2, 400);
            await new Promise(r => setTimeout(r, 100));
        }

        el.focus();
        el.click();

        const nativeSetter =
            Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set ||
            Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;

        if (nativeSetter) nativeSetter.call(el, value);
        else el.value = value;

        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));

        results.push({selector, success: true, value: value.substring(0, 30)});
        await new Promise(r => setTimeout(r, 200));
    }

    if (window.__ai) { window.__ai.hideHighlight(); window.__ai.hideLabel(); }
    return JSON.stringify({success: true, filled: results});
})(%s)
"""

# ─── Hide all visuals (cleanup) ───────────────────────────────────────────

HIDE_VISUALS = """
(function() {
    if (window.__ai) {
        window.__ai.hideCursor();
        window.__ai.hideHighlight();
        window.__ai.hideLabel();
    }
})()
"""
