# Repository-loss continuity prompt

This prompt is intentionally self-contained. Save it somewhere outside the repository. Paste
the block below into a capable coding agent when the repository and local configuration have
both been lost.

---

Recreate from scratch a repository named `pi-local-model-config`, then install and verify a
pi coding-agent setup backed by local MLX models on Apple Silicon. Assume no repository files
survive. Do not search for an old clone as a substitute for reconstruction.

Work autonomously through creation, installation, and executable verification. Preserve any
unrelated user configuration you encounter. Never expose credentials. Do not delete model
weights or caches. Stop only for a real blocker or a destructive operation requiring consent.

## Canonical architecture

- Client: pi coding agent.
- Server and macOS daemon: oMLX, not standalone `mlx-vlm`.
- Minimum verified oMLX: `0.5.7`.
- API: OpenAI completions at `http://127.0.0.1:8000/v1`.
- Service: Homebrew/launchd label `homebrew.mxcl.omlx`.
- Server mode: multi-model, Hugging Face cache discovery, localhost only.
- Default model: `lmstudio-community--Qwen3.8-27B-MLX-8bit`.
- Qwen source repo: `lmstudio-community/Qwen3.8-27B-MLX-8bit`.
- Qwen is a `qwen3_5` VLM using `Qwen3_5ForConditionalGeneration`, about 28 GiB,
  262,144-token context, image input, thinking disabled.
- Keep optional Laguna and GLM choices.

Canonical aliases and oMLX API IDs:

```text
qwen, qwen3.8 -> lmstudio-community--Qwen3.8-27B-MLX-8bit
qwen-bf16, qwen16 -> mlx-community--Qwen3.8-27B-bf16
laguna-fast   -> mlx-community--Laguna-S-2.1-oQ4e-fast
laguna        -> mlx-community--Laguna-S-2.1-oQ4e
glm, glm-air  -> mlx-community--GLM-4.5-Air-8bit
```

## Repository to create

Create this structure under `~/workspaces/pi-local-model-config`:

```text
README.md
configs/omlx-settings.json
configs/omlx-model-settings.json
configs/pi-settings.json
configs/pi-models.json
configs/pi-APPEND_SYSTEM.md
docs/SETUP.md
docs/PROMPT.md
docs/CONTINUITY.md
scripts/omlx-model
scripts/omlx-start
scripts/omlx-start-bg
scripts/omlx-restart
scripts/omlx-stop
scripts/omlx-status
tools/link_lmstudio_to_hf.py
tools/bench_omlx.py
```

Initialize git, but do not commit or create a GitHub repository unless explicitly asked.
Use ASCII, executable zsh scripts, Python standard library only, and valid formatted JSON.

## Canonical pi configuration

Create `configs/pi-settings.json` with these required values; package/version UI fields may be
added when appropriate:

```json
{
  "packages": [
    "npm:pi-smart-web-search",
    "npm:pi-smart-fetch",
    "npm:pi-subagents"
  ],
  "defaultProvider": "omlx",
  "defaultModel": "lmstudio-community--Qwen3.8-27B-MLX-8bit",
  "httpIdleTimeoutMs": 0,
  "defaultThinkingLevel": "off"
}
```

Create `configs/pi-models.json`. It may contain other providers, but `providers.omlx` must be:

```json
{
  "api": "openai-completions",
  "apiKey": "omlx",
  "baseUrl": "http://127.0.0.1:8000/v1",
  "compat": {
    "supportsDeveloperRole": false,
    "supportsReasoningEffort": false
  },
  "models": [
    {
      "id": "lmstudio-community--Qwen3.8-27B-MLX-8bit",
      "name": "qwen3.8-27b",
      "contextWindow": 262144,
      "input": ["text", "image"],
      "maxTokens": 32768
    },
    {
      "id": "mlx-community--Qwen3.8-27B-bf16",
      "name": "qwen3.8-27b-bf16",
      "contextWindow": 262144,
      "input": ["text", "image"],
      "maxTokens": 32768
    },
    {
      "id": "mlx-community--Laguna-S-2.1-oQ4e-fast",
      "name": "laguna-fast",
      "contextWindow": 131072,
      "reasoning": true,
      "compat": {"thinkingFormat": "qwen-chat-template"},
      "maxTokens": 32768
    },
    {
      "id": "mlx-community--Laguna-S-2.1-oQ4e",
      "name": "laguna",
      "contextWindow": 131072,
      "reasoning": true,
      "compat": {"thinkingFormat": "qwen-chat-template"},
      "maxTokens": 32768
    },
    {
      "id": "mlx-community--GLM-4.5-Air-8bit",
      "name": "glm-air",
      "contextWindow": 131072,
      "maxTokens": 32768
    }
  ]
}
```

Do not accidentally put Qwen under a legacy `local` provider. Verify with
`pi --list-models qwen3.8`; the provider column must say `omlx`.

Create `configs/omlx-model-settings.json`:

