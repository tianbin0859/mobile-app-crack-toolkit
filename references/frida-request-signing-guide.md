---
name: frida-mobile-signing-reverse
tags: ['debugging', 'mobile', 'reverse-engineering']
triggers:
  - Frida
  - Frida移动逆向
  - Frida逆向
  - 修复错误
  - 移动应用
  - 移动端开发
  - 调试代码
description: Reverse engineer mobile app request signing (mTOP, custom protocols) using Frida dynamic instrumentation. Includes anti-debug bypass, StringBuilder/MD5/OkHttp interception, JSONL logging bridge, log analysis, and signature reconstruction pipeline.
version: 1.0.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: ['debugging', 'mobile', 'reverse-engineering']
    related_skills: [unity-il2cpp-memory-research, browser-use, tiktok-seckill-patterns, seckill-automation-framework, webview-seckill-architecture]




---




# Frida Mobile Signing Reverse Engineering

A complete pipeline for reverse engineering mobile app request signatures using Frida dynamic instrumentation and Python analysis tools. Proven against Ali mTOP (Damai, Taobao) and adaptable to any custom signing protocol.

## When to Use

- You need to understand how a mobile app constructs `sign`, `x-sign`, or HMAC parameters
- The signing logic is split across Java and Native (`libsgmain.so`, `libwind.so`, `libturing.so`)
- Static APK analysis fails because the key is dynamically negotiated at runtime
- You want to reconstruct the signing algorithm in Python for protocol replay

## Architecture Overview

```
Android Device (Frida)
    ├── anti_antidebug.js      → bypass SSL pinning, ptrace, TracerPid
    ├── string_interceptor.js  → hook StringBuilder, StringBuffer, MessageDigest
    ├── okhttp_sniffer.js      → hook OkHttp3 / WebView URLs and headers
    └── native_sign_hook.js    → scan / hook native crypto exports

           ↓ JSONL logs

Python Analysis Stack
    ├── frida_bridge.py        → attach, load multi-scripts, persist logs
    ├── log_analyzer.py        → extract signatures, URLs, hashes, param freq
    └── signature_reconstructor.py → match plaintext → hash, guess salt
```

## Step 1: Environment Setup

### Prerequisites
- Android 8.0+ device with **Magisk + Root** (emulators are easily detected)
- USB debugging enabled
- `frida` and `frida-tools` installed on host
- `frida-server` binary pushed to `/data/local/tmp/frida-server` and running as root

### Wireless Debugging (optional)
```bash
adb tcpip 5555
adb connect <phone-ip>:5555
frida-ps -R
```

## Step 2: Frida Script Stack

Load scripts in this order: **anti-debug first**, then interceptors.

### 2.1 anti_antidebug.js
**Purpose**: prevent the app from detecting Frida/ debugger and bypass SSL pinning.

Hook targets:
- `fopen` / `fgets` on `/proc/self/status` → fake `TracerPid: 0`
- `ptrace` → block `PTRACE_TRACEME`
- `X509TrustManager` / `SSLContext.init` → inject empty trust manager

### 2.2 string_interceptor.js
**Purpose**: capture the raw signing string before it is hashed.

Hook targets:
- `java.lang.StringBuilder.append(String)`
- `java.lang.StringBuffer.append(String)`
- `java.security.MessageDigest.update()` and `.digest()`

**Filter heuristics**: only log strings containing `sign`, `appKey`, `timestamp`, `&`, or `=` to reduce noise.

**Output example**:
```
[StringBuilder] appKey=123&itemId=456&price=880&t=1712345678901&key=SECRET
[MD5/SHA result] 7A4A9C9D18109A6E357BD7DF0F6FA015
```

### 2.3 okhttp_sniffer.js
**Purpose**: capture the actual network request to correlate signature with endpoint.

Hook targets:
- `okhttp3.Request$Builder.url(String)`
- `okhttp3.Request$Builder.addHeader(String, String)`
- `android.webkit.WebView.loadUrl(String)`

### 2.4 native_sign_hook.js
**Purpose**: discover and hook native security modules.

Actions:
- `Process.enumerateModules()` to find `libsgmain.so`, `libwind.so`, `libturing.so`
- `Module.enumerateExports()` to list `MD5`, `HMAC`, `sign`, `hash` symbols
- Attach to `MD5()` / `HMAC()` OpenSSL exports if present

## Step 3: Python Automation Bridge

