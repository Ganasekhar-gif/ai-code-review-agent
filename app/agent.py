import os
import json
import re
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

from review import stream_review
from qna import prepare_qna_inputs

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# -------------------------------
# LLM Setup (Groq LLaMA3)
# -------------------------------
def get_llm(model_id: str = "llama3-8b-8192", temperature: float = 0, max_tokens: int = 2048):
    if not GROQ_API_KEY:
        raise ValueError("Missing GROQ_API_KEY in .env")
    return ChatGroq(
        model_name=model_id,
        groq_api_key=GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def call_llm(prompt: str, model_id: str = "llama3-8b-8192") -> str:
    llm = get_llm(model_id=model_id)
    try:
        msg = llm.invoke([
            {"role": "system", "content": "You are an expert software assistant. Answer only from the given context."},
            {"role": "user", "content": prompt}
        ])
        print("\n[DEBUG] Raw LLM response:", msg)
        return getattr(msg, "content", str(msg))
    except Exception as e:
        import traceback
        print("\n[ERROR] Exception during LLM call:")
        traceback.print_exc()
        return f"ERROR: {e}"


# -------------------------------
# Generic agent prompt (kept as-is)
# -------------------------------
AGENT_PROMPT = """
You are an AI assistant managing two tools:

1) QNA Tool: For documentation/setup/how-to queries.
   Input: query + relevant context chunks.
   Output: a clear natural language answer.

2) Review Tool: For code patch reviews.
   Input: linter results + diff snippet.
   Output: JSON with keys: summary, issues, suggested_fixes, confidence, green_signal.

Decide based on the user request which tool to call.
Always output the final answer (natural language or JSON as required).
If the answer is not in the context, reply with:
I cannot find relevant information in the repo context.

User request: {request}
Tool inputs: {tool_inputs}
"""

# -------------------------------
# Reviewer: Summarization helpers
# -------------------------------
REVIEW_SUMMARY_SYSTEM = (
    "You are a senior code reviewer. You will receive raw tool output: "
    "git diff chunks, list of changed files, flake8 and pylint results, and (optionally) autofix outcomes. "
    "Produce a STRICT JSON object with keys:\n"
    " - summary: short natural-language summary\n"
    " - issues: array of objects {type: 'lint'|'bug'|'style'|'security'|'other', file, details, line_hint?}\n"
    " - suggested_fixes: array of strings with concrete actions\n"
    " - green_signal: boolean (true if safe to merge with no major issues)\n"
    " - confidence: one of 'low'|'medium'|'high'\n"
    "If no issues are found, issues should be an empty array and green_signal true.\n"
    "Do NOT include any backticks or commentary outside the JSON."
)

REVIEW_SUMMARY_USER_TEMPLATE = """Raw review events (JSON list): {events_json}"""


def summarize_review_events_with_llm(events: list, model_id: str = "llama3-8b-8192") -> dict:
    """Ask the LLM to produce a single structured summary JSON from streamed review events."""
    llm = get_llm(model_id=model_id)
    events_json = json.dumps(events, indent=2)

    msg = llm.invoke([
        {"role": "system", "content": REVIEW_SUMMARY_SYSTEM},
        {"role": "user", "content": REVIEW_SUMMARY_USER_TEMPLATE.format(events_json=events_json)}
    ])
    content = getattr(msg, "content", "{}")

    # Extract JSON robustly
    try:
        m = re.search(r'\{.*\}', content, re.S)
        if m:
            return json.loads(m.group(0))
        return json.loads(content)
    except Exception:
        return {
            "summary": "LLM summarization failed to parse. Returning raw content.",
            "issues": [],
            "suggested_fixes": [],
            "green_signal": False,
            "confidence": "low",
            "raw": content,
        }


def format_review_output(summary: dict, events: list, auto_fix: bool = False, suggestions_text: str | None = None) -> str:
    """Convert structured review JSON + raw events into a friendly, conversational explanation."""
    lines = []

    # Opening tone
    lines.append("📝 Here's what I found in your review:")
    lines.append(summary.get("summary", "I didn't get a clear summary this time."))
    lines.append("")

    # Issues
    issues = summary.get("issues", [])
    if issues:
        lines.append("⚠️ Issues that need your attention:")
        for i, issue in enumerate(issues, start=1):
            lines.append(
                f"{i}. [{issue.get('type', 'other').upper()}] "
                f"{issue.get('details')} (file: {issue.get('file', 'unknown')}, line: {issue.get('line_hint', '?')})"
            )
        lines.append("")
    else:
        lines.append("✅ I didn't spot any major issues — looks good to merge.")
        lines.append("")

    # Suggestions from summary (bullet-level)
    fixes = summary.get("suggested_fixes", [])
    if fixes:
        lines.append("💡 Quick suggestions:")
        for fix in fixes:
            lines.append(f"- {fix}")
        lines.append("")

    # LLM-powered concrete suggestions with code, only when not auto-fixing
    if (not auto_fix) and issues and suggestions_text:
        lines.append("🧩 Proposed improvements (with code):")
        lines.append(suggestions_text)
        lines.append("")

    # Auto-fix recap
    if auto_fix:
        applied = [e for e in events if e.get("type") == "autofix" and e.get("fixed")]
        if applied:
            lines.append("🤖 I went ahead and applied formatting fixes to these files:")
            for e in applied:
                lines.append(f"- {e['file']} ✅")
            lines.append("")

    # Post-fix diff
    diffs = [e for e in events if e.get("type") == "post_fix_diff"]
    if diffs:
        lines.append("📄 Changes after auto-fix (first 500 chars):")
        for d in diffs:
            snippet = d["diff"][:500]
            lines.append("```diff")
            lines.append(snippet)
            lines.append("```")
        lines.append("")

    # Closing verdict
    if summary.get("green_signal"):
        if auto_fix:
            lines.append("🟢 Final take: All set! Auto-fixes are applied — feel confident to commit and push.")
        else:
            lines.append("🟢 Final take: You're good to merge.")
    else:
        if auto_fix:
            lines.append("🟠 Final take: I applied auto-fixes, but a few items still need attention before merging.")
        else:
            lines.append("🔴 Final take: Let's address the above points before merging.")
            lines.append("")
            lines.append("What to do next:")
            if issues:
                for issue in issues:
                    file_name = issue.get('file', 'unknown')
                    line_hint = issue.get('line_hint')
                    if isinstance(line_hint, int) or (isinstance(line_hint, str) and line_hint.isdigit()):
                        lines.append(f"- Open {file_name}, go to line {line_hint}, and apply the suggested change.")
                    else:
                        lines.append(f"- Open {file_name} and apply the suggested change shown above.")
            else:
                lines.append("- Apply the suggested changes above.")

    return "\n".join(lines)


def generate_suggestions_from_events(summary: dict, events: list, model_id: str = "llama3-8b-8192") -> str:
    """Use the original diff and detected issues to propose specific code corrections.
    The LLM should output concise suggestions and corrected code blocks. If a file is large,
    focus on the impacted function or the minimal hunk that fixes the issue.
    """
    llm = get_llm(model_id=model_id)

    issues = summary.get("issues", [])
    original_diff = next((e.get("diff") for e in events if e.get("type") == "original_diff"), "")

    prompt = (
        "You are a senior code reviewer. I will give you issues (with file and line hints) and a git diff.\n"
        "Produce beginner-friendly, minimal fixes focused exactly on the broken lines.\n"
        "Strict format per issue:\n"
        "1) What is wrong (plain language, 1-2 sentences).\n"
        "2) Exact fix (the corrected line only, if possible).\n"
        "3) Corrected code block with ONLY the minimal snippet:\n"
        "   - If the issue is inside a function, include just that function or the smallest viable portion.\n"
        "   - If the issue is outside any function (e.g., a stray print), include just those corrected lines.\n"
        "Rules:\n"
        "- Do NOT include unrelated code.\n"
        "- Do NOT include any diff headers or markers like @@, +, -, or ---/+++.\n"
        "- Use a tiny fenced code block with the appropriate language tag (e.g., ```python).\n"
        "- If a line number is given, you may include 1-3 lines of context above/below.\n"
        "- Keep output concise and copy-pasteable.\n\n"
        f"Issues (JSON):\n{json.dumps(issues, indent=2)}\n\n"
        f"Git diff (for your reference):\n```diff\n{original_diff[:8000]}\n```\n\n"
        "Now provide the suggestions in the specified format."
    )

    try:
        msg = llm.invoke([
            {"role": "system", "content": "You are an expert reviewer. Respond with concise, helpful suggestions and code blocks only."},
            {"role": "user", "content": prompt}
        ])
        return getattr(msg, "content", str(msg))
    except Exception as e:
        return f"(Could not generate suggestions: {e})"


def run_code_review(repo_url: str, auto_fix: bool = False, staged: bool = False, model_id: str = "llama3-8b-8192"):
    """Execute the review tool, collect events, and produce an LLM summary.
    If auto_fix=True, stream_review will attempt autopep8 fixes and re-check.
    """
    events = list(stream_review(repo_url, auto_fix=auto_fix, staged=staged))
    summary = summarize_review_events_with_llm(events, model_id=model_id)

    # Generate suggestions only when auto-fix is off and issues exist
    issues = summary.get("issues", []) if isinstance(summary, dict) else []
    suggestions_text = None
    if (not auto_fix) and issues:
        suggestions_text = generate_suggestions_from_events(summary, events, model_id=model_id)

    human_readable = format_review_output(summary, events, auto_fix=auto_fix, suggestions_text=suggestions_text)
    return {"events": events, "summary": summary, "formatted": human_readable}


# -------------------------------
# Main Agent Runner (kept)
# -------------------------------
def run_agent(task_type: str, repo_url=None, query=None, auto_fix=False):
    if task_type == "review":
        tool_inputs = []
        for event in stream_review(repo_url, auto_fix=auto_fix):
            tool_inputs.append(event)
    elif task_type == "qna":
        tool_inputs = prepare_qna_inputs(repo_url, query)
    else:
        raise ValueError("Invalid task_type: must be 'qna' or 'review'")

    template = PromptTemplate(
        input_variables=["request", "tool_inputs"],
        template=AGENT_PROMPT
    )

    llm = get_llm()
    chain = LLMChain(llm=llm, prompt=template)

    response = chain.run(
        request=query if task_type == "qna" else "Review this patch",
        tool_inputs=json.dumps(tool_inputs, indent=2)
    )

    if task_type == "review":
        try:
            m = re.search(r'(\{.*\})', response, re.S)
            if m:
                return json.loads(m.group(1))
        except Exception:
            return {"raw": response}

    return response
