# Rebuild prompt

Paste the block below into a coding agent on the target Apple Silicon Mac when this
repository is available. If the repository is missing, use [CONTINUITY.md](CONTINUITY.md)
instead.

---

Reinstall and verify my pi + oMLX local-model setup from the `pi-local-model-config`
repository. Work through every phase, stop on failed verification, preserve unrelated
existing settings, and never expose credentials.

## Required state

- Runtime: oMLX `0.5.7` or newer, not standalone `mlx-vlm`.
- Managed daemon: Homebrew service `homebrew.mxcl.omlx` on `127.0.0.1:8000`.
- pi provider: `omlx`, OpenAI completions API at `http://127.0.0.1:8000/v1`.
- Default model: `lmstudio-community--Qwen3.8-27B-MLX-8bit`.
- Qwen aliases: `qwen`, `qwen3.8`; thinking disabled; 262,144 context; image input.
- Retain Laguna aliases `laguna-fast`, `laguna` and GLM aliases `glm`, `glm-air`.
- No-argument `omlx-model`, `omlx-start`, `omlx-start-bg`, and `omlx-restart` must select
  Qwen and provider `omlx`.

## 1. Prerequisites

Confirm Apple Silicon, RAM, power mode, free disk, and versions:

```sh
sw_vers
system_profiler SPHardwareDataType | grep -E 'Chip|Memory'
pmset -g | grep -iE 'lowpowermode|powermode'
df -h "$HOME"
pi --version
omlx --version
```

Install pi if absent with the official `https://pi.dev/install.sh`. Install or upgrade
oMLX with:

```sh
brew tap jundot/omlx https://github.com/jundot/omlx
brew update
brew upgrade omlx || brew install omlx
omlx --version
```

Require oMLX `0.5.7` or newer. Homebrew may ask for confirmation; do not mistake an
idle prompt for a completed upgrade.

## 2. Install repository files

From the repository root:

```sh
mkdir -p ~/.omlx/models ~/.pi/agent ~/.local/bin
cp configs/omlx-settings.json ~/.omlx/settings.json
cp configs/omlx-model-settings.json ~/.omlx/models/model_settings.json
cp configs/pi-settings.json ~/.pi/agent/settings.json
cp configs/pi-models.json ~/.pi/agent/models.json
cp configs/pi-APPEND_SYSTEM.md ~/.pi/agent/APPEND_SYSTEM.md
cp scripts/omlx-* ~/.local/bin/
chmod +x ~/.local/bin/omlx-*
```

Ensure `~/.local/bin` is on `PATH`. Validate all JSON with `python3 -m json.tool` and all
scripts with `zsh -n ~/.local/bin/omlx-*`.

## 3. Link the Qwen LM Studio download

Expected source:

```text
~/.lmstudio/models/lmstudio-community/Qwen3.8-27B-MLX-8bit
```

Before linking, require `config.json`, `model.safetensors.index.json`, and all six
referenced `.safetensors` shards. The complete source is about 27.5 GiB.

```sh
python3 tools/link_lmstudio_to_hf.py \
  lmstudio-community/Qwen3.8-27B-MLX-8bit
```

Expected upstream revision at the time this prompt was written:
`241ebb5f1d60b122fd653da658836a55feb9e2b0`. Accept a newer revision only when the HF
manifest and local files match. Verify the snapshot has no broken symlinks and that all
six snapshot shards have the same dereferenced inode as their LM Studio sources. `du`
will show 28 GiB at both paths even though hardlinks do not duplicate physical blocks.

Inspect cached `config.json`; require:

```text
model_type: qwen3_5
architectures: Qwen3_5ForConditionalGeneration
vision_config: present
```

## 4. Start the daemon

```sh
omlx-start-bg
brew services info omlx
omlx-status
```

Require `Running: true`, `Loaded: true`, and Qwen in `/v1/models` under the exact ID
`lmstudio-community--Qwen3.8-27B-MLX-8bit`. oMLX should classify it as a VLM and use its
VLM engine. Keep Laguna and GLM discoverable when their caches exist.

## 5. Verify direct inference

The first request may take several minutes because oMLX loads about 28 GiB and scans an
existing SSD cache. Do not kill it merely because the HTTP response is initially quiet.

```sh
curl -sS --max-time 900 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"lmstudio-community--Qwen3.8-27B-MLX-8bit","messages":[{"role":"user","content":"Reply with exactly QWEN_OK"}],"temperature":0,"max_tokens":64,"stream":false}'
```

Require HTTP 200, the exact model ID, content `QWEN_OK`, and `finish_reason: stop`. If
reasoning prose appears, ensure the Qwen entry in
`~/.omlx/models/model_settings.json` has `"enable_thinking": false` and retry warm.

The `Structured output requires xgrammar` log is informational for plain chat. Do not
install the grammar extra unless structured-output grammar is actually required.

## 6. Verify pi configuration and headless inference

Require these live values:

```text
defaultProvider: omlx
defaultModel: lmstudio-community--Qwen3.8-27B-MLX-8bit
defaultThinkingLevel: off
```

Run `pi --list-models qwen3.8`; it must report provider `omlx`, 262.1K context, 32.8K
maximum output, thinking `no`, images `yes`.

Then run the minimal headless smoke test:

```sh
pi --print --mode text --no-extensions --no-skills --no-context-files \
  --no-tools --no-session --offline \
  --system-prompt 'Answer exactly as requested.' \
  'Reply with exactly: PI_QWEN_OK'
```

Require exact output `PI_QWEN_OK`. Do not add provider/model flags: this test must prove
the defaults work. If an agent sandbox reports `EPERM` for `~/.pi`, rerun with approved
filesystem access; an unreadable settings file can make pi silently fall back to an
Anthropic model and produce a misleading connection error.

## 7. Final checks

```sh
brew services info omlx
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
python3 -m json.tool ~/.pi/agent/settings.json
pi --list-models qwen3.8
```

Report runtime version, daemon PID/state, Qwen API ID, hardlink verification, direct
response, headless pi response, and commands for switching to `laguna-fast`, `laguna`,
or `glm`. Leave the managed service running and Qwen selected.

---