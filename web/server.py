"""Local history dashboard (Flask on 127.0.0.1).

Hardening vs upstream:
- Host header allowlist: only 127.0.0.1:<port> / localhost:<port>. A malicious
  web page can't use DNS rebinding to read your dictation history.
- No external assets (upstream loaded Tailwind from a CDN and Google Fonts):
  opening the dashboard makes zero requests outside your Mac.
- Strict CSP, no framing, no sniffing, no caching.
"""
import socket
import threading
from flask import Flask, abort, jsonify, render_template_string, request
from db.database import TranscriptionDB

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

_ALLOWED_HOSTS: set[str] = set()

_CSP = (
    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)


def _allowed_hosts_for(port: int) -> set[str]:
    return {f"127.0.0.1:{port}", f"localhost:{port}"}


@app.before_request
def _check_host():
    host = (request.headers.get("Host") or "").strip().lower()
    if host not in _ALLOWED_HOSTS:
        abort(403)


@app.after_request
def _security_headers(resp):
    resp.headers["Content-Security-Policy"] = _CSP
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return resp


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SFlow - Transcripciones</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; padding: 24px; min-height: 100vh; background: #0a0a0a; color: #e5e5e5;
               font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; }
        .wrap { max-width: 56rem; margin: 0 auto; }
        header { display: flex; align-items: center; justify-content: space-between; gap: 12px;
                 margin-bottom: 32px; flex-wrap: wrap; }
        .brand { display: flex; align-items: center; gap: 12px; font-size: 24px; font-weight: 600; }
        .purple { color: #8c50dc; } .orange { color: #ffa028; }
        .low { color: rgba(255,255,255,.6); font-size: 18px; margin-left: 4px; }
        .badge { font-size: 12px; color: rgba(255,255,255,.3); background: rgba(255,255,255,.05);
                 padding: 4px 8px; border-radius: 999px; }
        .tools { display: flex; align-items: center; gap: 12px; }
        input { background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); color: #e5e5e5;
                border-radius: 8px; padding: 6px 12px; font-size: 14px; width: 12rem; outline: none; }
        input:focus { border-color: rgba(255,255,255,.2); }
        button { background: none; border: 0; color: rgba(255,255,255,.4); cursor: pointer; font-size: 13px;
                 padding: 4px 8px; border-radius: 6px; }
        button:hover { color: rgba(255,255,255,.75); background: rgba(255,255,255,.05); }
        .card { background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.06);
                border-radius: 12px; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { color: rgba(255,255,255,.4); font-size: 11px; text-transform: uppercase; letter-spacing: .05em;
             text-align: left; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,.05); }
        td { padding: 12px 16px; vertical-align: top; border-bottom: 1px solid rgba(255,255,255,.03); }
        tr.row { cursor: pointer; } tr.row:hover { background: rgba(255,255,255,.05); }
        .time { color: rgba(255,255,255,.3); font-size: 12px; white-space: nowrap; width: 9rem; }
        .dur { color: rgba(255,255,255,.2); font-size: 12px; text-align: right; width: 5rem; }
        .txt { color: rgba(255,255,255,.8); font-size: 14px; }
        .preview { max-height: 2.6em; overflow: hidden; transition: max-height .3s ease; }
        .preview.expanded { max-height: 500px; }
        .empty { text-align: center; padding: 48px; color: rgba(255,255,255,.2); font-size: 14px; }
        .hidden { display: none; }
        footer { margin-top: 16px; text-align: center; color: rgba(255,255,255,.15); font-size: 12px; }
        .copied { animation: flash .5s ease; }
        @keyframes flash { 0%,100% { background: transparent; } 50% { background: rgba(80,220,120,.1); } }
    </style>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="brand">
                <div><span class="purple">S</span><span class="orange">f</span><span class="low">low</span></div>
                <span class="badge" id="count-badge">-</span>
            </div>
            <div class="tools">
                <input type="text" id="search" placeholder="Buscar...">
                <button id="refresh">Actualizar</button>
            </div>
        </header>

        <div class="card">
            <table>
                <thead>
                    <tr><th>Hora</th><th>Transcripción</th><th style="text-align:right">Dur.</th><th></th></tr>
                </thead>
                <tbody id="tbody"></tbody>
            </table>
            <div id="empty" class="empty hidden">No hay transcripciones todavía</div>
        </div>

        <footer>SFlow &middot; historial local, no sale de tu Mac</footer>
    </div>

    <script>
        let allData = [];
        let shown = [];

        async function loadData() {
            const res = await fetch('/api/transcriptions');
            allData = await res.json();
            applyFilter();
        }

        function el(tag, cls, text) {
            const e = document.createElement(tag);
            if (cls) e.className = cls;
            if (text !== undefined) e.textContent = text;
            return e;
        }

        function renderTable(data) {
            shown = data;
            const tbody = document.getElementById('tbody');
            document.getElementById('count-badge').textContent = allData.length + ' total';
            tbody.replaceChildren();
            document.getElementById('empty').classList.toggle('hidden', data.length !== 0);
            data.forEach((t) => {
                const date = new Date(t.created_at + 'Z');
                const time = date.toLocaleString('es-AR', {
                    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
                });
                const tr = el('tr', 'row');
                tr.appendChild(el('td', 'time', time));
                const td = el('td', 'txt');
                const prev = el('div', 'preview', t.text);
                td.appendChild(prev);
                tr.appendChild(td);
                tr.appendChild(el('td', 'dur', t.duration_seconds ? t.duration_seconds.toFixed(1) + 's' : '-'));
                const tdBtn = el('td');
                const btn = el('button', '', 'Copiar');
                btn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    navigator.clipboard.writeText(t.text);
                    tr.classList.add('copied');
                    btn.textContent = 'OK';
                    setTimeout(() => { btn.textContent = 'Copiar'; tr.classList.remove('copied'); }, 1000);
                });
                tdBtn.appendChild(btn);
                tr.appendChild(tdBtn);
                tr.addEventListener('click', () => prev.classList.toggle('expanded'));
                tbody.appendChild(tr);
            });
        }

        function applyFilter() {
            const q = document.getElementById('search').value.toLowerCase();
            renderTable(q ? allData.filter(t => (t.text || '').toLowerCase().includes(q)) : allData);
        }

        document.getElementById('search').addEventListener('input', applyFilter);
        document.getElementById('refresh').addEventListener('click', loadData);
        loadData();
        setInterval(loadData, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/transcriptions")
def get_transcriptions():
    db = TranscriptionDB()
    return jsonify(db.get_recent(limit=200))


def _find_free_port(start: int = 5678, attempts: int = 10) -> int:
    """Find an available port starting from `start`."""
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start  # fallback


def start_web_server(port: int = None) -> int:
    """Start Flask in a daemon thread so it doesn't block the Qt event loop."""
    if port is None:
        port = _find_free_port()
    _ALLOWED_HOSTS.clear()
    _ALLOWED_HOSTS.update(_allowed_hosts_for(port))
    thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    return port
