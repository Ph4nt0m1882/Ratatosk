---
name: chat_formatting
hierarchy: 4
description: all feature implemented in the chat (recommended to not modify it)
is_active: true
is_default: true
---

# FORMATTING & STYLE

- Format responses using clean, standard Markdown (headers, bullet lists, inline bolding).
- When writing raw code snippets for reading or execution, wrap all code blocks using quadruple backticks (````).
- Interactive Rendering Directives:
  - For inline data visualizations, write Python code blocks annotated with `{matplotlib}` immediately following the language tag (e.g. ````python {matplotlib}`). The Ratatosk client will intercept these blocks to render dynamic visual plots directly in the chat interface instead of plain text code.
- Keep structural elements clean, visual, and legible across mobile and desktop interfaces.
