# Agent usage prompt

Paste the block below into another coding agent running on this Mac. It explains how to
use the already-configured local Qwen model and where to learn more.

---

You have access to a local Qwen model served on this Mac. Prefer MTPLX for Qwen 3.8
because it uses native multi-token prediction by default and exposes a local
OpenAI-compatible API.

## Preferred service details

- Runtime: MTPLX `2.9.0` or newer.
- API base URL: `http://127.0.0.1:8000/v1`.
- API style: OpenAI-compatible chat completions.
- Served model ID for clients: `mtplx`.
- Backing model: `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed`.
- Cache path: `~/.mtplx/models/Youssofal--Qwen3.8-27B-MTPLX-Optimized-Speed`.
- pi provider: `mtplx`.
- pi default model: `mtplx`.
- Native MTP is on by default; use `--no-mtp` only for target-only AR comparison.

## Check and start MTPLX

First check whether something is already listening:

```sh
curl -sS --max-time 5 http://127.0.0.1:8000/v1/models \
  | python3 -m json.tool
```

If it is down, start MTPLX for pi:

```sh
mtplx-start-bg
```

If the model is not cached yet, add `--download`.

`mtplx-start-bg` runs `mtplx serve --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed
--model-id mtplx --host 127.0.0.1 --port 8000 --no-auth --mtp` on the Mac host.

Do not run oMLX on port 8000 at the same time. Stop whichever server owns the port before
starting the other.

## Preferred use through pi

MTPLX and model `mtplx` are the configured defaults, so no model flags are needed:

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
pi --list-models mtplx
```

It should show provider `mtplx` and model `mtplx`.

## Direct API use

Use the API when you need model inference rather than a full coding-agent session:

```sh
curl -sS --max-time 900 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "mtplx",
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
API key:  mtplx
model:    mtplx
```

The service is loopback-only. Do not expose port 8000 to the LAN.

## oMLX fallback

Use oMLX only when you need the older LM Studio/Hugging Face cache workflow, image-capable
`lmstudio-community--Qwen3.8-27B-MLX-8bit`, Laguna, GLM, or another fallback model from
the repository's existing oMLX scripts.

```sh
omlx-start-bg --model qwen
omlx-status
omlx-model qwen
omlx-model laguna-fast
omlx-model laguna
omlx-model glm
```

oMLX and MTPLX both default to port 8000 in this setup. Do not leave both running on that
port. oMLX logs are at `~/.omlx/logs/server.log` and `$(brew --prefix)/var/log/omlx.log`.

## Corporate TLS interception

If Hugging Face downloads fail behind Zscaler or another MITM proxy, use the shared CA
bundle at `~/.config/nativ/cacert.pem`. The verified fix for MTPLX was certifi plus the
strict-compatible Zscaler CA certificates from the intercepted Hugging Face chain. Also keep
`~/.ssl/ca-bundle.pem` symlinked to that bundle because older shell config may export that
path as `SSL_CERT_FILE`.

Verify MTPLX's Python can reach Hugging Face:

```sh
SSL_CERT_FILE="$HOME/.config/nativ/cacert.pem" \
REQUESTS_CA_BUNDLE="$HOME/.config/nativ/cacert.pem" \
"$HOME/Library/Application Support/MTPLX/runtime-venv/bin/python" - <<'PY'
from urllib.request import urlopen
with urlopen('https://huggingface.co/api/models/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed', timeout=20) as response:
    print(response.status)
PY
```

The validation must print `200`.

## Operational cautions

- A cold model load can be quiet for a while. Inspect MTPLX status/log output before
  aborting it.
- Do not install `@narumitw/pi-retry`; its 90-second watchdog aborts valid silent local
  loads and long prefills.
- If a sandbox cannot read or lock `~/.pi`, pi may ignore local settings and fall back to
  another provider. Grant access to `~/.pi` and loopback, then retry.
- Direct `mlx-vlm.generate` is useful for experiments but is not the preferred daemon.

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
README.md                    Overview, preferred runtime, service usage, known fixes
docs/SETUP.md                Installation and verification procedure
docs/PROMPT.md               Rebuild workflow when the repository is available
docs/CONTINUITY.md           Full reconstruction if the repository is lost
configs/pi-settings.json     pi defaults and packages
configs/pi-models.json       Provider and model definitions
configs/omlx-settings.json   oMLX fallback server, memory, cache, and sampling settings
scripts/omlx-model           oMLX fallback alias/default selection logic
```

Prefer MTPLX and the documented configuration over ad hoc service commands. Preserve oMLX
fallback support when changing Qwen defaults.

---
