# Setup

## Requirements

- Apple Silicon Mac with enough unified memory for the selected model
- macOS 15 or newer
- Homebrew, Node.js, and Python 3.11+
- MTPLX 2.9.0 or newer for Qwen native-MTP serving
- oMLX 0.5.7 or newer only for fallback multi-model/VLM serving

## 1. Install pi and MTPLX

```sh
curl -fsSL https://pi.dev/install.sh | sh

brew install youssofal/mtplx/mtplx
mtplx --version
```

The MTPLX Mac app is also valid: download the DMG from `https://mtplx.com/download`, drag
it to Applications, and launch MTPLX. The app installs `~/.mtplx/bin/mtplx` and its own
runtime under `~/Library/Application Support/MTPLX`.

MTPLX is preferred for Qwen 3.8 because it serves
`Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed` with native MTP enabled by default. Direct
`mlx-vlm` is not the preferred daemon.

Install oMLX only when you need the fallback multi-model setup:

```sh
brew tap jundot/omlx https://github.com/jundot/omlx
brew install omlx
brew update && brew upgrade omlx

omlx --version
```

## 2. Install configuration

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

Ensure `~/.local/bin` is on `PATH`.

The checked-in pi default is MTPLX:

```text
defaultProvider: mtplx
defaultModel: mtplx
base URL: http://127.0.0.1:8000/v1
```

Do not install `npm:@narumitw/pi-retry`. Its 90-second stream watchdog is unsuitable for
silent local model loads and long prefills. If already installed, remove it:

```sh
pi remove npm:@narumitw/pi-retry
```

## 3. Download the MTPLX Qwen model

Use MTPLX's downloader for the preferred model:

```sh
mtplx-start-bg --download
```

The expected cache path is:

```text
~/.mtplx/models/Youssofal--Qwen3.8-27B-MTPLX-Optimized-Speed
```

If you are behind Zscaler or another TLS-intercepting proxy, complete the Corporate TLS
interception section before retrying downloads.

## 4. Optional: link LM Studio models for oMLX fallback

LM Studio and Hugging Face use different cache layouts. The linker creates hardlinks,
so it does not duplicate model weights:

```sh
python3 tools/link_lmstudio_to_hf.py lmstudio-community/Qwen3.8-27B-MLX-8bit
python3 tools/link_lmstudio_to_hf.py mlx-community/Qwen3.8-27B-bf16  # optional
```

Run it only after LM Studio finishes downloading. It accepts multiple model IDs; omit
them to scan all complete LM Studio MLX downloads.

## 5. Start and select

```sh
mtplx-start-bg
mtplx-status
pi -p "Reply with OK"
```

`mtplx-start-bg` runs this Mac-local API server command:

```sh
mtplx serve --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --model-id mtplx --host 127.0.0.1 --port 8000 --no-auth --mtp
```

It logs to `/tmp/mtplx.log`, records `/tmp/mtplx.pid`, and stops the oMLX fallback first
if oMLX owns port 8000. Use `mtplx-stop` to stop the MTPLX server.

For oMLX fallback, aliases are `qwen`, `qwen-bf16`/`qwen16`, `laguna-fast`, `laguna`,
and `glm`. Any full oMLX model ID also works. Starting oMLX on port 8000 conflicts with
MTPLX on the same port, so stop one before starting the other.

```sh
omlx-model glm
omlx-model laguna-fast
omlx-model qwen
omlx-model qwen-bf16  # optional 51 GiB bf16 model; first request loads it
```

The bf16 option is registered with 262,144 context and image support, but is intentionally
not inference-tested by this setup. Return to the oMLX fallback Qwen with `omlx-model qwen`.

Restart oMLX only for fallback daemon or fallback configuration changes:

```sh
omlx-restart
```

## 6. Verify and benchmark

```sh
curl -sS http://127.0.0.1:8000/v1/models | python3 -m json.tool
```

Expected smoke-test results:

```text
direct MTPLX response: QWEN_OK
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

For an oMLX fallback or Nativ comparison, start that server and use the benchmark tool
explicitly:

```sh
python3 tools/bench_omlx.py --model qwen \
  --nativ-model mlx-community/Laguna-S-2.1-oQ4e-fast
```

## Corporate TLS interception

The oMLX scripts and patched MTPLX launcher automatically use
`~/.config/nativ/cacert.pem` when present and disable Hugging Face Xet.
Python 3.14/OpenSSL 3.5 can reject some macOS-trusted corporate roots under strict
verification, so prefer a certifi bundle plus the strict-compatible Zscaler CA
certificates from the intercepted Hugging Face chain:

```sh
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/hf-zscaler-ca.XXXXXX")
trap 'rm -rf "$tmpdir"' EXIT

openssl s_client -connect huggingface.co:443 -servername huggingface.co \
  -showcerts </dev/null > "$tmpdir/chain.txt" 2>/dev/null

awk '/-----BEGIN CERTIFICATE-----/{n++; in_cert=1} in_cert{print > sprintf("'"$tmpdir"'/chain-%04d.pem", n)} /-----END CERTIFICATE-----/{in_cert=0}' \
  "$tmpdir/chain.txt"

mkdir -p ~/.config/nativ
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

launchctl setenv SSL_CERT_FILE "$HOME/.config/nativ/cacert.pem"
launchctl setenv REQUESTS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv CURL_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv NODE_EXTRA_CA_CERTS "$HOME/.config/nativ/cacert.pem"
launchctl setenv GRPC_DEFAULT_SSL_ROOTS_FILE_PATH "$HOME/.config/nativ/cacert.pem"
launchctl setenv AWS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
launchctl setenv HF_HUB_DISABLE_XET 1
launchctl setenv HF_HUB_ENABLE_HF_TRANSFER 0
```

Restart GUI apps after setting the launchd environment. Already-running apps do not
inherit changed variables.
