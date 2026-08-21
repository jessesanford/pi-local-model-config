# Rebuild prompt

Paste the block below into a coding agent on the target Apple Silicon Mac when this
repository is available. If the repository is missing, use [CONTINUITY.md](CONTINUITY.md)
instead.

---

Reinstall and verify my pi + MTPLX local-model setup from the `pi-local-model-config`
repository. Work through every phase, stop on failed verification, preserve unrelated
existing settings, and never expose credentials.

## Required state

- Preferred runtime: MTPLX `2.9.0` or newer, not oMLX or direct `mlx-vlm`.
- Preferred server: MTPLX OpenAI-compatible API on `127.0.0.1:8000`.
- pi provider: `mtplx`, OpenAI completions API at `http://127.0.0.1:8000/v1`.
- Default model: `mtplx`.
- Backing Qwen model: `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed`.
- Native MTP must be enabled; MTPLX uses `--mtp` by default.
- oMLX `0.5.7` or newer remains an optional fallback, not the default runtime.
- oMLX fallback Qwen: `lmstudio-community--Qwen3.8-27B-MLX-8bit`, thinking disabled,
  262,144 context, image input.
- Optional bf16: `mlx-community--Qwen3.8-27B-bf16`, aliases `qwen-bf16` and `qwen16`,
  about 51 GiB, linked but not inference-tested, never the default.
- Retain Laguna aliases `laguna-fast`, `laguna` and GLM aliases `glm`, `glm-air`.
- MTPLX cache directory: `~/.mtplx/models`.
- oMLX fallback SSD cache directory: `~/.omlx/cache-0.5.7`, isolated from incompatible
  legacy caches.
- Do not install `@narumitw/pi-retry`; its 90-second watchdog aborts valid cold loads.
- oMLX scripts are fallback utilities only; do not let them overwrite the preferred
  MTPLX pi defaults unless explicitly switching to the fallback runtime.

## 1. Prerequisites

Confirm Apple Silicon, RAM, power mode, free disk, and versions:

```sh
sw_vers
system_profiler SPHardwareDataType | grep -E 'Chip|Memory'
pmset -g | grep -iE 'lowpowermode|powermode'
df -h "$HOME"
pi --version
mtplx --version
omlx --version
```

Install pi if absent with the official `https://pi.dev/install.sh`. Install or upgrade
MTPLX first:

```sh
brew install youssofal/mtplx/mtplx
mtplx --version
```

The Mac app is also valid: download the DMG from `https://mtplx.com/download`, drag it
to Applications, then launch MTPLX. The app installs `~/.mtplx/bin/mtplx` and its own
runtime under `~/Library/Application Support/MTPLX`. The preferred model is
`Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed`, cached at
`~/.mtplx/models/Youssofal--Qwen3.8-27B-MTPLX-Optimized-Speed`.

Install or upgrade oMLX only for fallback serving:

```sh
brew tap jundot/omlx https://github.com/jundot/omlx
brew update
brew upgrade omlx || brew install omlx
omlx --version
```

Require MTPLX `2.9.0` or newer. Require oMLX `0.5.7` or newer only if the fallback path
will be used. Homebrew may ask for confirmation; do not mistake an idle prompt for a
completed upgrade.

## 2. Corporate TLS / Zscaler setup for oMLX and MTPLX

If Hugging Face downloads fail with `CERTIFICATE_VERIFY_FAILED` behind a MITM proxy,
build a Python/OpenSSL-compatible bundle before model downloads. Do not blindly append
every macOS Keychain certificate: MTPLX's Python 3.14/OpenSSL 3.5 uses strict X.509
verification and rejected a broad Keychain export with `Basic Constraints of CA cert not
marked critical`.

Create `~/.config/nativ/cacert.pem` from certifi plus the strict-compatible Zscaler CA
certificates observed in the intercepted Hugging Face chain:

