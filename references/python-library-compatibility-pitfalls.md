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
| click | `@command()` with same function name | `@command(name="...")` + unique function name | `NameError: name 'analyze' is not defined` or duplicate command registration |
| Python f-string | `f"path_{id.replace(':', '_')}.png"` | `"path_" + id.replace(":", "_") + ".png"` | `SyntaxError: f-string expression part cannot include a backslash` or quote conflicts |

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

## click: Command Name Collision

**Problem:** Multiple CLI command groups use the same function name `analyze`, causing `NameError` or duplicate command registration when all groups are imported into the same CLI module.

**Root Cause:** When using `click` decorators, the function name becomes the command name by default. If multiple modules define `@click.command()` on functions named `analyze`, importing them all into a single CLI module causes name collisions.

**Fix:** Use explicit `name=` parameter in the `@click.command()` decorator, and use unique function names.

```python
# ❌ BROKEN - Name collision when multiple groups imported
@click.command()
def analyze():
    pass

# ✅ WORKING - Explicit name + unique function name
@click.command(name="analyze")
def ai_analyze():
    pass

@click.command(name="analyze")
def deob_analyze():
    pass

@click.command(name="analyze")
def scan_analyze():
    pass
```

**CLI Result:**
```bash
crack ai analyze <apk>      # → ai_analyze function
crack deob analyze <apk>    # → deob_analyze function
crack scan analyze <apk>     # → scan_analyze function
```

**Rule:** Always use `name=` parameter when the command name might collide with other commands. Keep function names descriptive and unique.

## Python f-string: Nested Quote Conflicts

**Problem:** f-strings containing method calls with string arguments cause `SyntaxError` due to quote conflicts.

**Root Cause:** When an f-string expression contains a method call with string arguments (e.g., `.replace(':', '_')`), the quotes inside the expression conflict with the f-string's outer quotes.

**Fix:** Use string concatenation instead of f-string for complex expressions with nested quotes.

```python
# ❌ BROKEN - SyntaxError: f-string expression part cannot include a backslash
# (or quote conflicts)
screenshot_path = f"/tmp/screenshot_{device_id.replace(':', '_')}.png"

# ✅ WORKING - String concatenation avoids quote conflicts
screenshot_path = "/tmp/screenshot_" + device_id.replace(":", "_") + ".png"

# Alternative: Use double quotes for outer, single for inner (works for simple cases)
screenshot_path = f'/tmp/screenshot_{device_id.replace(":", "_")}.png'
```

**Rule of Thumb:**
- Use f-strings for simple variable interpolation only
- Use string concatenation (`+`) when the expression contains method calls with string arguments
- Use `str.format()` or `%` formatting for complex cases with many nested quotes

**Example from v7.5 device_manager.py:**
```python
# Original (broken):
output_path = f"/tmp/screenshot_{device_id.replace(':', '_')}.png"

# Fixed:
output_path = "/tmp/screenshot_" + device_id.replace(":", "_") + ".png"
```
