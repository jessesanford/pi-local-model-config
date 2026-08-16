# Agent usage prompt

Paste the block below into another coding agent running on this Mac. It explains how to
use the already-configured local Qwen model and where to learn more.

---

You have access to a local Qwen vision-language model served on this Mac. Use it when a
local model is appropriate for coding, analysis, drafting, or image-aware prompts.

## Service details

- Runtime: oMLX `0.5.7` or newer, managed by Homebrew/launchd.
- API base URL: `http://127.0.0.1:8000/v1`.
- API style: OpenAI-compatible chat completions.
- Model ID: `lmstudio-community--Qwen3.8-27B-MLX-8bit`.
- pi provider: `omlx`.
- pi model alias: `qwen` or `qwen3.8`.
- Optional bf16 alias: `qwen-bf16` or `qwen16` (linked, not inference-tested).
- Context window: 262,144 tokens.
- Inputs: text and images.
- Thinking is disabled by default.

## Check and start the service

First check it without restarting a healthy daemon:

```sh
omlx-status
curl -sS --max-time 5 http://127.0.0.1:8000/v1/models \
  | python3 -m json.tool
```

If it is down, start the persistent managed service:

```sh
omlx-start-bg
omlx-status
```

Use `omlx-restart` only for a stuck daemon or changed oMLX configuration. Use
`omlx-stop` to stop it. Service logs are at `~/.omlx/logs/server.log` and
`$(brew --prefix)/var/log/omlx.log`.

## Preferred use through pi

Qwen and provider `omlx` are the configured defaults, so no model flags are needed:

```sh
pi
pi -p "Explain the architecture of this project"
pi @README.md -p "Review this document for technical errors"
```

For automation or a minimal diagnostic request:

```sh
pi --print --mode text --no-extensions --no-skills --no-context-files \
  --no-tools --no-session --offline \
  --system-prompt 'Answer the request directly.' \
  'Reply with exactly LOCAL_QWEN_OK'
```

Confirm pi's registration when needed:

```sh
pi --list-models qwen3.8
```

It should show provider `omlx`, context `262.1K`, maximum output `32.8K`, thinking
`no`, and images `yes`.

## Direct API use

Use the API when you need model inference rather than a full coding-agent session:

```sh
curl -sS --max-time 900 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "lmstudio-community--Qwen3.8-27B-MLX-8bit",
    "messages": [
      {"role": "user", "content": "Explain what a content-addressed cache is."}
    ],
    "temperature": 0.2,
    "max_tokens": 1024,
    "stream": false
  }'
```

OpenAI-compatible clients should use:

```text
base URL: http://127.0.0.1:8000/v1
API key:  omlx
model:    lmstudio-community--Qwen3.8-27B-MLX-8bit
```

The service is loopback-only. Do not expose port 8000 to the LAN.

## Model switching

The oMLX daemon is multi-model. Changing pi's default does not require restarting it:

```sh
omlx-model qwen
omlx-model qwen-bf16
omlx-model laguna-fast
omlx-model laguna
omlx-model glm
```

Return to Qwen with `omlx-model qwen` or simply `omlx-model`.

`qwen-bf16` selects `mlx-community--Qwen3.8-27B-bf16`, a roughly 51 GiB model. It
has not been loaded or tested. Selection alone does not load weights; the first request does.

## Operational cautions

- A cold model load can be quiet for a while. Inspect the oMLX log before aborting it.
- Do not install `@narumitw/pi-retry`; its 90-second watchdog aborts valid silent local
  loads and long prefills.
- Current SSD cache data belongs in `~/.omlx/cache-0.5.7`. Do not delete the older
  `~/.omlx/cache` automatically.
- If a sandbox cannot read or lock `~/.pi`, pi may ignore local settings and fall back to
  another provider. Grant access to `~/.pi` and loopback, then retry.
- Do not run a second inference server on port 8000 while oMLX is active.

## Project documentation

Canonical GitHub repository:

```text
https://github.com/jessesanford/pi-local-model-config
```

The current local checkout may still have its pre-rename directory name:

```text
/Users/jesse.sanford/workspaces/pi-laguna-S-2.1-oQ4e-fast-config
```

Read these files before modifying the setup:

```text
README.md                    Overview, model aliases, service usage, known fixes
docs/SETUP.md                Installation and verification procedure
docs/PROMPT.md               Rebuild workflow when the repository is available
docs/CONTINUITY.md           Full reconstruction if the repository is lost
configs/pi-settings.json     pi defaults and packages
configs/pi-models.json       Provider and model definitions
configs/omlx-settings.json   oMLX server, memory, cache, and sampling settings
scripts/omlx-model           Shared model alias/default selection logic
```

Prefer the repository's scripts and documented configuration over ad hoc service commands.
Preserve Laguna and GLM support when changing Qwen defaults or oMLX behavior.

---