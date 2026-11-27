#!/usr/bin/env python3
"""
Minimal Jira REST client for the jira-loop pipeline. Stdlib only, no
third-party dependencies, so it runs on any machine with python3.

Auth: reads JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN from the environment.
If they are not set, it looks for a KEY=VALUE file at (in order):
  ./.claude/jira-loop.env
  ./jira-loop.env
and loads it into the environment before proceeding.

JIRA_API_VERSION controls the comment/description API shape:
  "3" (default) -> Jira Cloud, comments use Atlassian Document Format (ADF)
  "2"           -> Jira Server / Data Center, comments are plain strings

Usage:
  jira_client.py env-check
  jira_client.py get <ISSUE-KEY>
  jira_client.py comment <ISSUE-KEY> (--text "..." | --file path.md)
  jira_client.py attach <ISSUE-KEY> <file-path> [<file-path> ...]
  jira_client.py transitions <ISSUE-KEY>
  jira_client.py transition <ISSUE-KEY> <transition-name>
"""
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

ENV_CANDIDATES = [
    os.path.join(".claude", "jira-loop.env"),
    "jira-loop.env",
]


def load_dotenv_if_needed():
    if os.environ.get("JIRA_BASE_URL") and os.environ.get("JIRA_EMAIL") and os.environ.get("JIRA_API_TOKEN"):
        return
    for path in ENV_CANDIDATES:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            return


def config():
    load_dotenv_if_needed()
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    api_version = os.environ.get("JIRA_API_VERSION", "3")
    missing = [n for n, v in [("JIRA_BASE_URL", base_url), ("JIRA_EMAIL", email), ("JIRA_API_TOKEN", token)] if not v]
    if missing:
        sys.stderr.write(
            "Missing required env vars: %s\n"
            "Set them in your shell, or create .claude/jira-loop.env "
            "(copy .claude/jira-loop.env.example) with:\n"
            "  JIRA_BASE_URL=https://yourcompany.atlassian.net\n"
            "  JIRA_EMAIL=you@company.com\n"
            "  JIRA_API_TOKEN=xxxx\n" % ", ".join(missing)
        )
        sys.exit(2)
    return base_url, email, token, api_version


def auth_header(email, token):
    raw = f"{email}:{token}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def request(method, url, email, token, data=None, headers=None, raw_body=False):
    hdrs = {"Authorization": auth_header(email, token), "Accept": "application/json"}
    body = None
    if data is not None:
        if raw_body:
            body = data
        else:
            body = json.dumps(data).encode("utf-8")
            hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {"raw": raw.decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")
        sys.stderr.write(f"Jira API error {e.code} on {method} {url}:\n{err_body}\n")
        sys.exit(1)


# ---------- ADF helpers ----------

def adf_text_from_doc(doc):
    """Flatten an Atlassian Document Format node tree into plain text."""
    if doc is None:
        return ""
    if isinstance(doc, str):
        return doc
    lines = []

    def walk(node):
        if not isinstance(node, dict):
            return
        ntype = node.get("type")
        if ntype == "text":
            lines.append(node.get("text", ""))
        elif ntype in ("paragraph", "heading"):
            for child in node.get("content", []) or []:
                walk(child)
            lines.append("\n")
        elif ntype == "codeBlock":
            lines.append("\n```\n")
            for child in node.get("content", []) or []:
                walk(child)
            lines.append("\n```\n")
        elif ntype in ("bulletList", "orderedList"):
            for child in node.get("content", []) or []:
                walk(child)
        elif ntype == "listItem":
            lines.append("- ")
            for child in node.get("content", []) or []:
                walk(child)
        else:
            for child in node.get("content", []) or []:
                walk(child)

    walk(doc)
    return "".join(lines).strip()


def text_to_adf(text):
    """Very small markdown-ish -> ADF converter: headings, bullet lists,
    fenced code blocks, and plain paragraphs. Good enough for the
    structured reports this pipeline generates."""
    content = []
    lines = text.splitlines()
    i = 0
    bullet_buf = []

    def flush_bullets():
        nonlocal bullet_buf
        if bullet_buf:
            content.append({
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": b}]}]}
                    for b in bullet_buf
                ],
            })
            bullet_buf = []

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_bullets()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            content.append({"type": "codeBlock", "content": [{"type": "text", "text": "\n".join(code_lines)}]})
            i += 1
            continue
        if line.startswith("#"):
            flush_bullets()
            level = min(len(line) - len(line.lstrip("#")), 6)
            heading_text = line.lstrip("#").strip()
            if heading_text:
                content.append({"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": heading_text}]})
            i += 1
            continue
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_buf.append(stripped[2:])
            i += 1
            continue
        flush_bullets()
        if stripped:
            content.append({"type": "paragraph", "content": [{"type": "text", "text": stripped}]})
        i += 1
    flush_bullets()
    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": text or " "}]}]
    return {"type": "doc", "version": 1, "content": content}


# ---------- commands ----------

