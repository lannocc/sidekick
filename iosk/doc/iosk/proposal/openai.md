# Proposal: OpenAI-Optimized Prompt Construction for IOSK

Status: Proposed

This document proposes targeted changes to IOSK’s prompt construction, section delineation, and bank phrasing so OpenAI models (gpt‑4o, gpt‑4o‑mini, gpt‑5) behave as reliably as Gemini models in our environment. It includes rationale, concrete templates, recommended bank rewrites, device‑specific pre/postambles, and an incremental rollout plan.

References
- Current “full constructed” prompt example: `./google-google-269-2-7.prompt`
- Current construction flow (chat): preamble → BANKS → chat history → postamble → “[user pwd] >> ”
- Current OpenAI call path: `src/iosk/dev/openai.py` sends one “user” message with the entire prompt string

---

## 1) Executive summary

OpenAI chat models adhere more strongly to role separation (system vs user) and to concise, explicit “contracts” (“You must do exactly one thing”) than Gemini. IOSK currently sends a single giant user message that blends instructions, banks, and history. Gemini tolerates that; OpenAI often under‑weights instructions or blends modes (chat + command + code). To improve OpenAI behavior without breaking Google behavior:

- Introduce device‑specific pre/postambles tailored to OpenAI (short, imperative, explicit)
- Delineate sections using unambiguous XML‑style tags rather than markdown prose
- Move rules and “output contract” to a dedicated SYSTEM segment (top) and repeat the key constraints at the end
- Rewrite bank phrasing to be concise, imperative, and free of narrative voice
- Tighten the history window and push “what to do now” into a TASK block, last
- For OpenAI calls, prefer roleful messages (system + user) and add stop sequences; if that’s not yet implemented, emulate the same structure in a single string with strong markers

---

## 2) Why OpenAI currently struggles (diagnosis)

Logical reasons tied to model behavior:
- Role weighting: OpenAI models prioritize “system” strongly, but IOSK provides everything as one “user” message. Result: diluted instruction salience and more “chatty” drift.
- Conflicting voices: Banks and preambles that speak in first‑person narrative (“I shall…”, “They call me…”) prime generative/storytelling behavior over tool‑use behavior.
- Instruction locality: Long history plus a long preamble yields instruction loss. OpenAI typically follows the last explicit, authoritative constraints best—ours are interleaved.
- Section ambiguity: Markdown headings (“=== … ===”) and mixed paragraphs are harder for OpenAI to parse as strict policy. XML‑style tags are more robust for policy/section separation.
- Output contract: OpenAI needs crisp, explicit “do exactly one of X/Y/Z” with examples and negative examples; current text hints at rules but is verbose and embedded.
- No stop sequences / temperature defaults: Without stop tokens and tight constraints, models are prone to keep going (e.g., add commentary after a $ command or after a code block).

---

## 3) Design principles for OpenAI prompts

- System-first: Put the minimal, non‑negotiable rules at the top as a SYSTEM block (or as the first lines of the single prompt string).
- Short, declarative, testable: Use imperative bullets, avoid narrative, minimize hedging. Make it easy to enforce: “Do exactly one. Never do both.”
- Strong segmentation: Use XML‑style tags for preamble, memory, history, task, and output contract.
- Recency > volume: Keep the history succinct. Summarize if needed. End with TASK and OUTPUT_CONTRACT.
- Redundancy where it matters: Repeat the “one action per turn” rule at the end.
- Defensive formatting: Remove needless fenced code examples from preambles and banks (these can trigger code output).
- Model hints: Provide stop sequences and low temperature for OpenAI calls.

---

## 4) Proposed file additions

Introduce OpenAI‑specific pre/postamble files (parallel to chat/ask variants):

- `/etc/openai/preamble` (chat)
- `/etc/openai/postamble` (chat)
- `/etc/ask/openai-preamble` (ask)
- `/etc/ask/openai-postamble` (ask)

These should be concise, imperative, and device‑specific. See Appendix A for drafts.

---

## 5) Sectioning and tags (for both one-string and roleful variants)

Even if you continue to send a single prompt string, switch to XML‑style tags to make structure and policy unambiguous:
```
<SYSTEM>
- You are an IOSK agent operating in a terminal-like environment.
- On each turn you must choose exactly one of:
  1) CHAT: write a plain chat reply to other users (no leading "$", no code fences).
  2) CMD: output exactly one line that begins with "$ " (a single command to run). No extra text.
  3) CODE: output exactly one fenced markdown code block (```lang ... ```), and nothing else.
- Never combine modes. Never add commentary before/after CMD or CODE.
- Prefer brevity. Do not restate context.
</SYSTEM>

<MEMORY>
[bullet rules distilled from banks; see §7]
</MEMORY>

<HISTORY>
[the recent chat excerpt only; keep it compact—or summarize older parts]
</HISTORY>

<TASK>
[the immediate question or the current shell prompt line, e.g., “[user /path] >> ”]
</TASK>

<OUTPUT_CONTRACT>
- Choose exactly one: CHAT or CMD or CODE.
- If CMD: output one line starting with "$ " and nothing else.
- If CODE: one fenced block only, no extra text. No “Here is…”.
</OUTPUT_CONTRACT>
```

