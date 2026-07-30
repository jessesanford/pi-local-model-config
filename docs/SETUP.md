# Setup guide

## Prerequisites

- macOS 15+ (Sequoia) or macOS 26+
- Apple Silicon (M1/M2/M3/M4/M5). This config is tuned for M5 Max 40-core / 128GB.
- Homebrew installed
- Node.js (for pi installation)
- Python 3.11+ (Homebrew's; used for tools/)
- ~200 GB free disk (Laguna oQ4e-fast alone is ~60 GB; you likely want the oQ4e
  variant too plus HF cache overhead)
- **Disable macOS Low Power Mode** in Battery settings — it roughly halves MLX throughput

## 1. Install pi

```
curl -fsSL https://pi.dev/install.sh | sh
```

Verify: `pi --version`

## 2. Install oMLX

```
brew tap jundot/omlx https://github.com/jundot/omlx
brew trust jundot/omlx
brew install omlx
```

Verify: `omlx --version` (expect 0.5.3+).

## 3. Download models

### 3a. Preferred: via oMLX or manually into HF cache

If HuggingFace CDN downloads work directly on your network, oMLX will fetch on demand.
If you're on a corporate network (Zscaler etc.), see the Zscaler section below.

Models this config expects (only oQ4e-fast is strictly required):
- `mlx-community/Laguna-S-2.1-oQ4e-fast`  (primary, ~60 GB, 1M context)
- `mlx-community/Laguna-S-2.1-oQ4e`       (older/slower, keep for A/B, ~60 GB)
- `poolside/Laguna-S-2.1-DFlash`          (draft for spec decode; NOT USABLE today,
                                           see Known Limitations, but keep for the future)

You can pull them via any of:
```
# via oMLX (uses ~/.cache/huggingface/hub automatically if --hf-cache passed to serve)
omlx serve --hf-cache   # downloads on first chat/completions request for that model

# or via huggingface_hub CLI
hf download mlx-community/Laguna-S-2.1-oQ4e-fast
```

### 3b. Alternate: reuse LM Studio downloads

If you already have models in `~/.lmstudio/models/`, use the linker to hardlink them
into HF cache format without duplicating storage:

```
python3 tools/link_lmstudio_to_hf.py
```

This scans `~/.lmstudio/models/<org>/<repo>/` for MLX models (config.json + safetensors),
queries HuggingFace for the correct blob hashes, then hardlinks each file into
`~/.cache/huggingface/hub/models--<org>--<repo>/blobs/<etag>` with proper symlinks in
`snapshots/<revision>/`. Storage cost is zero (hardlinks share inodes).

## 4. Install configs

```
# oMLX
cp configs/omlx-settings.json         ~/.omlx/settings.json
mkdir -p ~/.omlx/models
cp configs/omlx-model-settings.json   ~/.omlx/models/model_settings.json

# pi
mkdir -p ~/.pi/agent
cp configs/pi-settings.json           ~/.pi/agent/settings.json
cp configs/pi-models.json             ~/.pi/agent/models.json
```

**IMPORTANT:** the copied `omlx-settings.json` has `auth.secret_key` set to a placeholder.
oMLX will regenerate a real key on first launch — that's fine.

## 5. Install scripts

```
mkdir -p ~/.local/bin
cp scripts/omlx-* ~/.local/bin/
chmod +x ~/.local/bin/omlx-*
# make sure ~/.local/bin is on PATH
grep -q '.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

## 6. Start the server

Foreground:
```
omlx-start
```

Or background:
```
omlx-start-bg
```

Then verify:
```
omlx-status
pi -p "reply: OK"
```

## Zscaler / corporate SSL workaround (for HF downloads and Nativ)

If your corporate network intercepts SSL (Zscaler):

1. Extract Zscaler root CA:
   ```
   security find-certificate -a -c "Zscaler" -p /Library/Keychains/System.keychain > /tmp/zscaler.pem
   ```
2. Merge with certifi bundle and put in a stable location:
   ```
   mkdir -p ~/.config/nativ
   cat $(python3 -c "import certifi; print(certifi.where())") /tmp/zscaler.pem > ~/.config/nativ/cacert.pem
   ```
3. Set env vars persistently for GUI apps (Nativ, HF CLI):
   ```
   launchctl setenv SSL_CERT_FILE "$HOME/.config/nativ/cacert.pem"
   launchctl setenv REQUESTS_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
   launchctl setenv CURL_CA_BUNDLE "$HOME/.config/nativ/cacert.pem"
   ```
4. HuggingFace Xet is also broken behind Zscaler — force the classic HTTP downloader:
   ```
   launchctl setenv HF_HUB_DISABLE_XET 1
   launchctl setenv HF_HUB_ENABLE_HF_TRANSFER 0
   ```
5. Zscaler DLP also blocks Python (.py) file downloads. When fetching models that include
   a `config.py` (e.g. `poolside/Laguna-S-2.1-DFlash`), briefly disconnect Zscaler for the
   config.py fetch, then reconnect.

## Verify tuning

```
python3 tools/bench_omlx.py
```

Expected on M5 Max High Power:
- decode ~60-65 tok/s
- TTFT small prompt ~360 ms
- TTFT 1k prompt ~640 ms
