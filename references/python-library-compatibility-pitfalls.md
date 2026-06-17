# Python Library Compatibility Pitfalls

Session-specific technical pitfalls discovered when building Python-based reverse engineering tools. These affect Frida scripting, cryptography operations, and module import patterns.

## Frida API: Session Type Annotation

**Problem:** Using `frida.Session` as a type annotation causes `AttributeError: module 'frida' has no attribute 'Session'`.

**Root Cause:** Newer versions of Frida (16.x+) do not expose `Session` as a top-level module attribute. The class exists internally but is not importable/referencable from the module namespace.

**Fix:** Remove type annotations for Frida session objects, or use `typing.Any` / `object` instead.

```python
# ❌ BROKEN - AttributeError
class FridaHook:
    def spawn_app(self) -> frida.Session:
        ...

# ✅ WORKING - No type annotation
class FridaHook:
    def spawn_app(self):
        self.session = self.device.attach(pid)
        return self.session
```

**Affected Methods:** `spawn_app()`, `attach_running()`, any method returning Frida internal objects.

## cryptography: PBKDF2 → PBKDF2HMAC

**Problem:** `from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2` fails with `ImportError: cannot import name 'PBKDF2'`.

**Root Cause:** The `cryptography` library renamed `PBKDF2` to `PBKDF2HMAC` in newer versions (3.4+). The old name was removed.

**Fix:** Use `PBKDF2HMAC` instead.

```python
# ❌ BROKEN - ImportError
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

# ✅ WORKING - Correct import
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Usage (same API)
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=b'salt',
    iterations=100000,
)
```

**Note:** Both `PBKDF2HMAC` and `PBKDF2` (if available in older versions) have identical constructor signatures. The change is purely a rename.

## Import Path Resolution: Relative vs Absolute

**Problem:** `from .config import ...` works when running a module directly but fails when the module is imported from a different entry point (e.g., CLI script vs package import).

**Root Cause:** Python's relative import resolution depends on `__name__` and `__package__`. When a module is imported as part of a package vs run as `__main__`, the relative path resolution differs.

**Fix:** Use absolute imports for package modules that may be imported from multiple entry points.

```python
# ❌ BROKEN - Relative import fails when entry point changes
from .config import CACHE_DIR, OUTPUT_DIR

# ✅ WORKING - Absolute import stable across entry points
from core.config import CACHE_DIR, OUTPUT_DIR
```

**Rule of Thumb:**
- Use relative imports (`from .module`) only within tightly coupled submodules that are always imported together
- Use absolute imports (`from package.module`) for any module that may be imported from CLI scripts, web servers, or test runners

## Quick Reference Table

| Library | Old API | New API | Error Symptom |
|---------|---------|---------|---------------|
| frida | `frida.Session` (type annotation) | `object` or no annotation | `AttributeError: module 'frida' has no attribute 'Session'` |
| cryptography | `PBKDF2` | `PBKDF2HMAC` | `ImportError: cannot import name 'PBKDF2'` |
| Python imports | `from .config import X` | `from core.config import X` | `ModuleNotFoundError: No module named 'modules.config'` |

## Detection Pattern

When building Python reverse engineering tools, always test imports from the CLI entry point:

```bash
# Test from package import
python -c "from modules.apk import APKAnalyzer"

# Test from CLI entry point
python -m core.cli --help

# Test after pip install
crack --help
```

Import errors that appear only in certain entry points indicate path resolution issues.
