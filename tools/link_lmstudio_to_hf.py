#!/usr/bin/env python3
"""Hardlink selected LM Studio MLX models into HF cache format."""
import argparse
import json
import os
import urllib.error
import urllib.request

LMS_ROOT = os.path.expanduser("~/.lmstudio/models")
HF_CACHE = os.path.expanduser("~/.cache/huggingface/hub")

def fetch_tree(repo_id):
    url = f"https://huggingface.co/api/models/{repo_id}/tree/main?recursive=true"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"__err__": f"HTTP {e.code}"}
    except Exception as e:
        return {"__err__": str(e)}

def fetch_revision(repo_id):
    url = f"https://huggingface.co/api/models/{repo_id}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"}), timeout=15) as r:
            return json.load(r).get("sha")
    except Exception:
        return None

def process(repo_id, src_dir):
    print(f"\n=== {repo_id} ===")
    tree = fetch_tree(repo_id)
    if isinstance(tree, dict) and "__err__" in tree:
        print(f"  SKIP: HF lookup failed ({tree['__err__']})")
        return
    rev = fetch_revision(repo_id)
    if not rev:
        print("  SKIP: no revision"); return
    dst = os.path.join(HF_CACHE, f"models--{repo_id.replace('/', '--')}")
    # Verify files
    missing, mismatched = [], []
    for f in tree:
        if f.get("type") != "file": continue
        p = os.path.join(src_dir, f["path"])
        if not os.path.exists(p):
            missing.append(f["path"])
        elif os.path.getsize(p) != f.get("size", 0):
            mismatched.append((f["path"], os.path.getsize(p), f["size"]))
    if mismatched:
        print(f"  SKIP: size mismatch on {len(mismatched)} file(s): {mismatched[:3]}")
        return
    if missing:
        # Small files can be fetched; large LFS files cannot
        big_missing = [m for m in missing if any(f["path"]==m and (f.get("lfs") or {}).get("oid") for f in tree)]
        if big_missing:
            print(f"  SKIP: missing large files: {big_missing[:3]}")
            return
        print(f"  WARN: fetching {len(missing)} small missing files: {missing}")
        for m in missing:
            url = f"https://huggingface.co/{repo_id}/resolve/main/{m}"
            try:
                urllib.request.urlretrieve(url, os.path.join(src_dir, m))
            except Exception as e:
                print(f"  FAIL fetch {m}: {e}"); return
    # Build cache dirs
    os.makedirs(os.path.join(dst, "blobs"), exist_ok=True)
    snap_dir = os.path.join(dst, "snapshots", rev)
    os.makedirs(snap_dir, exist_ok=True)
    os.makedirs(os.path.join(dst, "refs"), exist_ok=True)
    with open(os.path.join(dst, "refs", "main"), "w") as f: f.write(rev)
    ok = 0
    for f in tree:
        if f.get("type") != "file": continue
        name = f["path"]
        etag = (f.get("lfs") or {}).get("oid") or f.get("oid")
        sp = os.path.join(src_dir, name)
        bp = os.path.join(dst, "blobs", etag)
        snap = os.path.join(snap_dir, name)
        os.makedirs(os.path.dirname(snap), exist_ok=True)
        if not os.path.exists(bp):
            try:
                os.link(sp, bp)
            except OSError as e:
                print(f"  link fail {name}: {e}"); continue
        if os.path.lexists(snap): os.remove(snap)
        os.symlink(os.path.relpath(bp, os.path.dirname(snap)), snap)
        ok += 1
    print(f"  LINKED {ok} files, rev={rev[:12]}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", nargs="*", help="HF model ID(s), or all models when omitted")
    parser.add_argument("--lmstudio-root", default=LMS_ROOT)
    args = parser.parse_args()
    requested = set(args.model)

    candidates = []
    for org in os.listdir(args.lmstudio_root):
        org_dir = os.path.join(args.lmstudio_root, org)
        if not os.path.isdir(org_dir): continue
        for repo in os.listdir(org_dir):
            repo_id = f"{org}/{repo}"
            if requested and repo_id not in requested: continue
            model_dir = os.path.join(org_dir, repo)
            if not os.path.isdir(model_dir): continue
            if not os.path.exists(os.path.join(model_dir, "config.json")): continue
            if not any(name.endswith(".safetensors") for name in os.listdir(model_dir)): continue
            candidates.append((repo_id, model_dir))

    found = {repo_id for repo_id, _ in candidates}
    missing = requested - found
    if missing:
        parser.error("model not found in LM Studio: " + ", ".join(sorted(missing)))
    for repo_id, source in candidates:
        process(repo_id, source)


if __name__ == "__main__":
    main()
