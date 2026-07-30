#!/usr/bin/env python3
"""Benchmark oMLX vs Nativ: decode tok/s, prefill tok/s, TTFT."""
import json, time, urllib.request, urllib.error, sys

def call(url, model, prompt, max_tokens=300, stream=False):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": stream,
    }).encode()
    req = urllib.request.Request(url + "/chat/completions",
                                  data=body,
                                  headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        if stream:
            ttft = None
            first_token_at = None
            content_len = 0
            for line in r:
                if line.startswith(b"data:"):
                    payload = line[5:].strip()
                    if payload == b"[DONE]":
                        break
                    try:
                        j = json.loads(payload)
                    except Exception:
                        continue
                    delta = j.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta and ttft is None:
                        ttft = time.time() - t0
                    if delta:
                        content_len += len(delta)
            total = time.time() - t0
            return {"ttft": ttft, "wall": total}
        data = json.loads(r.read())
    wall = time.time() - t0
    u = data.get("usage", {})
    return {
        "prompt_toks": u.get("prompt_tokens", 0),
        "gen_toks": u.get("completion_tokens", 0),
        "wall": wall,
        "reported_total": data.get("total_time"),
        "reported_load": data.get("model_load_duration", 0),
    }

def bench(label, url, model, prompt, runs=3, max_tokens=300):
    print(f"\n=== {label} ({model}) ===")
    for i in range(runs):
        try:
            r = call(url, model, prompt, max_tokens=max_tokens)
            active = r["wall"] - (r.get("reported_load") or 0)
            tps = r["gen_toks"] / active if active > 0 else 0
            print(f"  run{i+1}: prompt={r['prompt_toks']}t gen={r['gen_toks']}t "
                  f"wall={r['wall']:.2f}s load={r.get('reported_load',0):.2f}s "
                  f"active={active:.2f}s => decode≈{tps:.1f} t/s")
        except urllib.error.HTTPError as e:
            print(f"  run{i+1}: HTTP {e.code}: {e.read()[:200]}")
        except Exception as e:
            print(f"  run{i+1}: {type(e).__name__}: {e}")

def bench_ttft(label, url, model, prompt):
    print(f"\n--- TTFT {label} ({model}) ---")
    for i in range(2):
        try:
            r = call(url, model, prompt, max_tokens=50, stream=True)
            print(f"  run{i+1}: TTFT={r['ttft']*1000:.0f}ms wall={r['wall']*1000:.0f}ms")
        except Exception as e:
            print(f"  run{i+1}: {e}")

if __name__ == "__main__":
    OMLX = "http://127.0.0.1:8000/v1"
    NATIV = "http://127.0.0.1:8080/v1"
    OMLX_M = "mlx-community--Laguna-S-2.1-oQ4e-fast"
    NATIV_M = "mlx-community/Laguna-S-2.1-oQ4e-fast"

    small_prompt = "Write a detailed 400-word explanation of how HashMap works. Keep going until you hit the token limit."
    long_prompt = "the quick brown fox jumps over the lazy dog. " * 130 + " Now write a 200-word story."

    bench("oMLX small prompt / 500 gen", OMLX, OMLX_M, small_prompt, runs=3, max_tokens=500)
    bench("oMLX 1k prompt / 300 gen", OMLX, OMLX_M, long_prompt, runs=2, max_tokens=300)
    bench_ttft("oMLX small", OMLX, OMLX_M, "hi")
    bench_ttft("oMLX 1k prompt", OMLX, OMLX_M, long_prompt)

    bench("Nativ small prompt / 500 gen", NATIV, NATIV_M, small_prompt, runs=2, max_tokens=500)
    bench_ttft("Nativ 1k prompt", NATIV, NATIV_M, long_prompt)