```json
{
  "lmstudio-community--Qwen3.8-27B-MLX-8bit": {"enable_thinking": false},
  "mlx-community--Qwen3.8-27B-bf16": {"enable_thinking": false},
  "mlx-community--Laguna-S-2.1-oQ4e-fast": {"enable_thinking": true},
  "mlx-community--Laguna-S-2.1-oQ4e": {"enable_thinking": true},
  "mlx-community--GLM-4.5-Air-8bit": {"enable_thinking": false},
  "lmstudio-community--GLM-4.5-Air-MLX-6bit": {"enable_thinking": false},
  "GLM-4.5-Air-6bit": {"enable_thinking": false}
}
```

Create `configs/omlx-settings.json` with localhost port 8000, HF-cache discovery, balanced
memory guard, chunked prefill, aggressive burst decode, 8 GiB hot cache, SSD cache enabled,
262,144 maximum context, 32,768 maximum output, temperature 1.0, top-p 1.0, top-k 20, and
repetition penalty 1.0. Set `cache.ssd_cache_dir` to `~/.omlx/cache-0.5.7`. Never embed a
real secret; use a placeholder that oMLX replaces.
Avoid machine-specific network aliases and absolute usernames.

Create `configs/pi-APPEND_SYSTEM.md` with concise policies for credential safety, explicit
GitHub host selection on multi-host machines, optional subagent use only when registered, and
context conservation for local models. No company hostname or credential may be hardcoded.

## Canonical script behavior

Put shared behavior in `scripts/omlx-model`; all lifecycle scripts must source it by their own
absolute script directory (`${0:A:h}` in zsh). Define `OMLX_DEFAULT_MODEL="qwen"` once.

`omlx-model` requirements:

- Resolve the canonical aliases above; pass unknown strings through unchanged.
- With no argument, select Qwen. Accept at most one argument.
- Update both `defaultProvider` to `omlx` and `defaultModel` in
  `~/.pi/agent/settings.json` using Python JSON APIs.
- Pass settings path/model through environment variables, never interpolate user input into
  Python source.
- Preserve all other pi settings and write a trailing newline.
- Fail clearly when the pi settings file is absent.

`omlx-start`, `omlx-start-bg`, and `omlx-restart` requirements:

- No arguments means Qwen, not "leave whatever was selected before".
- Accept `-m VALUE` and `--model VALUE`, reject a missing value, and pass other arguments to
  oMLX.
- Always invoke the shared selector before starting.
- If `~/.config/nativ/cacert.pem` exists, export it as `SSL_CERT_FILE`,
  `REQUESTS_CA_BUNDLE`, and `CURL_CA_BUNDLE`.
- Export `HF_HUB_DISABLE_XET=1` and `HF_HUB_ENABLE_HF_TRANSFER=0`.
- Foreground command: `/opt/homebrew/opt/omlx/bin/omlx serve --host 127.0.0.1 --port 8000
  --hf-cache --memory-guard balanced --log-level info` plus passthrough arguments.
- Managed background command: `/opt/homebrew/opt/omlx/bin/omlx start` plus passthrough.
- Restart must stop managed and direct processes, free port 8000, launch `omlx serve` with
  `nohup`, log to `/tmp/omlx.log`, and wait up to two minutes for `/v1/models`.

`omlx-stop` must stop Homebrew/oMLX managed service and residual `omlx serve` or
`omlx-server` processes without failing when already stopped. `omlx-status` must query
`/v1/models`, report UP/DOWN, and print useful model information.

Important historical fix: older scripts mapped `glm` to `GLM-4.5-Air-6bit` while docs claimed
8-bit. The canonical `glm` alias is now `mlx-community--GLM-4.5-Air-8bit`.

## LM Studio to Hugging Face linker

Implement `tools/link_lmstudio_to_hf.py` with `argparse` and standard library only:

- Default LM Studio root: `~/.lmstudio/models` (never a hardcoded username).
- Default HF cache: `~/.cache/huggingface/hub`.
- Positional model IDs select one or more `org/repo` directories; no IDs scans all complete
  models.
- A candidate requires `config.json` and at least one `.safetensors` file.
- Query `https://huggingface.co/api/models/{repo}/tree/main?recursive=true` and
  `https://huggingface.co/api/models/{repo}` for manifest, etags, and revision.
- Verify every local file size. Fetch only missing non-LFS small files. Never silently download
  a missing weight shard.
- Build standard HF `blobs`, `refs/main`, and `snapshots/<revision>` layout.
- Hardlink source files into blobs and create relative snapshot symlinks.
- Be idempotent and report missing requested models as an argparse error.

Canonical Qwen source path:

```text
~/.lmstudio/models/lmstudio-community/Qwen3.8-27B-MLX-8bit
```

The verified download had six of six indexed shards and 27.51 GiB. The verified revision was
`241ebb5f1d60b122fd653da658836a55feb9e2b0`, with 18 snapshot symlinks and no broken links.
A newer upstream revision is acceptable when manifest validation succeeds.

