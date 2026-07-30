# Master rebuild prompt

Paste the entire block below (from `---` to `---`) into a Claude session (Claude Code,
Claude.ai desktop with tool access, or similar) running on the target Mac. Claude
will install and configure everything end-to-end without further prompts.

---

I want you to fully reinstall and configure my local pi + oMLX + Laguna-S 2.1 setup on this Mac
following the repo at `~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/`.

**Rules:**
- Do the phases IN ORDER. Verify each phase before moving on.
- Never skip a verification step. If a check fails, stop and tell me before continuing.
- Never print, echo, or hardcode credentials (GitHub tokens, HF tokens, keychain secrets) into any tool call, file, or log. If you need one, ask me to provide it in the current turn.
- Ask before making any destructive change (deleting model caches, uninstalling apps, force-pushing, `rm -rf`).

## Phase 1 — sanity + prerequisites

1. Report OS, chip, GPU cores, RAM, current power mode:
   ```
   sw_vers
   sysctl -n machdep.cpu.brand_string
   system_profiler SPHardwareDataType | grep -E "Memory|Chip"
   system_profiler SPDisplaysDataType | grep -E "Chipset|Cores"
   pmset -g | grep -iE "lowpowermode|powermode"
   ```
   Requirements: Apple Silicon (M-series), ideally 40+ GPU cores, 128 GB RAM.
   - If RAM < 96 GB, WARN — Laguna oQ4e-fast needs ~60 GB resident and leaves little headroom.
   - If `powermode 1` (Low Power Mode): STOP. Tell me to disable it in System Settings → Battery. MLX inference runs at ~half speed under Low Power Mode.
2. Detect whether the machine is behind a corporate SSL-intercepting proxy (Zscaler etc.):
   ```
   echo | openssl s_client -connect huggingface.co:443 -servername huggingface.co 2>/dev/null | grep -i issuer | head -1
   ```
   If issuer contains "Zscaler" or a non-Amazon/non-Cloudflare CA name, set `ZSCALER_ACTIVE=1` and follow the "Zscaler branches" callouts below. Otherwise skip them.
3. Homebrew: `which brew`. If missing:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
4. HuggingFace CLI (required for Phase 2 downloads):
   ```
   which hf || brew install huggingface-cli
   ```
5. pi CLI: `which pi`. If missing:
   ```
   curl -fsSL https://pi.dev/install.sh | sh
   ```
6. oMLX:
   ```
   which omlx || {
     brew tap jundot/omlx https://github.com/jundot/omlx
     brew trust jundot/omlx
     brew install omlx
   }
   omlx --version
   ```
   Expect version 0.5.3+.

### Zscaler branch (only if `ZSCALER_ACTIVE=1`)

Extract the Zscaler root CA and merge it with certifi so Python-based HTTP clients (hf, oMLX's mlx-vlm-server, Nativ's bundled Python) accept SSL through the interception proxy. This is a one-time setup.

```
mkdir -p "$HOME/.config/nativ"
security find-certificate -a -c "Zscaler" -p /Library/Keychains/System.keychain > /tmp/zscaler.pem
# Requires the running Python's certifi to be installed. If /usr/bin/python3 doesn't have certifi,
# use any python that does (Nativ's bundled one works, or `python3 -m pip install certifi --user`).
CERTIFI_PEM=$(python3 -c 'import certifi; print(certifi.where())' 2>/dev/null || \
              /Applications/Nativ.app/Contents/Frameworks/NativServerKit.framework/Resources/mlx-vlm-server/python/bin/python3 -c 'import certifi; print(certifi.where())' 2>/dev/null)
[ -n "$CERTIFI_PEM" ] && cat "$CERTIFI_PEM" /tmp/zscaler.pem > "$HOME/.config/nativ/cacert.pem"
wc -l "$HOME/.config/nativ/cacert.pem"   # sanity: should be a few thousand lines
```

Then set launchctl user env vars so all future processes (including GUI apps launched from Finder) inherit them:

```
launchctl setenv SSL_CERT_FILE      "$HOME/.config/nativ/cacert.pem"
launchctl setenv REQUESTS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv CURL_CA_BUNDLE     "$HOME/.config/nativ/cacert.pem"
launchctl setenv HF_HUB_DISABLE_XET 1
launchctl setenv HF_HUB_ENABLE_HF_TRANSFER 0
```

