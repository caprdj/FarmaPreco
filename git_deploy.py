import subprocess
import os

git_exe = os.path.expanduser(r"~\AppData\Local\Programs\Git\cmd\git.exe")
if not os.path.exists(git_exe):
    git_exe = "git"

def run_git(args):
    cmd = [git_exe] + args
    print(f"Executando: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
    return res.returncode

# 1. git init
run_git(["init"])

# 2. git branch -M main
run_git(["branch", "-M", "main"])

# 3. git config
run_git(["config", "user.name", "Caroline Peixoto"])
run_git(["config", "user.email", "caprdj@users.noreply.github.com"])

# 4. git remote
run_git(["remote", "remove", "origin"])
run_git(["remote", "add", "origin", "https://github.com/caprdj/FarmaPreco.git"])
run_git(["remote", "-v"])

# 5. git add
run_git(["add", "."])

# 6. git status
run_git(["status", "--short"])

# 7. git commit
run_git(["commit", "-m", "feat: FarmaPreco - Portal web comparador de farmacias, OCR prints Droga Raia e app Flutter"])
