# pi + Laguna-S 2.1 + MLX on Apple Silicon (M5 Max 128GB)

Full working config that runs the [pi coding agent](https://pi.dev) against a local
`mlx-community/Laguna-S-2.1-oQ4e-fast` model served by [oMLX](https://github.com/jundot/omlx)
with tuned sampling, prefix caching, and native thinking-mode toggling.

Hardware/OS target: **Apple Silicon Mac (M5 Max 40-core, 128 GB), macOS 26+.**
Should work on any M-series with enough RAM (~65 GB peak for Laguna oQ4e-fast).

## What's inside

```
configs/
  omlx-settings.json         → ~/.omlx/settings.json          — oMLX server tuning
  omlx-model-settings.json   → ~/.omlx/models/model_settings.json — per-model enable_thinking
  pi-settings.json           → ~/.pi/agent/settings.json      — pi provider/model defaults
  pi-models.json             → ~/.pi/agent/models.json        — omlx + fallback provider defs
  pi-APPEND_SYSTEM.md        → ~/.pi/agent/APPEND_SYSTEM.md   — credential handling, gh multi-host, subagents, context size
scripts/
  omlx-start                 foreground server
  omlx-start-bg              background/managed server
  omlx-stop                  shut down
  omlx-status                health check
  omlx-restart               robust kill-then-relaunch (handles stuck ports)
tools/
  link_lmstudio_to_hf.py     hardlink LM Studio MLX models into HF cache format
  pi_proxy2.py               request-body capture proxy for diagnostics
  bench_omlx.py              decode/prefill/TTFT benchmark
  bench_proxy.py             heavier request-timing proxy
docs/
  SETUP.md                   full reinstall instructions
  PROMPT.md                  ready-to-paste Claude prompt that rebuilds this end-to-end
```

## Quick start (already set up once)

```
omlx-start-bg          # start server (or omlx-restart if stuck)
pi -p "hello"          # test via pi
Shift+Tab              # toggle thinking level inside pi TUI
```

## Full reinstall on a new Mac

Open `docs/PROMPT.md` and paste the entire contents into a Claude session with tool access.
It runs 9 verification-gated phases, installs everything, downloads/links models,
tunes settings, and verifies end-to-end.

## Baseline performance (M5 Max 128GB, High Power mode)

| Test | Result |
|---|---|
| Decode (small ctx) | ~62-66 tok/s |
| Decode (1k ctx) | ~59-60 tok/s |
| TTFT (small prompt) | ~360 ms |
| TTFT (1k prompt) | ~640 ms |
| Peak RAM (Laguna oQ4e-fast @ 1k) | ~60 GB |

Matches the published omlx.ai benchmark within noise.
**Low Power Mode roughly halves throughput** — keep it off.

## What's tuned

- **Sampling** (author's shipped defaults): temp=1.0, top_p=1.0, top_k=20, min_p=0.0
- **Context window**: 131,072 (128k) — good headroom, ~2min max cold prefill worst case
- **Max output tokens per response**: 32,768
- **Prefix caching**: 8 GB hot cache, 8192 initial blocks (128k tokens of prefix cache)
- **Burst decode**: aggressive
- **Chunked prefill**: on
- **KV cache quantization** (TurboQuant): off — you have RAM for full quality
- **pi HTTP idle timeout**: disabled (no more disconnect on long prefills)
- **pi thinking-format**: `qwen-chat-template` — pi's `--thinking off/high` translates to
  `chat_template_kwargs.enable_thinking` server-side (whether the client-side wiring reaches
  the server is not conclusively verified — see PROMPT.md Phase 8)

## What's protected

`~/.pi/agent/APPEND_SYSTEM.md` covers four persistent policies:

1. **`credential_handling`** — no extracting/printing/hardcoding tokens, no `git credential fill`
   or keychain sweeps, no `gh auth login --token-stdin` from stdout of a previous command.
2. **`gh_multi_host`** — for machines dual-authenticated to a corporate GHE instance
   AND public `github.com`. Every `gh` call must pass explicit `--hostname`. Never touch
   `GH_HOST`. Never `gh auth login/switch/refresh` without explicit user instruction.
   The shipped APPEND_SYSTEM.md uses `<enterprise-ghe-host>` as a placeholder — replace
   with your corp host or delete the block if you don't have one.
3. **`subagents`** — when the `pi-subagents` extension is active, prefer parallel independent
   work and isolated risky operations via subagents. Don't fabricate the tool if it's not registered.
4. **`context_size`** — keep prompts small; suggest `/compact` at ~100k tokens.

## Installed pi extensions

- `pi-subagents` — Claude Code-style parallel subagents (2790★, MIT)
- `@narumitw/pi-retry` — stall-watchdog retry for local models
- `pi-smart-web-search` — improved web search
- `pi-smart-fetch` — improved fetch

## Known limitations

- **DFlash speculative decoding does not work on Mac for Laguna** as of oMLX 0.5.3
  (server errors "DFlash supports only Qwen and Gemma4 models"). Draft model is cached but not usable.
  Track [omlx#2398](https://github.com/jundot/omlx/issues/2398).
- **Nativ 0.6.8 bundled mlx-vlm** also lacks a `laguna_dflash` drafter.
- **Podman / Docker Desktop VMs share GPU** with MLX — pause them if throughput drops.

## Do NOT install

- `pi-lean-ctx` — needs external `lean-ctx` binary; installer wraps Claude Code / adds shell
  allowlist / injects MCP into VS Code / modifies zshrc. Uninstall aggressively.
- Any of the `pi-omlx-*` provider adapters — pi's generic `openai-completions` provider already
  works and adding these tramples the custom sampling / thinking-format config.
