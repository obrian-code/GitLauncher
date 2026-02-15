from pathlib import Path
import subprocess
from getpass import getpass
import json
import os
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.tree import Tree
from rich.markdown import Markdown
from cryptography.fernet import Fernet

console = Console()

CRED_FILE = Path.home() / ".git_auto_cli.json"
KEY_FILE = Path.home() / ".git_auto_cli.key"

PROJECTS_FILE = Path.home() / ".git_helper_projects.json"

CONVENTIONAL_TYPES = [
    "feat", "fix", "docs", "style", "refactor", "test",
    "chore", "perf", "ci", "build", "revert", "BREAKING CHANGE"
]

APP_TITLE = "Git Auto CLI"
PRIMARY = "bold cyan"
SUCCESS = "bold green"
WARNING = "bold yellow"
ERROR = "bold red"

def header(text):
    console.print(Panel.fit(text, style=PRIMARY))

def success(msg):
    console.print(f"[{{SUCCESS}}]✔ {{msg}}[/{{SUCCESS}}]")

def warn(msg):
    console.print(f"[{{WARNING}}]⚠ {{msg}}[/{{WARNING}}]")

def error(msg):
    console.print(f"[{{ERROR}}]✖ {{msg}}[/{{ERROR}}]")

def divider():
    console.rule(style="grey50")

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

# ============================================================
# GUARDAR Y CARGAR PROYECTOS
# ============================================================

def load_projects():
    if PROJECTS_FILE.exists():
        return json.loads(PROJECTS_FILE.read_text())
    return []

def git_exists(path):
    return os.path.exists(os.path.join(path, ".git"))

def save_project(path):
    projects = load_projects()
    path_str = str(Path(path).resolve())

    if path_str not in projects:
        projects.append(path_str)
        PROJECTS_FILE.write_text(json.dumps(projects, indent=2))


def choose_project():
    projects = load_projects()

    if not projects:
        console.print("[yellow]No hay proyectos guardados[/yellow]")
        return None

    console.print(Panel("[bold green]Proyectos guardados:[/bold green]"))

    for i, p in enumerate(projects, 1):
        console.print(f"[green]{i}[/green] → {p}")

    idx = Prompt.ask(
        "Elige número o ENTER para usar carpeta actual",
        default=""
    )

    if idx.isdigit():
        idx = int(idx)
        if 1 <= idx <= len(projects):
            return Path(projects[idx - 1])

    return None



# ============================================================
# INICIALIZAR PROYECTO
# ============================================================

def init_git(project_path):
    console.print("Inicializando Git...")
    run(["git", "init"], cwd=project_path)

    url = Prompt.ask("URL repo remoto (opcional)", default="")
    if url:
        run(["git", "remote", "add", "origin", url], cwd=project_path)

    run(["git", "add", "."], cwd=project_path)
    run(["git", "commit", "-m", "commit inicial"], cwd=project_path)

    if url:
        push = Prompt.ask("¿Hacer push inicial?", choices=["s","n"], default="s")
        if push == "s":
            run(["git", "push", "-u", "origin", "main"], cwd=project_path)

    save_project(project_path)

# ==============================
# Commit automático
# ==============================
def commit_changes(cwd):
    if not has_changes(cwd):
        console.print("[bold yellow]Error:[/bold yellow] [red]No hay cambios para hacer commit.[/red]")
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


def squash_commits(project_path):
    n = Prompt.ask("¿Cuántos commits juntar?", default="2")
    run(["git", "rebase", "-i", f"HEAD~{n}"], cwd=project_path)


def edit_commit_message(project_path):
    commit = Prompt.ask("Hash commit")
    run(["git", "rebase", "-i", f"{commit}^"], cwd=project_path)


def cherry_pick_commit(project_path):
    commit = Prompt.ask("Hash commit")
    run(["git", "cherry-pick", commit], cwd=project_path)


def show_diff_visual(project_path):
    console.print("1 Cambios actuales")
    console.print("2 Commit específico")
    opt = Prompt.ask("Opción", choices=["1","2"])

    if opt == "1":
        run(["git", "diff"], cwd=project_path)
    else:
        commit = Prompt.ask("Hash")
        run(["git", "show", commit], cwd=project_path)


def search_commit_by_file(project_path):
    file = Prompt.ask("Nombre archivo")
    run(["git", "log", "--oneline", "--", file], cwd=project_path)

# ============================================================
# MENU COMMITS
# ============================================================

def git_commit_menu(project_path):
    while True:
        console.print(Panel.fit(
            "1 List commits\n"
            "2 Eliminar último commit\n"
            "3 Eliminar commit específico\n"
            "4 Squash commits\n"
            "5 Editar mensaje commit\n"
            "6 Cherry-pick commit\n"
            "7 Ver diff visual\n"
            "8 Buscar commits por archivo\n"
            "0 Volver"
        ))

        c = Prompt.ask("Opción")

        if c == "1": list_commits(project_path)
        elif c == "2": delete_last_commit(project_path)
        elif c == "3": delete_specific_commit(project_path)
        elif c == "4": squash_commits(project_path)
        elif c == "5": edit_commit_message(project_path)
        elif c == "6": cherry_pick_commit(project_path)
        elif c == "7": show_diff_visual(project_path)
        elif c == "8": search_commit_by_file(project_path)
        elif c == "0": break

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

    if not git_exists(path):
        run(["git", "init"], cwd=path)

    save_project(path)
    return path


# ==============================
# Main
# ==============================
def main():
    console.print("[bold magenta]🚀 Git Auto CLI - Bienvenido![/bold magenta]")
    console.print("[cyan]Por favor, elige una opción del menú a continuación:[/cyan]")

    # Elegir proyecto guardado
    project_path = choose_project()

    if project_path is None:
        console.print("[cyan]Usando carpeta actual o creando nueva[/cyan]")
        project_path = setup_git()
    else:
        console.print(f"[green]Proyecto seleccionado:[/green] {project_path}")

    if not git_exists(project_path):
        init_git(project_path)

    while True:
        console.print(Panel.fit(
            "[bold cyan]1 Commit cambios[/bold cyan]\n"
            "[bold cyan]2 Gestionar ramas[/bold cyan]\n"
            "[bold cyan]3 Gestionar commits[/bold cyan]\n"
            "[bold red]0 Salir[/bold red]"
        ))

        opt = Prompt.ask("Opción")

        if opt == "1":
            commit_changes(project_path)
        elif opt == "2":
            git_branch_menu(project_path)
        elif opt == "3":
            git_commit_menu(project_path)
        elif opt == "0":
            break


if __name__ == "__main__":
    main()