```sh
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/hf-zscaler-ca.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT

openssl s_client -connect huggingface.co:443 -servername huggingface.co \
  -showcerts </dev/null > "$tmpdir/chain.txt" 2>/dev/null

awk '/-----BEGIN CERTIFICATE-----/{n++; in_cert=1} in_cert{print > sprintf("'"$tmpdir"'/chain-%04d.pem", n)} /-----END CERTIFICATE-----/{in_cert=0}' \
  "$tmpdir/chain.txt"

mkdir -p ~/.config/nativ ~/.ssl
cat "$(python3 -c 'import certifi; print(certifi.where())')" > ~/.config/nativ/cacert.pem
for cert in "$tmpdir"/chain-*.pem; do
  text=$(openssl x509 -in "$cert" -noout -text 2>/dev/null) || continue
  subject=$(openssl x509 -in "$cert" -noout -subject 2>/dev/null)
  if [[ "$text" == *"X509v3 Basic Constraints: critical"* && \
        "$text" == *"CA:TRUE"* && \
        "$subject" == *"Zscaler"* ]]; then
    cat "$cert" >> ~/.config/nativ/cacert.pem
  fi
done
```

Export it for shells, launchd GUI apps, Python requests, curl, Node, gRPC, AWS SDKs, and
Hugging Face. Keep the legacy `~/.ssl/ca-bundle.pem` path as a symlink because an older
shell config on this Mac exported `SSL_CERT_FILE` there and caused MTPLX GUI retries to
keep failing even after launchd was fixed:

```sh
ln -sfn "$HOME/.config/nativ/cacert.pem" "$HOME/.ssl/ca-bundle.pem"

launchctl setenv SSL_CERT_FILE "$HOME/.config/nativ/cacert.pem"
launchctl setenv REQUESTS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv CURL_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv NODE_EXTRA_CA_CERTS "$HOME/.config/nativ/cacert.pem"
launchctl setenv GRPC_DEFAULT_SSL_ROOTS_FILE_PATH "$HOME/.config/nativ/cacert.pem"
launchctl setenv AWS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv HF_HUB_DISABLE_XET 1
launchctl setenv HF_HUB_ENABLE_HF_TRANSFER 0
```

Persist those GUI variables across logins with a LaunchAgent that runs a small helper such
as `~/.local/bin/mtplx-ca-env`. The helper should refresh or verify
`~/.config/nativ/cacert.pem`, then run the same `launchctl setenv` commands above. Install
the plist under `~/Library/LaunchAgents/com.jesse.mtplx-ca-env.plist` with `RunAtLoad=true`,
then load it with `launchctl bootstrap gui/$(id -u) ...` and verify with
`launchctl getenv SSL_CERT_FILE`.

If `~/.zshrc` or another shell file exports `SSL_CERT_FILE="$HOME/.ssl/ca-bundle.pem"`,
either update it to `~/.config/nativ/cacert.pem` or keep the symlink above. Patch
`~/.mtplx/bin/mtplx` to export the same variables before it execs MTPLX's runtime.

Validate with MTPLX's bundled Python, then restart MTPLX so the GUI inherits the new
environment:

```sh
SSL_CERT_FILE="$HOME/.config/nativ/cacert.pem" \
REQUESTS_CA_BUNDLE="$HOME/.config/nativ/cacert.pem" \
"$HOME/Library/Application Support/MTPLX/runtime-venv/bin/python" - <<'PY'
from urllib.request import urlopen
with urlopen('https://huggingface.co/api/models/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed', timeout=20) as response:
    print(response.status)
PY

osascript -e 'tell application "MTPLX" to quit' 2>/dev/null || true
open -a MTPLX
```

The validation must print `200`. If the GUI still reports `Basic Constraints of CA cert
not marked critical`, inspect the live process with `ps eww -p $(pgrep -f MTPLXApp)` and
fix whichever `SSL_CERT_FILE` path it actually inherited.

## 3. Install repository files

From the repository root:

