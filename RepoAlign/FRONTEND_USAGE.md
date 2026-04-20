# Sub-phase 5.7: Frontend Request Trigger - User Guide

## Overview

Sub-phase 5.7 adds the frontend trigger functionality to the VS Code extension, allowing users to:

1. Open a file in the editor
2. Enter an instruction to improve the code
3. Receive a generated patch with a diff and statistics

## Getting Started

### Prerequisites

1. **Backend Running**: Ensure the RepoAlign backend is running:

   ```bash
   docker-compose up -d
   ```

2. **Extension Installed**: Load the extension in VS Code:
   - Navigate to `frontend` folder
   - Run `npm install` (if needed)
   - Run `npm run compile`
   - Press `F5` to open Extension Development Host

3. **Code Indexed**: Run the "Analyze Workspace" command first:
   - `Ctrl+Shift+P` → Search "RepoAlign: Analyze Workspace"
   - This builds the knowledge graph for context retrieval

## Using the Generate Patch Feature

### Method 1: Command Palette (Easiest)

1. **Open any Python file** in the editor
2. **Open Command Palette**: `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
3. **Search for**: "RepoAlign: Generate Code Patch"
4. **Enter your instruction**, e.g.:
   - "Add error handling to this function"
   - "Improve documentation with type hints"
   - "Optimize this loop for performance"
5. **View results** in the RepoAlign output channel

### Method 2: Keyboard Shortcut

1. **Open any Python file** and put cursor in it (give it focus)
2. **Press**: `Ctrl+Shift+Alt+G` (Windows/Linux) or `Cmd+Shift+Alt+G` (Mac)
3. **Enter your instruction**
4. **View results**

## Output Format

When you generate a patch, results appear in the **RepoAlign Output Channel** with:

```
=== RepoAlign Patch Generation Results ===

Query: Your instruction here
File: path/to/your/file.py

--- Statistics ---
Lines Added: 5
Lines Removed: 1
Lines Modified: 2
Total Changes: 8
Similarity Ratio: 92.34%

--- Generated Diff ---
--- a/path/to/file.py	original
+++ b/path/to/file.py	generated
@@ -1,5 +1,8 @@
 def original_function():
-    pass
+    """Function with documentation."""
+    # Implementation here
+    try:
+        # code
+    except Exception as e:
+        print(f"Error: {e}")

--- Generated Code ---
def original_function():
    """Function with documentation."""
    # Implementation here
    try:
        # code
    except Exception as e:
        print(f"Error: {e}")
```

## Understanding the Output

### Statistics

- **Lines Added**: New lines in generated code
- **Lines Removed**: Old lines that were replaced/deleted
- **Lines Modified**: Lines that changed
- **Total Changes**: Sum of added + removed + modified
- **Similarity Ratio**: How similar original and generated are (0-100%)
  - 95-100% = Minimal changes
  - 80-95% = Minor improvements
  - 60-80% = Significant changes
  - <60% = Major rewrite

### Diff Format

Standard unified diff format compatible with:

- `git apply`
- `patch` command
- Diff viewers
- VS Code diff editors

## Workflow Example

### Scenario: Add Error Handling

**Step 1**: Open a Python file

```python
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

**Step 2**: Press `Ctrl+Shift+Alt+G` or use Command Palette

**Step 3**: Enter instruction:

```
Add error handling and improve the email validation function
```

**Step 4**: View output in RepoAlign channel with:

- Generated improved version
- Unified diff showing changes
- Statistics about the changes

**Step 5**: Decide whether to:

- Copy the generated code
- Apply the diff manually
- Use it as inspiration
- Discard and try different instruction

## Common Instructions

### Adding Documentation

```
Add comprehensive docstrings with parameter descriptions and type hints
```

### Error Handling

```
Add try-except blocks and proper error handling with logging
```

### Performance

```
Optimize this function for better performance and reduce complexity
```

### Code Quality

```
Improve code readability and follow Python best practices
```

### Type Safety

```
Add type hints to all function parameters and return types
```

### Testing

```
Add assertion checks and input validation at the start of this function
```

## Tips & Best Practices

1. **Be Specific**: More detailed instructions → better results
   - ❌ "Make it better"
   - ✅ "Add input validation and error messages"

2. **One Change at a Time**: Generate patches for specific improvements
   - ❌ "Refactor everything"
   - ✅ "Add error handling to this function"

3. **Review Before Applying**: Always review the diff before using generated code

4. **Check Similarity Ratio**:
   - High ratio (>90%) = Safe, minor changes
   - Low ratio (<60%) = Review carefully, major changes

5. **Context Matters**: The backend retrieves related code for context
   - Better results with descriptive function/variable names
   - Related code in same file helps

## Troubleshooting

### "Please open a file in the editor first"

- **Solution**: Click in a file editor to give it focus, then try again

### "No instruction provided"

- **Solution**: You need to enter an instruction in the input box
- Don't leave it empty

### "Failed to generate patch"

- **Possible causes**:
  1. Backend not running → Start with `docker-compose up -d`
  2. Code not indexed → Run "RepoAlign: Analyze Workspace" first
  3. LLM not responding → Check backend logs
  4. Invalid request → Try simpler instruction

### "Command not found"

- **Solution**:
  - Make sure extension is activated (F5 in Extension Development Host)
  - Run `npm run compile` to rebuild TypeScript
  - Reload VS Code window

### Empty or nonsensical generated code

- **Explanation**: TinyLLaMA 1.1GB is small; consider upgrading to larger model
- **Workaround**: Increase `limit` in backend request for more context
- **Solution**: Use `codellama:7b` or better model in Ollama

## File Structure Changes (Sub-phase 5.7)

**Created/Modified Files:**

- `frontend/src/extension.ts` - Added `generatePatch` command
- `frontend/package.json` - Registered new command and keybinding

**Key Addition:**

```typescript
// New command: repoalign.generatePatch
- Shows input dialog for user instruction
- Gets current file content
- Calls /generate-patch endpoint
- Displays results in output channel
```

## Next Steps (Sub-phases 5.8-5.10)

### 5.8: Frontend Diff Viewer

- Replace output channel with native VS Code diff viewer
- Side-by-side comparison in editor
- Better visual representation

### 5.9: Frontend User Actions

- "Accept" button to apply patch
- "Reject" button to discard
- "Edit" to modify before applying

### 5.10: End-to-End Loop

- Full workflow: Generate → Review → Accept/Reject
- Apply accepted patches to actual files
- Show confirmation and undo options

## Status

✅ **Sub-phase 5.7 COMPLETE**

The frontend now has a functional trigger to generate code patches!

### What Works:

- ✅ Command palette integration
- ✅ Keyboard shortcut (Ctrl+Shift+Alt+G)
- ✅ Input dialog for instructions
- ✅ API call to backend
- ✅ Output channel display
- ✅ Results with diff and stats

### For User:

- ✅ Can generate patches from VS Code editor
- ✅ Can review diffs in output channel
- ✅ Can copy/paste or manually apply changes
- ✅ Can iterate with different instructions

---

**Ready for Sub-phase 5.8: Frontend Diff Viewer** 🚀