Persist across reboots by adding the same lines (as `launchctl setenv ...`) to a LaunchAgent plist if the user cares. Otherwise they'll be re-set on next login by running `omlx-restart` (which exports them inline).

**Zscaler quirks to remember:**
- HuggingFace's Xet CDN protocol times out through Zscaler; `HF_HUB_DISABLE_XET=1` forces classic HTTP downloads which work fine.
- Zscaler DLP blocks Python source file downloads. If a model repo contains a `config.py` (e.g. `poolside/Laguna-S-2.1-DFlash`), it returns an HTML block page instead of the real file. Ask me to briefly disconnect Zscaler for that specific fetch, then reconnect.
- Direct `curl` uses the macOS system keychain which already has the Zscaler root — that's why curl works even when Python doesn't. Don't be surprised if `curl` succeeds and `hf download` fails on the same URL.

## Phase 2 — models

Primary model: `mlx-community/Laguna-S-2.1-oQ4e-fast` (~60 GB, 1M context, 13 safetensors).
Nice-to-have: `mlx-community/Laguna-S-2.1-oQ4e` (~60 GB, slower but useful for A/B).
Skip: `poolside/Laguna-S-2.1-DFlash` — download procedure documented in Phase 2c but it is NOT usable today (see Known Limitations).

### 2a — check what already exists

```
ls ~/.cache/huggingface/hub/models--mlx-community--Laguna-S-2.1-oQ4e-fast/blobs/ 2>/dev/null | wc -l
ls ~/.lmstudio/models/mlx-community/Laguna-S-2.1-oQ4e-fast/*.safetensors 2>/dev/null | wc -l
```

Expected complete state: 13 safetensors + small text files.

### 2b — if you have LM Studio downloads but not HF cache: hardlink

Zero storage cost. Run:
```
python3 ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/tools/link_lmstudio_to_hf.py
```
This scans `~/.lmstudio/models/*/*/` for MLX models (config.json + safetensors), queries HuggingFace for authentic blob etags, hardlinks each file into `~/.cache/huggingface/hub/models--<org>--<repo>/blobs/<etag>` with proper `snapshots/<revision>/` symlinks. Verifies with the HF manifest so sizes must match; skips repos that don't exist upstream.

Verify:
```
du -sh ~/.cache/huggingface/hub/models--mlx-community--Laguna-S-2.1-oQ4e-fast/
# expect ~60 GB
find ~/.cache/huggingface/hub/models--mlx-community--Laguna-S-2.1-oQ4e-fast/snapshots -type l | wc -l
# expect 26 symlinks (matches HF file count)
```

### 2c — if neither cache exists: download

If not behind Zscaler:
```
hf download mlx-community/Laguna-S-2.1-oQ4e-fast
```

If behind Zscaler and the CA workaround from Phase 1 is applied, `hf download` should work.
If it still fails, fall back to LM Studio's UI (its download path is different and more resilient) then re-run Phase 2b to hardlink.

Optional DFlash (draft model, ~2 GB, currently unusable but downloadable for future):
- Small files work fine over Zscaler
- The safetensors is a single 2 GB blob — direct curl with resume works well:
  ```
  DST=$HOME/.cache/huggingface/hub/models--poolside--Laguna-S-2.1-DFlash
  mkdir -p "$DST/blobs" "$DST/snapshots/b0486d1586daa0d56435c508108171fc1c8daff9" "$DST/refs"
  echo -n b0486d1586daa0d56435c508108171fc1c8daff9 > "$DST/refs/main"
  ETAG=f24f08781c697c19952c02fb2e7e9bdf2071b79a711c2a44b836a74b9b62a1f4
  curl -sSL --retry 10 --retry-delay 3 -C - -o "$DST/blobs/$ETAG" \
    https://huggingface.co/poolside/Laguna-S-2.1-DFlash/resolve/main/model.safetensors
  ln -sf "../../blobs/$ETAG" "$DST/snapshots/b0486d1586daa0d56435c508108171fc1c8daff9/model.safetensors"
  ```
- `config.py` is blocked by Zscaler DLP. Ask me to briefly disconnect Zscaler, then:
  ```
  curl -sSL -o "$DST/blobs/0df8b20877a4fb34a49b676dfbcca4309cc8fd53" \
    https://huggingface.co/poolside/Laguna-S-2.1-DFlash/resolve/main/config.py
  ln -sf "../../blobs/0df8b20877a4fb34a49b676dfbcca4309cc8fd53" \
    "$DST/snapshots/b0486d1586daa0d56435c508108171fc1c8daff9/config.py"
  ```