def cmd_env_check(_args):
    base_url, email, _token, api_version = config()
    print(f"OK base_url={base_url} email={email} api_version={api_version}")


def cmd_get(args):
    base_url, email, token, _v = config()
    key = args[0]
    ac_field = os.environ.get("JIRA_ACCEPTANCE_CRITERIA_FIELD", "").strip()
    fields = "summary,description,status,issuetype,comment,labels,priority,parent"
    if ac_field:
        fields += f",{ac_field}"
    url = f"{base_url}/rest/api/3/issue/{key}?fields={fields}"
    data = request("GET", url, email, token)
    f = data.get("fields", {})
    description = f.get("description")
    description_text = adf_text_from_doc(description) if isinstance(description, dict) else (description or "")
    comments = []
    for c in (f.get("comment", {}) or {}).get("comments", []):
        body = c.get("body")
        body_text = adf_text_from_doc(body) if isinstance(body, dict) else (body or "")
        comments.append({"author": (c.get("author") or {}).get("displayName", "unknown"), "body": body_text})
    parent = f.get("parent")
    parent_out = None
    if parent:
        pf = parent.get("fields", {}) or {}
        parent_out = {"key": parent.get("key"), "summary": pf.get("summary")}
    acceptance_criteria = None
    if ac_field and ac_field in f and f.get(ac_field) is not None:
        raw_ac = f.get(ac_field)
        acceptance_criteria = adf_text_from_doc(raw_ac) if isinstance(raw_ac, dict) else str(raw_ac)
    out = {
        "key": data.get("key"),
        "summary": f.get("summary"),
        "description_text": description_text,
        "status": (f.get("status") or {}).get("name"),
        "issuetype": (f.get("issuetype") or {}).get("name"),
        "labels": f.get("labels", []),
        "priority": (f.get("priority") or {}).get("name"),
        "parent": parent_out,
        "acceptance_criteria": acceptance_criteria,
        "comments": comments,
        "url": f"{base_url}/browse/{key}",
    }
    print(json.dumps(out, indent=2))


def cmd_comment(args):
    base_url, email, token, api_version = config()
    key = args[0]
    text = None
    if "--text" in args:
        text = args[args.index("--text") + 1]
    elif "--file" in args:
        path = args[args.index("--file") + 1]
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    else:
        sys.stderr.write("comment requires --text \"...\" or --file path.md\n")
        sys.exit(2)

    if api_version == "2":
        url = f"{base_url}/rest/api/2/issue/{key}/comment"
        payload = {"body": text}
    else:
        url = f"{base_url}/rest/api/3/issue/{key}/comment"
        payload = {"body": text_to_adf(text)}
    request("POST", url, email, token, data=payload)
    print(f"Comment posted to {key}")


def multipart_body(file_paths):
    boundary = uuid.uuid4().hex
    parts = []
    for path in file_paths:
        filename = os.path.basename(path)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            data = fh.read()
        parts.append(
            (f"--{boundary}\r\n"
             f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
             f"Content-Type: {ctype}\r\n\r\n").encode("utf-8")
            + data + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)
    return body, boundary


def cmd_attach(args):
    base_url, email, token, _v = config()
    key = args[0]
    file_paths = args[1:]
    if not file_paths:
        sys.stderr.write("attach requires at least one file path\n")
        sys.exit(2)
    body, boundary = multipart_body(file_paths)
    url = f"{base_url}/rest/api/2/issue/{key}/attachments"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "X-Atlassian-Token": "no-check",
    }
    request("POST", url, email, token, data=body, headers=headers, raw_body=True)
    print(f"Attached {len(file_paths)} file(s) to {key}")


def cmd_transitions(args):
    base_url, email, token, _v = config()
    key = args[0]
    url = f"{base_url}/rest/api/3/issue/{key}/transitions"
    data = request("GET", url, email, token)
    for t in data.get("transitions", []):
        print(f"{t.get('id')}\t{t.get('name')}")


def cmd_transition(args):
    base_url, email, token, _v = config()
    key = args[0]
    target_name = args[1].lower()
    url = f"{base_url}/rest/api/3/issue/{key}/transitions"
    data = request("GET", url, email, token)
    match = next((t for t in data.get("transitions", []) if t.get("name", "").lower() == target_name), None)
    if not match:
        available = ", ".join(t.get("name", "") for t in data.get("transitions", []))
        sys.stderr.write(f"No transition named '{args[1]}'. Available: {available}\n")
        sys.exit(1)
    request("POST", url, email, token, data={"transition": {"id": match["id"]}})
    print(f"{key} transitioned to {match['name']}")


COMMANDS = {
    "env-check": cmd_env_check,
    "get": cmd_get,
    "comment": cmd_comment,
    "attach": cmd_attach,
    "transitions": cmd_transitions,
    "transition": cmd_transition,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.stderr.write(f"Usage: jira_client.py <{'|'.join(COMMANDS)}> ...\n")
        sys.exit(2)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