Optional bf16 source: `~/.lmstudio/models/mlx-community/Qwen3.8-27B-bf16`. The verified
download had 11 shards, 50.98 GiB, revision
`6f265714824f3c38d4452baa1628aef3d9b9aae9`, 24 snapshot links, and 11/11 shared shard
inodes. Register it as `qwen-bf16`/`qwen16`, but keep 8-bit Qwen as the default and do not
load or inference-test bf16 without explicit instruction.

On macOS, compare source inode with `stat -f %i` and dereferenced snapshot inode with
`stat -Lf %i`. A non-dereferenced check compares the symlink inode and falsely reports that
hardlinks are absent. `du` counts hardlinks per argument and can also misleadingly display
28 GiB for both trees; shared inode identity is the decisive check.

## Benchmark tool

Implement `tools/bench_omlx.py` with these aliases and Qwen as argparse default. It must accept
arbitrary model IDs through `--model/-m`, benchmark direct oMLX chat completions and streaming
TTFT, and skip Nativ unless an explicit `--nativ-model` is supplied. Do not retain a hidden
Laguna default.

## Installation and model linking

Install pi if absent using its official installer. Install oMLX with Homebrew:

```sh
brew tap jundot/omlx https://github.com/jundot/omlx
brew update
brew upgrade omlx || brew install omlx
```

Require `omlx --version` to report `0.5.7` or newer. Homebrew can prompt during an upgrade;
answer deliberately and wait for completion. A transient "Failed to fix install linkage" must
be followed by checking `/opt/homebrew/opt/omlx`, `/opt/homebrew/bin/omlx --version`, and
`brew list --versions omlx`; do not assume failure if the final upgrade and symlinks succeeded.

Install repository configs/scripts to `~/.omlx`, `~/.pi/agent`, and `~/.local/bin`. Copy, do not
symlink, unless the user requests otherwise. Ensure scripts are executable and PATH is set.

Do not install `@narumitw/pi-retry`. If it is present, run
`pi remove npm:@narumitw/pi-retry`. Its 90-second stall watchdog aborts healthy local
requests during silent cold loads and long prefills; pi's HTTP idle timeout is already disabled.

After LM Studio finishes Qwen, run the targeted linker. Verify all indexed shards before and
all snapshot links/shared inodes after.

## Start and acceptance tests

Start persistent serving with `omlx-start-bg` without a model argument. Require:

```text
brew services info omlx -> Running: true, Loaded: true
GET /v1/models -> lmstudio-community--Qwen3.8-27B-MLX-8bit present
pi settings -> defaultProvider=omlx and exact Qwen defaultModel
pi --list-models qwen3.8 -> provider omlx, context 262.1K, max-out 32.8K,
                           thinking no, images yes
```

The first Qwen request can take several minutes: loading is about 28 GiB, and an existing SSD
cache scan once took roughly seven minutes. Watch oMLX logs rather than killing a quiet curl.
The successful load should identify a VLM engine and approximately 27.9 GiB actual weights.

Use `~/.omlx/cache-0.5.7` for current cache data. A verified incident involved 5,047
incompatible blocks totaling 417.03 GB under `~/.omlx/cache`; scanning them took 6 minutes
27 seconds and triggered the removed retry extension. Do not delete that legacy directory
automatically. Isolating the new cache fixed the cold headless request, which then completed
in 10 seconds.

Direct smoke test:

```sh
curl -sS --max-time 900 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"lmstudio-community--Qwen3.8-27B-MLX-8bit","messages":[{"role":"user","content":"Reply with exactly QWEN_OK"}],"temperature":0,"max_tokens":64,"stream":false}'
```

Require HTTP 200, exact model ID, `QWEN_OK`, and stop completion. If 16 tokens yields partial
reasoning prose, that is not a serving failure: confirm `enable_thinking=false` and retry with
64 tokens. The warm verified result was exact `QWEN_OK`.

Headless pi smoke test, with no provider/model override:

```sh
pi --print --mode text --no-extensions --no-skills --no-context-files \
  --no-tools --no-session --offline \
  --system-prompt 'Answer exactly as requested.' \
  'Reply with exactly: PI_QWEN_OK'
```

Require exact `PI_QWEN_OK`. If run from a sandbox, `EPERM` reading or locking `~/.pi` can cause
pi to ignore settings, fall back to Anthropic, and report a misleading connection error. Rerun
with approved access to `~/.pi` and loopback. Confirm the emitted provider/model or server log
when diagnosing.

The oMLX log line `Structured output requires xgrammar` does not block ordinary chat. Install
the grammar extra only for grammar-constrained output.

Leave the Homebrew-managed daemon running and Qwen selected. Finally write README, SETUP, the
normal rebuild prompt, and this continuity prompt with the resulting exact commands and any
newly verified version/revision differences. Run JSON validation, Python compilation, zsh
syntax checks, `git diff --check`, direct inference, and headless pi inference before declaring
success.

---
