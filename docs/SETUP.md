# Setup

## Requirements

- Apple Silicon Mac with enough unified memory for the selected model
- macOS 15 or newer
- Homebrew, Node.js, and Python 3.11+
- oMLX 0.5.7 or newer for current Qwen VLM support

## 1. Install pi and oMLX

```sh
curl -fsSL https://pi.dev/install.sh | sh

brew tap jundot/omlx https://github.com/jundot/omlx
brew install omlx
brew update && brew upgrade omlx

pi --version
omlx --version
```

oMLX includes `mlx-vlm` and is the OpenAI-compatible, multi-model daemon used by pi.

## 2. Install configuration

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

Ensure `~/.local/bin` is on `PATH`.

Do not install `npm:@narumitw/pi-retry`. Its 90-second stream watchdog is unsuitable for
silent local model loads and long prefills. If already installed, remove it:

```sh
pi remove npm:@narumitw/pi-retry
```

## 3. Link LM Studio models

LM Studio and Hugging Face use different cache layouts. The linker creates hardlinks,
so it does not duplicate model weights:

```sh
python3 tools/link_lmstudio_to_hf.py lmstudio-community/Qwen3.8-27B-MLX-8bit
python3 tools/link_lmstudio_to_hf.py mlx-community/Qwen3.8-27B-bf16  # optional
```

Run it only after LM Studio finishes downloading. It accepts multiple model IDs; omit
them to scan all complete LM Studio MLX downloads.

## 4. Start and select

```sh
omlx-start-bg
omlx-status
pi -p "Reply with OK"
```

Aliases are `qwen`, `qwen-bf16`/`qwen16`, `laguna-fast`, `laguna`, and `glm`. Any full oMLX model ID also
works. With no model argument, `omlx-model`, `omlx-start`, `omlx-start-bg`, and
`omlx-restart` select Qwen and provider `omlx`. Changing pi's model does not require a
restart:

```sh
omlx-model glm
omlx-model laguna-fast
omlx-model qwen
omlx-model qwen-bf16  # optional 51 GiB bf16 model; first request loads it
```

The bf16 option is registered with 262,144 context and image support, but is intentionally
not inference-tested by this setup. Return to the default with `omlx-model qwen`.

Restart for daemon or configuration changes:

```sh
omlx-restart
```

## 5. Verify and benchmark

```sh
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
python3 tools/bench_omlx.py --model qwen --no-nativ
```

Expected smoke-test results:

```text
direct oMLX response: QWEN_OK
headless pi response: PI_QWEN_OK
```

The configured SSD cache path is `~/.omlx/cache-0.5.7`. A separate older
`~/.omlx/cache` can remain in place, but oMLX must not scan it when starting Qwen.

Use this minimal headless test to avoid extension startup affecting diagnosis:

```sh
pi --print --mode text --no-extensions --no-skills --no-context-files \
  --no-tools --no-session --offline \
  --system-prompt 'Answer exactly as requested.' \
  'Reply with exactly: PI_QWEN_OK'
```

For a separate Nativ comparison, provide its slash-form model ID explicitly:

```sh
python3 tools/bench_omlx.py --model qwen \
  --nativ-model mlx-community/Laguna-S-2.1-oQ4e-fast
```

## Corporate TLS interception

The scripts automatically use `~/.config/nativ/cacert.pem` when present and disable
Hugging Face Xet. To build a Zscaler-compatible bundle:

```sh
security find-certificate -a -c "Zscaler" -p \
  /Library/Keychains/System.keychain > /tmp/zscaler.pem
mkdir -p ~/.config/nativ
cat "$(python3 -c 'import certifi; print(certifi.where())')" \
  /tmp/zscaler.pem > ~/.config/nativ/cacert.pem

launchctl setenv SSL_CERT_FILE "$HOME/.config/nativ/cacert.pem"
launchctl setenv REQUESTS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv CURL_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv HF_HUB_DISABLE_XET 1
```