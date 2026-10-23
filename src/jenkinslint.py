"""Structure checks for Declarative Jenkinsfiles. Text-based, with a brace tokenizer; it does not understand Groovy and cannot replace
Jenkins' own validator (`Jenkinsfile Linter` endpoint / `declarative-linter`). Findings are advisory."""
import re, sys

def strip_comments_and_strings(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"(^|[^:])//[^\n]*", r"\1", text)
    return re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", '""', text)

def balanced(text):
    depth = 0
    for ch in strip_comments_and_strings(text):
        depth += ch == "{"; depth -= ch == "}"
        if depth < 0: return False
    return depth == 0

def block_names(text):
    return re.findall(r"\b(pipeline|agent|options|environment|stages|stage|steps|post|parallel|when|always|failure|success|tools|triggers|parameters)\b\s*[({]", strip_comments_and_strings(text))

def lint(text):
    problems = []; clean = strip_comments_and_strings(text); raw_no_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if not balanced(text): problems.append("unbalanced braces: the file will not parse"); return problems
    names = block_names(text)
    if "pipeline" not in names: problems.append("no declarative 'pipeline { }' block (scripted pipelines need different checks)")
    if "agent" not in names and not re.search(r"\bagent\s+(any|none)\b", clean): problems.append("missing required 'agent' section")
    if "stages" not in names: problems.append("missing required 'stages' section")
    if names.count("stage") == 0: problems.append("no stage blocks")
    if re.search(r"\bagent\s+any\b", clean): problems.append("'agent any' lets the build run on any node; use labels so builds land on suitable, trusted agents")
    if "timeout(" not in clean: problems.append("no timeout() option: a hung build occupies an executor indefinitely")
    if "post" not in names: problems.append("no post { } section for always/failure handling (reports, notifications, cleanup)")
    if "disableConcurrentBuilds" not in clean: problems.append("concurrent builds are allowed; consider disableConcurrentBuilds() for jobs that deploy")
    if "buildDiscarder" not in clean: problems.append("no buildDiscarder: build history and artifacts will accumulate on the controller")
    for m in re.finditer(r"(password|passwd|secret|token|apikey|api_key)\s*[=:]\s*['\"][^'\"$]{6,}['\"]", raw_no_comments, re.I):
        problems.append(f"possible hard-coded credential: {m.group(0)[:40]}...; use credentials() / withCredentials")
    if re.search(r"sh\s+['\"][^'\"]*\$\{?[A-Za-z_]*(TOKEN|PASSWORD|SECRET)", raw_no_comments) : problems.append("secret interpolated into an sh string; single-quote the script and let the shell read the environment variable (avoids Groovy string interpolation leaks)")
    for m in re.finditer(r"stage\(\s*['\"]([^'\"]*)['\"]\s*\)\s*\{", raw_no_comments):
        if re.search(r"deploy|release|publish", m.group(1), re.I):
            body = raw_no_comments[m.end(): m.end() + 600]
            if not re.search(r"\bwhen\s*\{", body.split("stage(")[0]): problems.append(f"stage {m.group(1)!r} looks like a deployment but has no 'when' condition: it would run on every branch")
    return problems

if __name__ == "__main__":
    p = lint(open(sys.argv[1]).read()); print("\n".join(p) if p else "OK"); sys.exit(1 if p else 0)
