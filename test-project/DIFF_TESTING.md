# Testing Sub-phase 5.5: Diff Generation

After you run "Analyze Workspace" and generate code via the API, you can test diff generation.

## Test Scenario

### Original File Content

Here's the original `utils/helpers.py` - notice it has a basic `validate_email` function:

```python
import re
from typing import List

def format_greeting(name: str) -> str:
    """Formats a greeting message."""
    return f"Hello, {name}!"

def validate_email(email: str) -> bool:
    """Validates if an email address has correct format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ... other functions ...
```

### Generated Code from LLM

When you call `/api/v1/generate-code` with query "Enhance email validation with domain checking":

The LLM generates:
```python
def validate_email_enhanced(email: str) -> Tuple[bool, Optional[str]]:
    """
    Enhanced email validation with domain extraction.
    
    Returns tuple of (is_valid, domain)
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,})$'
    match = re.match(pattern, email)
    if match:
        domain = match.group(1)
        return True, domain
    return False, None
```

### Generated Diff (`.diff` format)

The diff generator compares original vs generated:

```diff
--- a/utils/helpers.py
+++ b/utils/helpers.py
@@ -1,6 +1,20 @@
 import re
 from typing import List
 
+from typing import Tuple, Optional
+
 def format_greeting(name: str) -> str:
     """Formats a greeting message."""
     return f"Hello, {name}!"
 
 def validate_email(email: str) -> bool:
@@ -10,3 +24,19 @@
     return re.match(pattern, email) is not None
 
+def validate_email_enhanced(email: str) -> Tuple[bool, Optional[str]]:
+    """
+    Enhanced email validation with domain extraction.
+    
+    Returns tuple of (is_valid, domain)
+    """
+    pattern = r'^[a-zA-Z0-9._%+-]+@((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,})$'
+    match = re.match(pattern, email)
+    if match:
+        domain = match.group(1)
+        return True, domain
+    return False, None
+
```

## How Sub-phase 5.5 Works

The `DiffGenerator` service provides:

### 1. Unified Diff Generation
```python
from app.services.diff_generator import DiffGenerator

generator = DiffGenerator()
diff = generator.generate_unified_diff(
    original_content=original_code,
    generated_content=generated_code,
    file_path="utils/helpers.py"
)
```

Returns standard `.diff` format compatible with:
- `patch` command
- Git
- Diff viewers
- VS Code

### 2. Diff Statistics

```python
stats = generator.get_diff_stats(original_code, generated_code)
# Returns:
# {
#   "lines_added": 14,
#   "lines_removed": 0,
#   "lines_modified": 1,
#   "total_changes": 15,
#   "similarity_ratio": 0.8234,
#   "identical": False
# }
```

### 3. Significance Detection

```python
is_significant = generator.is_significant_diff(
    original_code,
    generated_code,
    threshold=0.85
)
# True if changes are meaningful (< 85% similarity)
```

### 4. Patch File Operations

```python
# Save diff to file
generator.save_patch_file(diff, "generated.patch")

# Load diff from file
patch = generator.load_patch_file("generated.patch")
```

## Next Steps (Sub-phase 5.6)

Sub-phase 5.6 will create a `/generate-patch` endpoint that:
1. Calls `/generate-code` to get generated code
2. Reads the original file content
3. Uses `DiffGenerator` to create the diff
4. Returns the patch to the user

This completes the backend pipeline:
```
User Instruction
    ↓
[5.4] CodeGenerator → Generated Code
    ↓
[5.5] DiffGenerator → Unified Diff/Patch
    ↓
[5.6] /generate-patch Endpoint → User
```