```sh
mkdir -p ~/.omlx/models ~/.pi/agent ~/.local/bin
cp configs/omlx-settings.json ~/.omlx/settings.json
cp configs/omlx-model-settings.json ~/.omlx/models/model_settings.json
cp configs/pi-settings.json ~/.pi/agent/settings.json
cp configs/pi-models.json ~/.pi/agent/models.json
cp configs/pi-APPEND_SYSTEM.md ~/.pi/agent/APPEND_SYSTEM.md
cp scripts/mtplx-* scripts/omlx-* ~/.local/bin/
chmod +x ~/.local/bin/mtplx-* ~/.local/bin/omlx-*
```

Ensure `~/.local/bin` is on `PATH`. Validate all JSON with `python3 -m json.tool` and all
scripts with `zsh -n ~/.local/bin/mtplx-* ~/.local/bin/omlx-*`.

## 4. Download the preferred MTPLX Qwen model

Download or verify the preferred MTPLX model:

```sh
mtplx-start-bg --download
```

Expected cache path:

```text
~/.mtplx/models/Youssofal--Qwen3.8-27B-MTPLX-Optimized-Speed
```

If MTPLX reports a TLS verification error behind Zscaler, complete the Corporate TLS
section above and retry. Do not switch to oMLX to work around a TLS issue; fix the shared
bundle so MTPLX, Python, curl, and oMLX can all use it.

## 5. Optional: link the oMLX fallback Qwen LM Studio download

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

When present, also link `~/.lmstudio/models/mlx-community/Qwen3.8-27B-bf16` with
`tools/link_lmstudio_to_hf.py mlx-community/Qwen3.8-27B-bf16`. A verified download had
11 shards, 50.98 GiB, revision `6f265714824f3c38d4452baa1628aef3d9b9aae9`, and 24
snapshot links. Register it in pi/oMLX but do not load or test it unless explicitly asked.

## 6. Start the preferred daemon

```sh
mtplx-start-bg
mtplx-status
```

Require `GET /v1/models` to return the served model ID `mtplx`. Do not run oMLX on port
8000 at the same time.

The Mac-side command used by `mtplx-start-bg` is:

```sh
mtplx serve --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --model-id mtplx --host 127.0.0.1 --port 8000 --no-auth --mtp
```

## 7. Verify direct inference

The first request may take several minutes because MTPLX loads the model and may tune or
warm the runtime. Do not kill it merely because the HTTP response is initially quiet.

```sh
curl -sS --max-time 900 http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"mtplx","messages":[{"role":"user","content":"Reply with exactly QWEN_OK"}],"temperature":0,"max_tokens":64,"stream":false}'
```

Require HTTP 200, model `mtplx`, content `QWEN_OK`, and `finish_reason: stop`.

## 8. Verify pi configuration and headless inference

Require these live values:

```text
defaultProvider: mtplx
defaultModel: mtplx
defaultThinkingLevel: off
```

Run `pi --list-models mtplx`; it must report provider `mtplx` and model `mtplx`.

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

If the error includes `[stall-watchdog-retry]`, remove `npm:@narumitw/pi-retry`. It is
unsuitable for quiet local model loads and long prefills.

## 9. Optional oMLX fallback checks

Only run these when explicitly validating the fallback runtime:

```sh
omlx-start-bg
brew services info omlx
omlx-status
pi --list-models qwen3.8
```

Require Qwen in `/v1/models` under the exact ID
`lmstudio-community--Qwen3.8-27B-MLX-8bit`. oMLX should classify it as a VLM and use its
VLM engine. Keep Laguna and GLM discoverable when their caches exist. Stop MTPLX or use a
different port before starting oMLX on 8000.

## 10. Final checks

```sh
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
python3 -m json.tool ~/.pi/agent/settings.json
pi --list-models mtplx
```

Report MTPLX version, daemon PID/state, served model ID, direct response, headless pi
response, and the command for starting the oMLX fallback. Leave MTPLX running and pi
selected to provider/model `mtplx`.

---