### frida_bridge.py
Responsibilities:
1. `attach(package_name)` → spawn or attach to target process
2. `load_multi_scripts([...])` → load scripts sequentially
3. `_on_message()` → receive Frida `send()` payloads and append to JSONL
4. `interactive()` → keep session alive until Ctrl+C

**Log format** (`logs/frida/<timestamp>.jsonl`):
```json
{"timestamp": 1712345678.9, "type": "send", "payload": {"type": "string_append", "content": "..."}}
```

### log_analyzer.py
Responsibilities:
- `extract_signatures()` → filter `string_append` events with `sign=` or `&`
- `extract_urls()` → collect OkHttp / WebView / URLConnection URLs
- `extract_hashes()` → collect `digest_result` events
- `analyze_sign_patterns()` → Counter of query parameter keys across all signature strings

### signature_reconstructor.py
Responsibilities:
- `find_matching_hash(plaintext)` → compute MD5(plaintext) and search captured hashes
- `guess_salt()` → brute-force common salt patterns if plaintext MD5 does not match
- `analyze_timestamp_alignment()` → correlate `t=` in signature with log timestamp

**Golden rule**: if `MD5(plaintext) == captured_hash`, you have fully reconstructed the signing logic for that sample.

## Step 4: Reverse Engineering Methodology

1. **Run the app with anti-debug + network sniffer**
   - Verify you can see HTTPS URLs (SSL pinning is bypassed)
2. **Add string interceptor**
   - Perform the target action (e.g., click "Buy Now")
   - Look for long `&`-delimited strings
3. **Correlate**
   - Match the signature string timestamp with the network request timestamp
   - Confirm the hash output matches `MessageDigest.digest()` result
4. **Sample expansion**
   - Repeat 5~10 times with different items/prices/times
   - Identify fixed salts vs dynamic variables
5. **Native fallback**
   - If Java layer shows no raw string (only binary blob), move to `native_sign_hook.js`
   - Use IDA Pro / Ghidra on the security SO to find the hashing routine
6. **Python verification**
   - Replicate the algorithm in Python
   - Feed real app parameters and compare output to Frida-captured hashes

## Step 5: Integration into Protocol Replay

Once verified, plug the reconstructed algorithm into your request signer:

```python
def sign_request(params: dict) -> dict:
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    raw = f"{APP_KEY}{sorted_params}{SECRET_KEY}"
    sign = hashlib.md5(raw.encode()).hexdigest().upper()
    params["sign"] = sign
    return params
```

## Known Pitfalls

1. **Do NOT use `reverse-engineering` as a Python package directory name**
   - Python cannot import from directories with hyphens. Use `reverse_engineering` instead.

2. **Frida version must match frida-server exactly**
   - `frida --version` on host == frida-server binary version on device.

3. **Spawn mode is safer than attach for anti-debug apps**
   - Use `frida -U -f <package> -l script.js --no-pause` so hooks are installed before app init.

4. **Loguru fallback is required for test portability**
   - If `loguru` may not be installed in test environments, wrap the import:
   ```python
   try:
       from loguru import logger
   except ImportError:
       import logging
       logger = logging.getLogger(__name__)
   ```

5. **Chinese quotation marks break Python string literals**
   - When generating diagrams or text containing `“` / `「`, avoid nesting them inside Python double-quoted strings. Use single quotes or different bracket styles.

6. **Dynamic session keys (2024+ Ali apps)**
   - Some apps negotiate a temporary key at startup. A captured key from one session will not work in another. You must replicate the **key derivation** logic, not just the key value.

## Verification Checklist

- [ ] `frida-ps -U` lists the target app process
- [ ] `anti_antidebug.js` loads without app crash
- [ ] HTTPS URLs appear in Frida logs (SSL pinning bypassed)
- [ ] Signature strings appear in logs when clicking target action
- [ ] `log_analyzer.py` reports >0 signatures and >0 hashes
- [ ] `signature_reconstructor.py` finds at least one `MD5(plaintext) == captured_hash` match
- [ ] Python replica produces identical signatures for 5+ independent samples

## Example Command

```bash
python reverse_engineering/frida_bridge.py \
    frida-scripts/anti_antidebug.js \
    frida-scripts/okhttp_sniffer.js \
    frida-scripts/string_interceptor.js
```

Then analyze:
```bash
python reverse_engineering/log_analyzer.py
python reverse_engineering/signature_reconstructor.py
```

## Reference Documents

| Document | Description |
|----------|-------------|
| `references/apk-static-analysis.md` | Static APK analysis quick-reference: extract info without running the app, identify Auto.js frameworks, game automation tools, and packing/obfuscation signatures |
