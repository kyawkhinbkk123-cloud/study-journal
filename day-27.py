# M7 Day 27 - Support Agent HTTP API (pure stdlib, no fastapi)
# Alt: fastapi venv is broken (pydantic_core missing) -> system fix needed,
# but per Kyaw rule we keep learning OFF the main Hermes system.
# So we build the SAME concept (HTTP endpoint + LLM) with stdlib http.server.
import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import providers

from http.server import BaseHTTPRequestHandler, HTTPServer

SYSTEM = "You are a concise customer support agent. Answer in 1-2 sentences."


def ask_llm(message: str) -> dict:
    resp = providers.chat([{"role": "user", "content": message}], system=SYSTEM)
    text = resp["text"] if isinstance(resp, dict) else str(resp)
    provider = resp.get("provider") if isinstance(resp, dict) else "?"
    return {"reply": text, "provider": provider}


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/chat":
            self._send(404, {"error": "not found"})
            return
        n = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(n) or b"{}")
        out = ask_llm(payload.get("message", ""))
        self._send(200, out)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    # 1) health check
    import threading, urllib.request
    srv = HTTPServer(("127.0.0.1", 8799), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        with urllib.request.urlopen("http://127.0.0.1:8799/health", timeout=5) as r:
            h = json.loads(r.read())
        assert h.get("status") == "ok", h
        print("GET /health OK:", h)
        # 2) chat check (real LLM)
        req = urllib.request.Request(
            "http://127.0.0.1:8799/chat",
            data=json.dumps({"message": "How do I reset my password?"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            c = json.loads(r.read())
        assert len(c.get("reply", "")) > 0, c
        print("POST /chat OK")
        print("  reply:", c["reply"][:120])
        print("  via:", c["provider"])
        print("PASS: stdlib Support-Agent API works (no fastapi needed)")
    finally:
        srv.shutdown()
