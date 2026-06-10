# Module Integration Pattern

## When to Use

When you have a standalone module/script from a specific project that should be integrated into a skill for reuse across projects.

## Example: License Manager Integration

**Source**: DNF Gold Bot project (`modules/license_manager.py`)
**Target**: APK Crack Engine skill (Module 6)

### Steps

1. **Identify reusable components** from the standalone module:
   - License generation
   - License validation
   - Machine binding
   - Batch generation

2. **Create skill module** with broader scope:
   - Rename from project-specific to generic
   - Add more authentication types
   - Add crack capabilities (both protect AND crack)

3. **Add to skill architecture**:
   - Add module section in SKILL.md
   - Include code examples
   - Add command-line usage
   - Document common auth types and crack methods

4. **Create reference docs**:
   - `references/license-management.md` - Detailed guide
   - Document 8+ auth types with crack difficulty ratings

### Key Insight

A module originally designed for "protecting" software can be extended to also "crack" software by:
- Understanding the protection mechanism
- Creating reverse operations
- Documenting both sides (protect + crack)

## Integration Checklist

- [ ] Extract core functionality from standalone module
- [ ] Generalize naming (remove project-specific references)
- [ ] Add both "use" and "break" documentation
- [ ] Include in skill's module list
- [ ] Add command-line examples
- [ ] Create reference documentation
- [ ] Update version history