- Same pattern for `.gitattributes`, `README.md`, `config.json`. Get their etags from
  `curl -s https://huggingface.co/api/models/poolside/Laguna-S-2.1-DFlash/tree/main`.

## Phase 3 — configs

```
mkdir -p ~/.omlx/models ~/.pi/agent

cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/configs/omlx-settings.json        ~/.omlx/settings.json
cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/configs/omlx-model-settings.json  ~/.omlx/models/model_settings.json

cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/configs/pi-settings.json          ~/.pi/agent/settings.json
cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/configs/pi-models.json            ~/.pi/agent/models.json
cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/configs/pi-APPEND_SYSTEM.md       ~/.pi/agent/APPEND_SYSTEM.md
```

`auth.secret_key` in `omlx-settings.json` is a placeholder — oMLX regenerates a real one on first launch. Fine.

## Phase 4 — scripts

```
mkdir -p ~/.local/bin
cp ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/scripts/omlx-* ~/.local/bin/
chmod +x ~/.local/bin/omlx-*

# persist PATH for future shells
grep -q '.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# ALSO source it into the current shell so the very next command below works
export PATH="$HOME/.local/bin:$PATH"
```

Scripts installed (all are portable — they skip Zscaler cert vars when `~/.config/nativ/cacert.pem` doesn't exist):
- `omlx-start` — foreground
- `omlx-start-bg` — background (managed via `omlx start`)
- `omlx-stop` — shut down
- `omlx-status` — health check
- `omlx-restart` — robust kill-then-relaunch with health wait

## Phase 5 — pi extensions

Install:
```
pi install npm:pi-subagents           # 2790★ - Claude Code-style parallel subagents
pi install npm:@narumitw/pi-retry     # stall-watchdog retry for local models
pi install npm:pi-smart-web-search    # (optional) improved web search
pi install npm:pi-smart-fetch         # (optional) improved fetch
```

**Do NOT install these** — tried and burned:
- `pi-lean-ctx` — depends on an external Rust binary; its installer aggressively modifies the system (wraps Claude Code, adds a shell allowlist that blocks arbitrary commands, injects MCP configs into VS Code, edits ~/.zshrc). Uninstall aggressively if already present: `pi remove npm:pi-lean-ctx` then `lean-ctx uninstall`.
- `pi-omlx-provider` and cousins (`@rolemodel/pi-omlx`, `pi-omlx-tps`, `pi-omlx-picker`) — pi already talks to oMLX via the generic `openai-completions` API; adding these tramples the custom sampling and thinking-format config.

## Phase 6 — start and verify

1. Start server:
   ```
   omlx-restart
   ```
   Should report "up on http://127.0.0.1:8000" and how many models it discovered.

2. Warm the model (first hit does the ~20s load; subsequent hits are fast):
   ```
   curl -sS -X POST http://127.0.0.1:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"mlx-community--Laguna-S-2.1-oQ4e-fast","messages":[{"role":"user","content":"reply: OK"}],"max_tokens":5,"stream":false}'
   ```
   Expect `"content":"OK"` within ~20s cold, ~1s warm.

3. End-to-end via pi:
   ```
   pi -p "reply: PI_OK"
   ```
   Should return `PI_OK`. If it hangs or reports connection error, run `omlx-restart` again.

4. Benchmark:
   ```
   python3 ~/workspace/pi-laguna-S-2.1-oQ4e-fast-config/tools/bench_omlx.py
   ```
   Expected on M5 Max, High Power mode, no competing GPU load:
   - decode: 60-65 tok/s
   - TTFT (small prompt): ~360 ms
   - TTFT (1k prompt): ~640 ms

   If decode is < 30 tok/s, in order:
   1. Confirm `pmset -g | grep powermode` shows `2` (High) or `0` (Auto), not `1` (Low).
   2. Check for competing GPU load — Apple Silicon VMs share GPU with MLX:
      ```
      ps aux | grep -iE "Virtualization|podman|OrbStack|Docker" | grep -v grep
      ```
      If a VM is running at significant CPU, pause it (`podman machine stop`, `orbctl stop`, etc.).
   3. Confirm the model actually loaded and isn't paging:
      ```
      curl -sS http://127.0.0.1:8000/v1/models/status | python3 -m json.tool | head -30
      ```

5. Sampling entropy test (verifies temp=1.0 / top_p=1.0 / top_k=20 took effect):
   ```
   for i in 1 2 3; do
     curl -sS -X POST http://127.0.0.1:8000/v1/chat/completions \
       -H "Content-Type: application/json" \
       -d '{"model":"mlx-community--Laguna-S-2.1-oQ4e-fast","messages":[{"role":"user","content":"Invent one creative fictional character name. Reply with just the name."}],"max_tokens":10,"stream":false}' \
     | python3 -c 'import json,sys;print(json.load(sys.stdin)["choices"][0]["message"]["content"].strip())'
   done
   ```
   Three different names → passing. Identical names three times → temperature/top_k didn't take effect; check `omlx-settings.json` and restart oMLX.

## Phase 7 — Nativ compatibility (optional)

Only if the user also runs Nativ (`/Applications/Nativ.app`):
1. Ensure the Zscaler CA bundle exists at `~/.config/nativ/cacert.pem` (see Phase 1 Zscaler branch).
2. The `launchctl setenv` vars from Phase 1 already cover Nativ — GUI apps launched from Finder inherit them at process start.
3. Quit and relaunch Nativ so it re-reads env.

## Phase 8 — auto-start (optional)

If the user wants oMLX to survive reboot and terminal close:
```
brew services start jundot/omlx/omlx
```
This uses launchd. To stop it: `brew services stop jundot/omlx/omlx`. To disable auto-start: `brew services info jundot/omlx/omlx`.

Otherwise, `omlx-restart` after login is enough.

## Phase 9 — thinking-mode wiring (KNOWN INCOMPLETE upstream)

Server-side, oMLX honors `chat_template_kwargs.enable_thinking` (proven by direct curl tests — sending `false` produces structured answers, `true` produces chain-of-thought traces). Client-side, pi ships `compat.thinkingFormat: "qwen-chat-template"` on the omlx models to translate `pi --thinking off/high` (or `Shift+Tab` in the TUI) into that field. Whether this actually flows end-to-end was not conclusively verified.

To verify:
1. Start oMLX with trace logging temporarily: `pkill -f 'omlx serve' && omlx serve --host 127.0.0.1 --port 8000 --hf-cache --log-level trace > /tmp/omlx_trace.log 2>&1 &`
2. Run two pi calls in a quiet terminal (no other pi sessions active — they'd pollute the log):
   ```
   pi -p --thinking off  "quick test"
   pi -p --thinking high "quick test"
   ```
3. Check whether pi sent different values:
   ```
   grep "Incoming POST /v1/chat" /tmp/omlx_trace.log | tail -2 | grep -oE '"chat_template_kwargs":\{[^}]*\}'
   ```
   Expected: two lines, one with `enable_thinking:false`, one with `enable_thinking:true`. If both are missing or identical, thinking toggling is not effective and pi's source at `/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent/node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js` around lines 570-585 needs inspection (the `thinkingFormat === "qwen-chat-template"` branch).
4. Restart oMLX normally: `omlx-restart` (trace logging is verbose and hurts performance).

## Phase 10 — final summary

Print a summary block:
- Models cached and total size: `du -sh ~/.cache/huggingface/hub/models--mlx-community--*`
- oMLX status: `omlx-status` (running, model count)
- pi default: `python3 -c "import json; d=json.load(open('$HOME/.pi/agent/settings.json')); print(d.get('defaultProvider'), d.get('defaultModel'))"`
- Installed pi extensions: `pi list`
- Measured decode tok/s from step 4
- Entropy test result from step 5
- Whether thinking wiring verification (step 9) passed

## Known limitations (still current)

- **DFlash speculative decoding does not work on Mac for Laguna** as of oMLX 0.5.3 (server returns "DFlash supports only Qwen and Gemma4 models"). Track [omlx#2398](https://github.com/jundot/omlx/issues/2398).
- **Nativ 0.6.8 bundled mlx-vlm** also lacks a `laguna_dflash` drafter.
- **Low Power Mode halves throughput.**
- **Podman / Docker Desktop / OrbStack VMs share GPU** with MLX. Pause if throughput drops.
- **Zscaler DLP blocks Python (.py) file downloads.** Small text/JSON files pass; safetensors are also fine; `.py` returns an HTML block page.

---
