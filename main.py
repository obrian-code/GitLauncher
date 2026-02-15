from pathlib import Path
import subprocess
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()

# ==============================
# Helper
# ==============================
def run(cmd, cwd=None, capture_output=False):
    console.print(f"[cyan]$ {' '.join(cmd)}[/cyan]")
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture_output)
    if r.returncode != 0 and r.stderr:
        console.print(f"[red]{r.stderr}[/red]")
    return r.stdout.strip() if capture_output else r.returncode == 0

# ==============================
# Commit básico
# ==============================
def commit_changes(path):
    run(["git","add","."], cwd=path)
    msg = Prompt.ask("Mensaje commit", default="update")
    run(["git","commit","-m",msg], cwd=path)

# ==============================
# Gestión avanzada commits
# ==============================
def list_commits(path):
    log = run(["git","log","--oneline","--graph","--decorate","-20"],cwd=path,capture_output=True)
    console.print(Panel(log or "Sin commits"))

def delete_last_commit(path):
    opt = Prompt.ask("1 soft 2 mixed 3 hard",choices=["1","2","3"])
    if opt=="1": run(["git","reset","--soft","HEAD~1"],cwd=path)
    if opt=="2": run(["git","reset","--mixed","HEAD~1"],cwd=path)
    if opt=="3" and Confirm.ask("Seguro?",default=False):
        run(["git","reset","--hard","HEAD~1"],cwd=path)

def delete_specific_commit(path):
    h = Prompt.ask("Hash commit")
    run(["git","revert",h],cwd=path)

def edit_commit_message(path):
    h = Prompt.ask("Hash commit")
    run(["git","rebase","-i",f"{h}^"],cwd=path)

def squash_commits(path):
    console.print("Se abrirá rebase interactivo")
    n = Prompt.ask("Cuantos commits juntar?",default="2")
    run(["git","rebase","-i",f"HEAD~{n}"],cwd=path)

def cherry_pick_commit(path):
    h = Prompt.ask("Hash commit a copiar")
    run(["git","cherry-pick",h],cwd=path)

def show_diff_visual(path):
    h = Prompt.ask("Hash commit (enter = último)",default="")
    if h:
        run(["git","show",h],cwd=path)
    else:
        run(["git","diff"],cwd=path)

def search_commit_by_file(path):
    file = Prompt.ask("Nombre archivo")
    run(["git","log","--oneline","--",file],cwd=path)

# ==============================
# Menú commits
# ==============================
def commit_menu(path):
    while True:
        console.print(Panel.fit(
            "1 List commits\n"
            "2 Delete last commit\n"
            "3 Delete specific commit\n"
            "4 Edit commit message\n"
            "5 Squash commits\n"
            "6 Cherry pick\n"
            "7 Ver diff\n"
            "8 Buscar commits por archivo\n"
            "0 Volver"
        ))

        c = Prompt.ask("Opción")

        if c=="1": list_commits(path)
        elif c=="2": delete_last_commit(path)
        elif c=="3": delete_specific_commit(path)
        elif c=="4": edit_commit_message(path)
        elif c=="5": squash_commits(path)
        elif c=="6": cherry_pick_commit(path)
        elif c=="7": show_diff_visual(path)
        elif c=="8": search_commit_by_file(path)
        elif c=="0": break

# ==============================
# Setup
# ==============================
def setup():
    p = Path(Prompt.ask("Project path")).expanduser()
    if not p.exists():
        if Confirm.ask("Crear carpeta?",default=True):
            p.mkdir(parents=True)
    if not (p/".git").exists():
        run(["git","init"],cwd=p)
    return p

# ==============================
# Main
# ==============================
def main():
    console.print(Panel.fit("🚀 Git Auto CLI PRO"))

    path = setup()

    while True:
        console.print(Panel.fit(
            "1 Commit cambios\n"
            "2 Gestion commits\n"
            "0 Salir"
        ))

        c = Prompt.ask("Opción")

        if c=="1": commit_changes(path)
        elif c=="2": commit_menu(path)
        elif c=="0": break

if __name__ == "__main__":
    main()
