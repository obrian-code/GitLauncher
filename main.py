from pathlib import Path
import subprocess
from getpass import getpass
import json
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.tree import Tree
from rich.markdown import Markdown
from cryptography.fernet import Fernet

console = Console()

CRED_FILE = Path.home() / ".git_auto_cli.json"
KEY_FILE = Path.home() / ".git_auto_cli.key"

CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor", "test",
    "chore", "perf", "ci", "build", "revert", "BREAKING CHANGE"
]

# ==============================
# Credenciales cifradas
# ==============================
def load_key():
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key

def encrypt_token(token):
    f = Fernet(load_key())
    return f.encrypt(token.encode()).decode()

def decrypt_token(enc):
    f = Fernet(load_key())
    return f.decrypt(enc.encode()).decode()

def save_credentials(username, email, token):
    data = {
        "username": username,
        "email": email,
        "token": encrypt_token(token) if token else ""
    }
    CRED_FILE.write_text(json.dumps(data))

def load_credentials():
    if CRED_FILE.exists():
        data = json.loads(CRED_FILE.read_text())
        if data.get("token"):
            data["token"] = decrypt_token(data["token"])
        return data
    return None

# ==============================
# Git helpers
# ==============================
def run(cmd, cwd=None, capture_output=False):
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture_output)
    if result.returncode != 0:
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
    return result.stdout.strip() if capture_output else result.returncode == 0

def has_changes(cwd):
    return bool(run(["git", "status", "--porcelain"], cwd=cwd, capture_output=True))

def remote_exists(cwd):
    remotes = run(["git", "remote"], cwd=cwd, capture_output=True)
    return "origin" in remotes

def push_branch(cwd):
    if not remote_exists(cwd):
        console.print("[yellow]No hay remoto configurado[/yellow]")
        return
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True)
    run(["git", "push", "-u", "origin", branch], cwd=cwd)

# ==============================
# Commit automático
# ==============================
def commit_changes(cwd):
    if not has_changes(cwd):
        console.print("[green]No hay cambios[/green]")
        return

    run(["git", "add", "."], cwd=cwd)

    commit_type = Prompt.ask("Tipo commit", choices=CONVENTIONAL_TYPES, default="feat")
    msg = Prompt.ask("Mensaje", default="Auto commit")

    run(["git", "commit", "-m", f"{commit_type}: {msg}"], cwd=cwd)

    if Confirm.ask("¿Hacer push?", default=True):
        push_branch(cwd)

# ==============================
# Gestión avanzada de commits
# ==============================
def list_commits(project_path):
    log = run(
        ["git", "log", "--oneline", "--graph", "--decorate", "-20"],
        cwd=project_path,
        capture_output=True
    )
    console.print(Panel(log or "No commits", title="Commits recientes"))

def delete_last_commit(project_path):
    console.print("1 Soft  2 Mixed  3 Hard")
    opt = Prompt.ask("Modo", choices=["1","2","3"])

    if opt == "1":
        run(["git", "reset", "--soft", "HEAD~1"], cwd=project_path)
    elif opt == "2":
        run(["git", "reset", "--mixed", "HEAD~1"], cwd=project_path)
    else:
        if Confirm.ask("⚠ Borrar cambios?", default=False):
            run(["git", "reset", "--hard", "HEAD~1"], cwd=project_path)

def delete_specific_commit(project_path):
    commit = Prompt.ask("Hash commit")

    console.print("1 Revert seguro")
    console.print("2 Rebase interactivo")
    opt = Prompt.ask("Modo", choices=["1","2"])

    if opt == "1":
        run(["git", "revert", commit], cwd=project_path)
    else:
        run(["git", "rebase", "-i", f"{commit}^"], cwd=project_path)

def git_commit_menu(project_path):
    while True:
        console.print(Panel.fit(
            "1 List commits\n"
            "2 Eliminar último commit\n"
            "3 Eliminar commit específico\n"
            "0 Volver"
        ))
        c = Prompt.ask("Opción")

        if c == "1":
            list_commits(project_path)
        elif c == "2":
            delete_last_commit(project_path)
        elif c == "3":
            delete_specific_commit(project_path)
        elif c == "0":
            break

# ==============================
# Branch menu
# ==============================
def git_branch_menu(project_path):
    while True:
        console.print(Panel.fit(
            "1 List branches\n"
            "2 Create branch\n"
            "3 Checkout\n"
            "4 Merge\n"
            "5 Delete branch\n"
            "0 Volver"
        ))
        c = Prompt.ask("Opción")

        if c == "1":
            run(["git", "branch", "--all"], cwd=project_path)
        elif c == "2":
            name = Prompt.ask("Nombre")
            run(["git", "branch", name], cwd=project_path)
        elif c == "3":
            name = Prompt.ask("Branch")
            run(["git", "checkout", name], cwd=project_path)
        elif c == "4":
            name = Prompt.ask("Merge branch")
            run(["git", "merge", name], cwd=project_path)
        elif c == "5":
            name = Prompt.ask("Delete branch")
            run(["git", "branch", "-d", name], cwd=project_path)
        elif c == "0":
            break

# ==============================
# Setup proyecto
# ==============================
def setup_git():
    path = Path(Prompt.ask("Project path")).expanduser()

    if not path.exists():
        if Confirm.ask("Crear carpeta?", default=True):
            path.mkdir(parents=True)
        else:
            exit()

    if not (path / ".git").exists():
        run(["git", "init"], cwd=path)

    return path

# ==============================
# Main
# ==============================
def main():
    console.print(Panel.fit("🚀 Git Auto CLI"))

    project = setup_git()

    while True:
        console.print(Panel.fit(
            "1 Commit cambios\n"
            "2 Gestionar ramas\n"
            "3 Gestionar commits\n"
            "0 Salir"
        ))

        opt = Prompt.ask("Opción")

        if opt == "1":
            commit_changes(project)
        elif opt == "2":
            git_branch_menu(project)
        elif opt == "3":
            git_commit_menu(project)
        elif opt == "0":
            break

if __name__ == "__main__":
    main()
