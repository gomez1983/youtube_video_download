import os
import threading
import tkinter as tk
from tkinter import filedialog
from flask import Flask, request, jsonify, send_from_directory

import yt_dlp

app = Flask(__name__, static_folder=".", static_url_path="")

# Estado global de progresso por download_id
progress_data = {}
progress_lock = threading.Lock()


def make_progress_hook(download_id):
    def hook(d):
        with progress_lock:
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                progress_data[download_id] = {
                    "status": "downloading",
                    "percent": round(percent, 1),
                    "speed": round(speed / 1024, 1) if speed else 0,  # KB/s
                    "eta": eta,
                    "filename": d.get("filename", ""),
                }
            elif d["status"] == "finished":
                progress_data[download_id] = {
                    "status": "finished",
                    "percent": 100,
                    "filename": d.get("filename", ""),
                }
            elif d["status"] == "error":
                progress_data[download_id] = {
                    "status": "error",
                    "message": str(d.get("error", "Erro desconhecido")),
                }

    return hook


def find_ffmpeg():
    # Localiza o ffmpeg instalado via winget ou PATH
    candidates = [
        r"C:\Users\andre\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    # Tenta PATH do sistema
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"


def remux_to_mp4(input_path, ffmpeg_bin):
    # Converte mpegts para MP4 real com faststart
    base, _ = os.path.splitext(input_path)
    output_path = base + "_premiere.mp4"
    cmd = [
        ffmpeg_bin,
        "-i", input_path,
        "-c", "copy",
        "-movflags", "+faststart",
        "-y",
        output_path,
    ]
    import subprocess
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0 and os.path.isfile(output_path):
        return output_path
    return None


def run_download(download_id, url, output_dir, fmt, audio_only, container, browser_cookies, cookies_file, h264_compat):
    with progress_lock:
        progress_data[download_id] = {"status": "starting", "percent": 0}

    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [make_progress_hook(download_id)],
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": os.path.dirname(find_ffmpeg()),
    }

    # cookies_file tem prioridade sobre browser_cookies
    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    elif browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)

    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        if fmt == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = fmt

        if h264_compat:
            # Mantém o download normal — faz remux via ffmpeg depois
            pass
        else:
            # container define o formato do arquivo final (mp4, mkv, webm, original)
            if container != "original":
                ydl_opts["merge_output_format"] = container

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if h264_compat and not audio_only:
                # Localiza o arquivo baixado
                filename = ydl.prepare_filename(info)
                # yt-dlp pode ter mudado a extensão
                if not os.path.isfile(filename):
                    base, _ = os.path.splitext(filename)
                    for ext in [".mp4", ".mkv", ".webm", ".ts", ".mpeg"]:
                        if os.path.isfile(base + ext):
                            filename = base + ext
                            break

                with progress_lock:
                    progress_data[download_id] = {"status": "remuxing", "percent": 100}

                ffmpeg_bin = find_ffmpeg()
                output = remux_to_mp4(filename, ffmpeg_bin)

                if output:
                    with progress_lock:
                        progress_data[download_id] = {"status": "finished", "percent": 100, "filename": output}
                else:
                    with progress_lock:
                        progress_data[download_id] = {"status": "error", "message": "Remux falhou. O arquivo original foi mantido."}
    except Exception as e:
        with progress_lock:
            progress_data[download_id] = {"status": "error", "message": str(e)}


@app.route("/browse-file", methods=["POST"])
def browse_file():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", True)
    file = filedialog.askopenfilename(
        parent=root,
        title="Selecionar arquivo cookies.txt",
        filetypes=[("Arquivo de cookies", "*.txt"), ("Todos os arquivos", "*.*")]
    )
    root.destroy()

    if file:
        file = os.path.normpath(file)
        return jsonify({"file": file})
    return jsonify({"file": None})


@app.route("/browse-folder", methods=["POST"])
def browse_folder():
    # Abre a janela de seleção de pasta nativa do Windows via tkinter
    root = tk.Tk()
    root.withdraw()          # Oculta a janela principal do tkinter
    root.wm_attributes("-topmost", True)  # Garante que o diálogo fica na frente
    folder = filedialog.askdirectory(parent=root, title="Selecionar pasta de destino")
    root.destroy()

    if folder:
        # Converte separadores para o padrão do Windows
        folder = os.path.normpath(folder)
        return jsonify({"folder": folder})
    return jsonify({"folder": None})


@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url = data.get("url", "").strip()
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    browser_cookies = data.get("browser_cookies", "").strip()
    cookies_file = data.get("cookies_file", "").strip()

    if not url:
        return jsonify({"error": "URL não informada"}), 400

    if audio_only:
        ydl_fmt = "bestaudio/best"
    else:
        ydl_fmt = "bestvideo+bestaudio/best" if fmt == "best" else fmt

    ydl_opts = {
        "format": ydl_fmt,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ffmpeg_location": os.path.dirname(find_ffmpeg()),
    }

    # cookies_file tem prioridade sobre browser_cookies
    if cookies_file and os.path.isfile(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    elif browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            duration = info.get("duration", 0)

            # Soma o tamanho de todos os formatos selecionados
            requested = info.get("requested_formats") or [info]
            total_bytes = 0
            approximate = False
            for f in requested:
                b = f.get("filesize") or f.get("filesize_approx")
                if b:
                    total_bytes += b
                    if not f.get("filesize"):
                        approximate = True

            return jsonify({
                "title": title,
                "duration": duration,
                "filesize": total_bytes,
                "approximate": approximate,
                "thumbnail": info.get("thumbnail", ""),
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/download", methods=["POST"])
def start_download():
    data = request.get_json()
    url = data.get("url", "").strip()
    output_dir = data.get("output_dir", "").strip() or os.path.expanduser("~/Downloads")
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    container = data.get("container", "mp4")
    browser_cookies = data.get("browser_cookies", "").strip()
    cookies_file = data.get("cookies_file", "").strip()
    h264_compat = data.get("h264_compat", False)

    if not url:
        return jsonify({"error": "URL não informada"}), 400

    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return jsonify({"error": f"Diretório inválido: {e}"}), 400

    import uuid
    download_id = str(uuid.uuid4())

    thread = threading.Thread(
        target=run_download,
        args=(download_id, url, output_dir, fmt, audio_only, container, browser_cookies, cookies_file, h264_compat),
        daemon=True,
    )
    thread.start()

    return jsonify({"download_id": download_id})


@app.route("/progress/<download_id>")
def get_progress(download_id):
    with progress_lock:
        data = progress_data.get(download_id, {"status": "not_found"})
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
