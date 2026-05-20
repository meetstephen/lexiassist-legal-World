"""One-shot script to split lexi/pages/tools.py.

The original `render_tools()` is a 1199-line monster with 7 tabs.
This script extracts each `with tab_X:` body into its own
`_render_tools_<short_name>()` function. The result:

  - render_tools() shrinks to ~30 lines (header + tab declaration +
    7 calls to sub-functions).
  - Each sub-function is at module top level, has a docstring, and
    contains exactly the original tab body, dedented by 4 spaces.

Behaviour is preserved byte-for-byte — only indentation changes.

Usage:
    python3 scripts/split_render_tools.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "lexi" / "pages" / "tools.py"

text = SRC.read_text()
lines = text.split("\n")

# 1. Locate render_tools() using AST (robust against multi-line strings
#    whose content lines start at column 0).
tree = ast.parse(text)
render_tools_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "render_tools":
        render_tools_node = node
        break
assert render_tools_node is not None, "Could not find render_tools()"

# AST line numbers are 1-based; lines list is 0-based.
render_tools_line = render_tools_node.lineno - 1
# end_lineno is the last line of the function body (Python 3.8+)
end_line = render_tools_node.end_lineno  # exclusive when used as range upper bound

# 2. Find each `with tab_X:` line at indent 4 inside render_tools
tab_pattern = re.compile(r"^    with (tab_\w+):\s*$")
tab_blocks: list[tuple[int, str]] = []
for i in range(render_tools_line + 1, end_line):
    m = tab_pattern.match(lines[i])
    if m:
        tab_blocks.append((i, m.group(1)))

# Each tab body runs from (start + 1) to the line BEFORE the next tab block.
# For the last tab, it runs to end_line.
tabs: list[dict] = []
for idx, (start, name) in enumerate(tab_blocks):
    body_start = start + 1
    body_end = tab_blocks[idx + 1][0] if idx + 1 < len(tab_blocks) else end_line
    # Trim trailing blank lines
    while body_end > body_start and lines[body_end - 1].strip() == "":
        body_end -= 1
    tabs.append({
        "name": name,
        "body_start": body_start,
        "body_end": body_end,
        "body_lines": lines[body_start:body_end],
        "tab_decl_line": start,
    })

# 3. Find the section comment that introduces each tab
def find_section_comment(line_idx: int) -> str:
    """Look back up to 3 lines for a `# ──` or `# ═══` line."""
    for j in range(line_idx - 1, max(line_idx - 4, 0), -1):
        line = lines[j].strip()
        if line.startswith("#") and ("──" in line or "═══" in line):
            return line.lstrip("#").strip(" ─═")
    return ""

for t in tabs:
    t["section"] = find_section_comment(t["tab_decl_line"])

# 4. Locate the `st.tabs(...)` call so we know where the preamble ends
tabs_call_start = None
for i in range(render_tools_line + 1, tab_blocks[0][0]):
    if "st.tabs(" in lines[i]:
        tabs_call_start = i
        break
assert tabs_call_start is not None

depth = 0
started = False
tabs_call_end = tabs_call_start
for i in range(tabs_call_start, tab_blocks[0][0]):
    for ch in lines[i]:
        if ch == "(":
            depth += 1
            started = True
        elif ch == ")":
            depth -= 1
    if started and depth == 0:
        tabs_call_end = i
        break

# 5. Build the new render_tools() body
preamble = lines[render_tools_line:tabs_call_end + 1]
new_orchestrator: list[str] = list(preamble)
new_orchestrator.append("")
for t in tabs:
    section = t["section"]
    short_name = t["name"].replace("tab_", "")
    if section:
        new_orchestrator.append(f"    # ── {section} ──")
    new_orchestrator.append(f"    with {t['name']}:")
    new_orchestrator.append(f"        _render_tools_{short_name}()")
    new_orchestrator.append("")

# 6. Build the sub-functions
subfuncs: list[str] = []
for t in tabs:
    short_name = t["name"].replace("tab_", "")
    fn_name = f"_render_tools_{short_name}"
    subfuncs.append("")
    subfuncs.append("")
    subfuncs.append(f"def {fn_name}() -> None:")
    if t["section"]:
        subfuncs.append(f'    """Render the "{t["section"]}" tab body of the Tools page."""')
    # Dedent body by 4 spaces (was at indent 8 inside `with tab_X:`)
    for line in t["body_lines"]:
        if line.startswith("        "):
            subfuncs.append(line[4:])
        elif line.strip() == "":
            subfuncs.append("")
        else:
            # Defensive — keep as is (shouldn't happen for well-formed code)
            subfuncs.append(line)

# 7. Assemble
header = lines[:render_tools_line]
new_content = "\n".join(header + new_orchestrator + subfuncs)
SRC.write_text(new_content)

print(f"Wrote {SRC.relative_to(REPO)}")
print(f"Original lines: {len(lines)}")
print(f"New lines:      {len(new_content.split(chr(10)))}")
print(f"Tabs extracted: {len(tabs)}")
for t in tabs:
    print(f"  - {t['name']:20s} → _render_tools_{t['name'].replace('tab_','')}() "
          f"({t['body_end'] - t['body_start']} lines: \"{t['section']}\")")
