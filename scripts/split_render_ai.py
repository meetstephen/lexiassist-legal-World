"""Split the Display Response section out of render_ai() into a sub-function."""
import ast
from pathlib import Path

REPO = Path(".")
SRC = REPO / "lexi" / "pages" / "ai.py"

text = SRC.read_text()
lines = text.split("\n")

# Find render_ai using AST
tree = ast.parse(text)
render_ai_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "render_ai":
        render_ai_node = node
        break
assert render_ai_node is not None

render_ai_start = render_ai_node.lineno - 1  # 0-based
render_ai_end = render_ai_node.end_lineno     # exclusive

# The "Display Response" section starts at the comment "# ── Display Response ──"
display_start = None
for i in range(render_ai_start, render_ai_end):
    if "# ── Display Response ──" in lines[i]:
        display_start = i
        break
assert display_start is not None, "Could not find Display Response section"

# It runs to the end of render_ai
display_end = render_ai_end

# Extract the body (lines display_start to display_end-1)
display_lines = lines[display_start:display_end]

# Replace in render_ai with a call to the sub-function
# The display section is at indent 4
replacement = [
    "    # ── Display Response (extracted) ──",
    "    _render_ai_response(mode)",
]

# Build new file
new_lines = (
    lines[:display_start]
    + replacement
    + ["", ""]  # blank lines after render_ai
)

# Build the sub-function
subfunc = [
    "",
    "",
    "def _render_ai_response(mode: str) -> None:",
    '    """Render the AI response display: confidence panel, citation audit,',
    '    structured output, case strength meter, follow-up, exports, save-to-case."""',
]

# Dedent display_lines by 0 (they're already at indent 4 which is correct
# for a function body — BUT they're at indent 4 inside render_ai which means
# they'll be at indent 4 in the new function too — perfect, no change needed)
for line in display_lines:
    subfunc.append(line)

new_content = "\n".join(new_lines + subfunc)
SRC.write_text(new_content)

print(f"Original: {len(lines)} lines")
print(f"New:      {len(new_content.split(chr(10)))} lines")
print(f"Extracted: lines {display_start+1}-{display_end} ({display_end - display_start} lines)")
print(f"render_ai() now ends at line {len(new_lines)}")