Notes
- For Gemini you can keep your current style; for OpenAI prefer the above stronger tags. If you want a single cross‑vendor format, these tags also work well with Gemini.
- Place TASK and OUTPUT_CONTRACT at the end. OpenAI tends to obey the final instructions most.

---

## 6) Message shaping specifically for OpenAI (roleful)

When feasible, change `src/iosk/dev/openai.py` to send multi‑message chat with roles:

- system: contents of SYSTEM + condensed MEMORY + the OUTPUT_CONTRACT
- user: minimal HISTORY + TASK (the “question/prompt cursor”)

This preserves your kernel’s single string assembly pattern while allowing OpenAI to obey system constraints better.

If you are not ready to change code paths, keep a single string but retain the tag structure and repeat the OUTPUT_CONTRACT at the end.

---

## 7) Bank (skrip) phrasing guidelines (OpenAI‑friendly)

Rewrite bank files that are loaded into “MEMORY” to be:
- Imperative, neutral voice; avoid first‑person narratives and lore.
- Short bullet points; avoid long prose or example code fences.
- No conflicting guidance; remove redundancy with system rules.
- Explicit, operational; e.g., “When generating code, emit one fenced block only.”

Example conversions

Current (narrative; not ideal for OpenAI)
- persona/aged_professor: multi‑paragraph backstory
- timing/…: long descriptions of cadence
- instinct/gut: “I shall continue; I go with my gut instinct.”

Proposed (operational, bulletized)
- persona/aged_professor → “Style preference: terse, precise, analytical; avoid metaphors. Prioritize correctness over flourish.”
- timing/1min_turbo → “Engagement cadence: bias for issuing a CMD when there is an actionable step; otherwise stay quiet.”
- instinct/gut → remove from OpenAI memory or replace with “Default to explicit reasoning only when necessary; otherwise act.”

Bank template

```
- Role: <concise role definition>
- Tone: <one line, e.g., “formal, concise”>
- Output rules (augment, do not conflict with SYSTEM):
  - Prefer CMD when a single system command advances the task.
  - Prefer CODE when a self-contained artifact is requested.
  - Otherwise, respond with brief CHAT.
- Prohibitions:
  - Do not mix CMD/CODE/CHAT.
  - Do not include “Here is…” or trailing commentary.
```

---

## 8) History management

OpenAI benefits from tighter context:
- Limit <HISTORY> to the most recent window (e.g., ~80–120 lines or a bytes budget).
- If older, insert a short summary at the top of <HISTORY> (e.g., “Earlier: X asked for Y; we produced Z.”) rather than raw lines.
- Keep the TASK last and prominent.

---

## 9) Output controls for OpenAI

