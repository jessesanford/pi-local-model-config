"""Dumb passthrough proxy that logs each request body verbatim."""
import http.server, socketserver, urllib.request, os, sys

UPSTREAM = "http://127.0.0.1:8000"
LOGDIR = "/tmp/pi_bodies"
os.makedirs(LOGDIR, exist_ok=True)
COUNT = [0]

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def _proxy(self, method):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method in ("POST","DELETE","PUT") else None
        if body and self.path.endswith("/chat/completions"):
            COUNT[0] += 1
            with open(f"{LOGDIR}/req_{COUNT[0]:03d}.json", "wb") as f:
                f.write(body)
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=method,
                                     headers={k:v for k,v in self.headers.items() if k.lower() not in ("host","content-length")})
        try:
            r = urllib.request.urlopen(req, timeout=600)
            data = r.read()
            self.send_response(r.status)
            for k,v in r.getheaders():
                if k.lower() not in ("transfer-encoding","content-encoding","connection"): self.send_header(k,v)
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())
    def do_GET(self): self._proxy("GET")
    def do_POST(self): self._proxy("POST")
    def do_DELETE(self): self._proxy("DELETE")
    def do_PUT(self): self._proxy("PUT")

with socketserver.ThreadingTCPServer(("127.0.0.1", 8090), H) as s:
    s.allow_reuse_address = True
    s.serve_forever()
