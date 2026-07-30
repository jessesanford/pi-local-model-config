import http.server, socketserver, urllib.request, json, sys, time

UPSTREAM = "http://127.0.0.1:8080"
LOG = "/tmp/pi_proxy.log"

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass
    def _proxy(self, method):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method in ("POST","DELETE","PUT") else None
        req = urllib.request.Request(UPSTREAM + self.path, data=body, method=method,
                                     headers={k:v for k,v in self.headers.items() if k.lower() not in ("host","content-length")})
        t0 = time.time()
        try:
            r = urllib.request.urlopen(req, timeout=600)
            data = r.read()
            self.send_response(r.status)
            for k,v in r.getheaders():
                if k.lower() not in ("transfer-encoding","content-encoding","connection"): self.send_header(k,v)
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode()); data=b""
        # log
        if self.path.endswith("/chat/completions") and body:
            try:
                req_j = json.loads(body)
                msgs = req_j.get("messages", [])
                sys_len = sum(len(m.get("content","")) for m in msgs if m.get("role") in ("system","developer"))
                user_len = sum(len(m.get("content","")) for m in msgs if m.get("role")=="user")
                total_chars = sum(len(str(m.get("content",""))) for m in msgs)
                stream = req_j.get("stream", False)
                # extract server timings
                prompt_n = prompt_ms = pred_n = pred_ms = None
                if not stream:
                    try:
                        rj = json.loads(data)
                        t = rj.get("timings",{}); prompt_n=t.get("prompt_n"); prompt_ms=t.get("prompt_ms")
                        pred_n=t.get("predicted_n"); pred_ms=t.get("predicted_ms")
                    except: pass
                else:
                    # scan SSE for last data line with timings
                    for line in reversed(data.split(b"\n")):
                        line = line.strip()
                        if line.startswith(b"data:") and b"timings" in line:
                            try:
                                j = json.loads(line[5:].strip())
                                t = j.get("timings",{}) or (j.get("x_timings",{}))
                                if t:
                                    prompt_n=t.get("prompt_n"); prompt_ms=t.get("prompt_ms")
                                    pred_n=t.get("predicted_n"); pred_ms=t.get("predicted_ms")
                                    break
                            except: pass
                with open(LOG,"a") as f:
                    f.write(json.dumps({
                        "t": round(time.time()-t0,2),
                        "stream": stream,
                        "num_msgs": len(msgs),
                        "roles": [m.get("role") for m in msgs],
                        "sys_chars": sys_len, "user_chars": user_len, "total_chars": total_chars,
                        "prompt_n": prompt_n, "prompt_ms": prompt_ms,
                        "predicted_n": pred_n, "predicted_ms": pred_ms,
                        "tools": len(req_j.get("tools") or []),
                    })+"\n")
            except Exception as e:
                open(LOG,"a").write(f"logerr: {e}\n")
    def do_GET(self): self._proxy("GET")
    def do_POST(self): self._proxy("POST")
    def do_DELETE(self): self._proxy("DELETE")
    def do_PUT(self): self._proxy("PUT")

open(LOG,"w").close()
with socketserver.ThreadingTCPServer(("127.0.0.1", 8090), H) as s:
    s.allow_reuse_address = True
    s.serve_forever()
