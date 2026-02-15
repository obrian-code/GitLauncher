import subprocess
from pathlib import Path

def run(cmd, cwd=None):
    """Ejecuta un comando y muestra salida."""
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True)
    if result.returncode != 0:
        print(f"[❌] Comando falló: {' '.join(cmd)}")
    return result.returncode == 0

def ask_input(prompt, default=None):
    """Pregunta y devuelve la respuesta."""
    if default:
        resp = input(f"{prompt} [{default}]: ").strip()
        return resp if resp else default
    else:
        return input(f"{prompt}: ").strip()

def setup_git():
    print("=== GitHub Auto Setup ===\n")

    # ------------------------------
    # Datos del usuario
    # ------------------------------
    github_user = ask_input("GitHub username")
    github_email = ask_input("GitHub email")
    github_token = ask_input("GitHub personal access token (opcional, deja vacío si ya guardaste)")
    
    # ------------------------------
    # Path del proyecto y repo
    # ------------------------------
    project_path = Path(ask_input("Ruta del proyecto (local)"))
    github_repo_url = ask_input("URL del repositorio GitHub (HTTPS)")

    # ------------------------------
    # Configuración global de Git
    # ------------------------------
    run(["git", "config", "--global", "user.name", github_user])
    run(["git", "config", "--global", "user.email", github_email])

    # ------------------------------
    # Inicializar repo local
    # ------------------------------
    if not project_path.exists():
        project_path.mkdir(parents=True)
    if not (project_path / ".git").exists():
        run(["git", "init"], cwd=project_path)

    # ------------------------------
    # Commit inicial
    # ------------------------------
    run(["git", "add", "."], cwd=project_path)
    run(["git", "commit", "-m", "initial commit 🚀"], cwd=project_path)

    # ------------------------------
    # Configurar remoto
    # ------------------------------
    if github_token:
        # Token en la URL HTTPS
        token_url = github_repo_url.replace("https://", f"https://{github_token}@")
    else:
        token_url = github_repo_url

    # Remoto
    remotes = subprocess.run(["git", "remote"], cwd=project_path, capture_output=True, text=True)
    if "origin" in remotes.stdout:
        run(["git", "remote", "remove", "origin"], cwd=project_path)
    run(["git", "remote", "add", "origin", token_url], cwd=project_path)

    # ------------------------------
    # Rama principal y push
    # ------------------------------
    run(["git", "branch", "-M", "main"], cwd=project_path)
    run(["git", "push", "-u", "origin", "main"], cwd=project_path)

    print("\n✅ Todo listo. Proyecto subido a GitHub!")

if __name__ == "__main__":
    setup_git()