When calling OpenAI (ask or chat):
- Set low temperature (e.g., 0.2–0.3) for determinism in tool‑use.
- Add stop sequences to prevent “spillover”:
  - For CMD: stop on “\n[” and “\n```”
  - For CODE: stop on a line that starts with “[” or another “```” after the closing fence
- Consider max_tokens appropriate to prevent overrun.

Example (conceptual)
- `stop`: ["\n[", "\n$ ", "\n```"] for CHAT; adjust per mode if you add mode detection upstream.

---

## 10) Example: transform the current Gemini‑style prompt for OpenAI

Given `./google-google-269-2-7.prompt` (large preamble, banks, help text, tree, etc.), build a trimmed OpenAI format:

```
<SYSTEM>
- You are an IOSK agent operating a terminal-like environment.
- On each turn choose exactly one: CHAT, CMD, or CODE.
- If CMD: output exactly one line beginning with "$ " and nothing else.
- If CODE: output exactly one fenced code block and nothing else.
- Never combine modes. Avoid meta commentary. Be brief.
</SYSTEM>

<MEMORY>
- Use IOSK commands only; one command per turn.
- Only you see command output; users see only CHAT.
- Prefer CMD when an actionable shell step exists; prefer CODE to produce files.
</MEMORY>

<HISTORY>
[Include only recent task-relevant lines, not the entire help + tree + prior welcome]
</HISTORY>

<TASK>
[google /home/google] >>  # (the last prompt, or a clarified task instruction)
</TASK>

<OUTPUT_CONTRACT>
- Choose exactly one: CHAT or CMD or CODE.
- No extra commentary before/after the chosen form.
</OUTPUT_CONTRACT>
```

This eliminates long generic “help” and “tree” dumps from the immediate context for OpenAI, replacing them with compact policy and the current action focus.

---

## 11) Changes for ask (one‑shot) with OpenAI

Add /etc/ask/openai-preamble and /etc/ask/openai-postamble that:
- Focus on “direct, concise answer” and the same OUTPUT_CONTRACT (if you still want the CMD/CODE discipline in one‑shot).
- If ask should always be CHAT (pure answer), simplify: set the contract to CHAT only and remove CMD/CODE rules for that path.

---

## 12) Rollout plan

Phase 1 (no kernel refactor required)
- Add new OpenAI‑specific pre/postambles (Appendix A).
- Switch to XML tags in constructed prompts for all devices; for Gemini this is harmless; for OpenAI it improves parsing.
- Rewrite/curate key bank files used by OpenAI agents into short, imperative bullets (Appendix B).

Phase 2 (device‑aware prompt shape; higher impact)
- In `src/iosk/dev/openai.py`, build messages with roles:
  - system = SYSTEM + condensed MEMORY + OUTPUT_CONTRACT
  - user = HISTORY + TASK
- Add `stop` and `temperature` settings for OpenAI calls.

Phase 3 (nice‑to‑have)
- Implement a history budget for OpenAI devices (bytes or token budget).
- Collect metrics: adherence (no mixed modes), token footprint, failure cases.

Success criteria
- >95% turns respect “one of CHAT/CMD/CODE”
- Reduced extraneous text before/after CMD/CODE
- Fewer instances of ignoring last instruction; fewer hallucinated steps

---

## Appendix A — Draft OpenAI pre/postambles

File: `/etc/openai/preamble`
```
#!/bin/skrip
<SYSTEM>
- You are an IOSK agent in a terminal-like environment.
- On each turn, choose exactly one output mode:
  1) CHAT: plain text to other users.
  2) CMD: one line starting with "$ " (a single shell command), no extra text.
  3) CODE: exactly one fenced code block, no extra text.
- Never combine modes. Be concise. Do not restate context.
</SYSTEM>
```

File: `/etc/openai/postamble`
```
#!/bin/skrip
<OUTPUT_CONTRACT>
- Choose exactly one mode: CHAT or CMD or CODE.
- If CMD: "$ <command>" only.
- If CODE: one fenced code block only.
- No commentary before or after.
</OUTPUT_CONTRACT>
```

File: `/etc/ask/openai-preamble`
```
#!/bin/skrip
<SYSTEM>
- One-shot request. Provide a direct and accurate answer.
- If the user requests a script or artifact, return exactly one fenced code block.
- Otherwise respond with concise CHAT. No extraneous text.
</SYSTEM>
```

File: `/etc/ask/openai-postamble`
```
#!/bin/skrip
<OUTPUT_CONTRACT>
- Prefer a single fenced code block for requested artifacts.
- Otherwise use concise CHAT.
- No prefaces or trailing commentary.
</OUTPUT_CONTRACT>
```

---

## Appendix B — Bank rewriting examples

Example: `bank/iosk/limitations` (trim to policy bullets for OpenAI)
```
#!/bin/skrip
- IOSK supports quotes, variable expansion, command substitution, redirection, and pipes.
- Only one command per turn (CMD) is allowed.
- Markdown code blocks are saved to files; if you output CODE, do not add commentary.
- Avoid diff blocks unless explicitly requested; prefer full files in a fenced block.
```

Example: `bank/iosk/skrip` (remove narrative; keep policy)
```
#!/bin/skrip
- Skrip files use lines with "$ " as commands; other lines are printed.
- Comments start with "#".
- When generating skrip content, emit it as a fenced code block with the correct language.
```

Example: persona/tone banks (convert to constraints)
```
#!/bin/skrip
- Tone: formal, concise, and direct. Avoid narrative flourish.
```

Remove or relocate extended creative personas for OpenAI agents unless explicitly needed; keep them out of default MEMORY for task‑oriented agents.

---

## Appendix C — Optional API tweaks for OpenAI

If you adjust code (future phase):
- In `openai.trip`: support `messages=[{"role":"system", "content": system_text}, {"role":"user","content": user_text}]`
- Provide `stop=["\n[", "\n```", "\n$ "]` and `temperature=0.2` (tune per mode)
- If you detect the intent is CMD or CODE (simple heuristic on last few actions), restrict stop sequences accordingly.

---

## FAQ

Q: Will these changes break Gemini?
- The XML‑style tags, shorter preambles, and explicit contracts are also fine for Gemini. Dedicated OpenAI pre/postambles are device‑scoped and won’t affect Google paths unless you explicitly switch.

Q: What if the agent still mixes CMD and CHAT?
- Strengthen the end‑of‑prompt OUTPUT_CONTRACT. Add a penalty loop (post‑processing) that rejects mixed output and asks the model to retry under a stricter contract (Phase 2+).

Q: Why remove narrative banks?
- They prime generative storytelling over tool use. For OpenAI, concise policy bullets produce better adherence and fewer “helper” phrases in outputs.

