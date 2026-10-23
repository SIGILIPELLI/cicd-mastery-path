import subprocess
from pathfilter import affected, glob_to_regex, changed_files
P = {"api": ["services/api/**", "libs/common/**"], "web": ["services/web/**", "libs/common/**"], "docs": ["docs/**"]}
G = [".github/workflows/**", "pyproject.toml", "Makefile"]
def test_single_project(): assert affected(["services/api/app/main.py"], P, G) == ["api"]
def test_shared_lib_affects_dependents(): assert affected(["libs/common/util.py"], P, G) == ["api", "web"]
def test_global_file_affects_all(): assert affected(["Makefile"], P, G) == ["api", "docs", "web"]
def test_workflow_change_affects_all(): assert affected([".github/workflows/ci.yml"], P, G) == ["api", "docs", "web"]
def test_unmatched_change_affects_none(): assert affected(["README.md"], P, G) == []
def test_double_star_depth(): assert glob_to_regex("a/**/c.txt").match("a/c.txt") and glob_to_regex("a/**/c.txt").match("a/b/x/c.txt")
def test_single_star_does_not_cross_dirs(): assert glob_to_regex("src/*.py").match("src/a.py") and not glob_to_regex("src/*.py").match("src/sub/a.py")
def test_regex_metacharacters_escaped(): assert glob_to_regex("a+b.txt").match("a+b.txt") and not glob_to_regex("a+b.txt").match("aab.txt")
def test_git_diff_integration(tmp_path):
    run = lambda *a: subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)
    run("git", "init", "-q", "-b", "main"); run("git", "config", "user.email", "a@b.c"); run("git", "config", "user.name", "t")
    (tmp_path / "services/api").mkdir(parents=True); (tmp_path / "services/web").mkdir(parents=True)
    (tmp_path / "services/api/a.py").write_text("1"); (tmp_path / "services/web/w.py").write_text("1"); run("git", "add", "-A"); run("git", "commit", "-qm", "base")
    run("git", "checkout", "-q", "-b", "feature"); (tmp_path / "services/web/w.py").write_text("2"); run("git", "commit", "-qam", "change web")
    files = changed_files("main", "feature", cwd=tmp_path); assert files == ["services/web/w.py"] and affected(files, P, G) == ["web"]
