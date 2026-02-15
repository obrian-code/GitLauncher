from pathlib import Path
import subprocess
from getpass import getpass
import json
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.markdown import Markdown
from cryptography.fernet import Fernet

console = Console()
CRED_FILE = Path.home() / ".git_auto_cli.json"
KEY_FILE = Path.home() / ".git_auto_cli.key"

# ==============================
# Manejo de credenciales cifradas
# ==============================
def load_key():
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    return key

def encrypt_token(token):
    key = load_key()
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(enc_token):
    key = load_key()
    f = Fernet(key)
    return f.decrypt(enc_token.encode()).decode()

def save_credentials(username, email, token):
    data = {"username": username, "email": email, "token": encrypt_token(token)}
    CRED_FILE.write_text(json.dumps(data))
    console.print(f"[green]✔ Credenciales guardadas en {CRED_FILE}[/green]")

def load_credentials():
    if CRED_FILE.exists():
        data = json.loads(CRED_FILE.read_text())
        data["token"] = decrypt_token(data["token"])
        return data
    return None

# ==============================
# Funciones Git
# ==============================
def run(cmd, cwd=None, capture_output=False):
    """Ejecuta comando Git y muestra salida"""
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture_output)
    if result.returncode != 0:
        if capture_output:
            console.print(f"[red]{result.stderr}[/red]")
        console.print(f"[red]❌ Comando falló: {' '.join(cmd)}[/red]")
    return result.stdout if capture_output else result.returncode == 0

def setup_git(project_path, github_repo_url):
    creds = load_credentials()
    if creds:
        github_user = creds["username"]
        github_email = creds["email"]
        github_token = creds["token"]
    else:
        github_user = Prompt.ask("GitHub username")
        github_email = Prompt.ask("GitHub email")
        github_token = getpass("GitHub personal access token: ")
        save_credentials(github_user, github_email, github_token)

    console.print(Panel(f"[bold]Configurando Git para {project_path}[/bold]", subtitle="Paso 1: Configuración global"))
    run(["git", "config", "--global", "user.name", github_user])
    run(["git", "config", "--global", "user.email", github_email])

    if not (project_path / ".git").exists():
        console.print(Panel("[bold yellow]Inicializando repositorio...[/bold yellow]"))
        run(["git", "init"], cwd=project_path)

    run(["git", "add", "."], cwd=project_path)
    run(["git", "commit", "-m", "Initial commit 🚀"], cwd=project_path)

    # Config remoto con token
    token_url = github_repo_url.replace("https://", f"https://{github_token}@")
    remotes = subprocess.run(["git", "remote"], cwd=project_path, capture_output=True, text=True)
    if "origin" in remotes.stdout:
        run(["git", "remote", "remove", "origin"], cwd=project_path)
    run(["git", "remote", "add", "origin", token_url], cwd=project_path)

    run(["git", "branch", "-M", "main"], cwd=project_path)

    # Intentar push y manejar error 403
    success = run(["git", "push", "-u", "origin", "main"], cwd=project_path)
    if not success:
        console.print("[red]❌ Push falló. Posiblemente token inválido o sin permisos.[/red]")
        if Confirm.ask("¿Deseas actualizar el token y reintentar?"):
            github_token = getpass("Nuevo GitHub personal access token: ")
            save_credentials(github_user, github_email, github_token)
            token_url = github_repo_url.replace("https://", f"https://{github_token}@")
            run(["git", "remote", "set-url", "origin", token_url], cwd=project_path)
            run(["git", "push", "-u", "origin", "main"], cwd=project_path)

    console.print(Panel("[green]✅ Repo inicializado y subido a GitHub[/green]", title="¡Listo!"))

# ==============================
# UI de ramas
# ==============================
def show_branch_tree(project_path):
    """Muestra árbol de ramas con último commit"""
    tree = Tree("[bold cyan]Git Branch Tree[/bold cyan]")
    branches = run(["git", "branch", "--all"], cwd=project_path, capture_output=True).splitlines()
    for branch in branches:
        branch_name = branch.strip().replace("* ", "")
        commit = run(["git", "log", "-1", "--pretty=format:%h %s", branch_name], cwd=project_path, capture_output=True)
        tree.add(f"[yellow]{branch_name}[/yellow]: {commit}")
    console.print(tree)

def show_commit_log(project_path):
    log = run(["git", "log", "--oneline", "--graph", "--all"], cwd=project_path, capture_output=True)
    console.print(Panel(Markdown(f"```git\n{log}\n```"), title="Commit Log"))

def git_branch_menu(project_path):
    while True:
        console.print(Panel.fit(
            "[bold yellow]Git Branch Manager[/bold yellow]\n"
            "1. List branches\n"
            "2. Create branch\n"
            "3. Checkout branch\n"
            "4. Merge branch\n"
            "5. Delete branch\n"
            "6. Revert commit\n"
            "7. Show commit tree\n"
            "8. Show log\n"
            "0. Exit"
        ))
        choice = Prompt.ask("Select option")
        if choice == "1":
            show_branch_tree(project_path)
        elif choice == "2":
            name = Prompt.ask("Branch name")
            run(["git", "branch", name], cwd=project_path)
        elif choice == "3":
            name = Prompt.ask("Branch to checkout")
            run(["git", "checkout", name], cwd=project_path)
        elif choice == "4":
            name = Prompt.ask("Branch to merge into current")
            run(["git", "merge", name], cwd=project_path)
        elif choice == "5":
            name = Prompt.ask("Branch to delete")
            run(["git", "branch", "-d", name], cwd=project_path)
        elif choice == "6":
            commit = Prompt.ask("Commit hash to revert")
            run(["git", "revert", commit], cwd=project_path)
        elif choice == "7":
            show_branch_tree(project_path)
        elif choice == "8":
            show_commit_log(project_path)
        elif choice == "0":
            break
        else:
            console.print("[red]Invalid option[/red]")

# ==============================
# Menú principal
# ==============================
def main():
    console.print(Panel.fit("[bold green]🚀 Git Auto CLI[/bold green]", subtitle="Automatiza Git desde la terminal"))
    project_path = Path(Prompt.ask("Project path (local)")).resolve()
    github_repo_url = Prompt.ask("GitHub repo URL (HTTPS)")

    setup_git(project_path, github_repo_url)

    if Confirm.ask("¿Deseas gestionar ramas de forma interactiva?", default=True):
        git_branch_menu(project_path)

if __name__ == "__main__":
    main()
