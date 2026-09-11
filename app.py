import os
import re
import threading
import tkinter as tk
from tkinter import filedialog
from flask import Flask, request, jsonify, send_from_directory

import yt_dlp

app = Flask(__name__, static_folder=".", static_url_path="")

# Estado global de progresso por download_id
progress_data = {}
progress_lock = threading.Lock()


def make_progress_hook(download_id, is_playlist=False):
    def hook(d):
        with progress_lock:
            info = d.get("info_dict", {})
            p_index = info.get("playlist_index")
            p_count = info.get("playlist_count") or info.get("n_entries")
            video_title = info.get("title") or os.path.basename(d.get("filename", ""))

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
                    "is_playlist": is_playlist,
                    "playlist_index": p_index,
                    "playlist_count": p_count,
                    "video_title": video_title,
                }
            elif d["status"] == "finished":
                if not is_playlist:
                    progress_data[download_id] = {
                        "status": "finished",
                        "percent": 100,
                        "filename": d.get("filename", ""),
                        "is_playlist": False,
                    }
                else:
                    progress_data[download_id] = {
                        "status": "item_finished",
                        "percent": 100,
                        "filename": d.get("filename", ""),
                        "is_playlist": True,
                        "playlist_index": p_index,
                        "playlist_count": p_count,
                        "video_title": video_title,
                    }
            elif d["status"] == "error":
                progress_data[download_id] = {
                    "status": "error",
                    "message": str(d.get("error", "Erro desconhecido")),
                }

    return hook


def find_ffmpeg():
    import shutil
    import glob

    # Busca dinâmica em qualquer versão instalada via winget
    pattern = r"C:\Users\andre\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"
    matches = glob.glob(pattern, recursive=True)
    if matches:
        return matches[0]

    # Tenta PATH do sistema
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


class YDLLogger:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def debug(self, msg):
        pass

    def warning(self, msg):
        self.warnings.append(msg)

    def error(self, msg):
        clean = re.sub(r"\x1b\[[0-9;]*m", "", str(msg)).strip()
        self.errors.append(clean)


def clean_error_message(err_str):
    clean = re.sub(r"\x1b\[[0-9;]*m", "", str(err_str)).strip()
    if "Join this channel to get access to members-only content" in clean:
        return "Vídeo exclusivo para membros do canal. Se você for membro, selecione seu navegador em 'Cookies do navegador' ou importe um arquivo cookies.txt."
    if "Unable to extract universal data for rehydration" in clean:
        return "Erro ao extrair vídeo do TikTok. Atualize o pacote yt-dlp (.venv/Scripts/python.exe -m pip install -U yt-dlp curl-cffi) e reinicie o servidor."
    return clean


def run_download(download_id, url, output_dir, fmt, audio_only, container, browser_cookies, cookies_file, h264_compat, download_playlist=False, create_subfolder=True):
    with progress_lock:
        progress_data[download_id] = {
            "status": "starting",
            "percent": 0,
            "is_playlist": download_playlist,
        }

    if download_playlist:
        if create_subfolder:
            outtmpl = os.path.join(output_dir, "%(playlist_title,playlist)s", "%(playlist_index)02d - %(title)s.%(ext)s")
        else:
            outtmpl = os.path.join(output_dir, "%(playlist_index)02d - %(title)s.%(ext)s")
    else:
        outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    ydl_logger = YDLLogger()

    ydl_opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [make_progress_hook(download_id, is_playlist=download_playlist)],
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": os.path.dirname(find_ffmpeg()),
        "noplaylist": not download_playlist,
        "no_color": True,
        "ignoreerrors": True if download_playlist else False,
        "logger": ydl_logger,
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
            pass
        else:
            # container define o formato do arquivo final (mp4, mkv, webm, original)
            if container != "original":
                ydl_opts["merge_output_format"] = container

    if h264_compat and not audio_only:
        ffmpeg_bin = find_ffmpeg()
        def remux_hook(filename):
            with progress_lock:
                progress_data[download_id]["status"] = "remuxing"
            remux_to_mp4(filename, ffmpeg_bin)

        ydl_opts["post_hooks"] = [remux_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            with progress_lock:
                if download_playlist:
                    skipped_count = len(ydl_logger.errors)
                    if skipped_count > 0:
                        msg = f"Download da playlist concluído! ({skipped_count} vídeo(s) exclusivo(s) para membros ou indisponíveis foram pulados)."
                    else:
                        msg = "Download da playlist concluído com sucesso!"
                else:
                    msg = "Download concluído!"

                progress_data[download_id] = {
                    "status": "finished",
                    "percent": 100,
                    "is_playlist": download_playlist,
                    "filename": ydl.prepare_filename(info) if (not download_playlist and info) else "",
                    "message": msg,
                }
    except Exception as e:
        with progress_lock:
            progress_data[download_id] = {"status": "error", "message": clean_error_message(str(e))}


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
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    browser_cookies = data.get("browser_cookies", "").strip()
    cookies_file = data.get("cookies_file", "").strip()
    force_single = data.get("force_single", False)

    if not url:
        return jsonify({"error": "URL não informada"}), 400

    # 1. Detecção rápida de playlist quando aplicável
    is_playlist_candidate = ("list=" in url or "/playlist" in url)
    if is_playlist_candidate and not force_single:
        ydl_opts_flat = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "ffmpeg_location": os.path.dirname(find_ffmpeg()),
        }
        if cookies_file and os.path.isfile(cookies_file):
            ydl_opts_flat["cookiefile"] = cookies_file
        elif browser_cookies:
            ydl_opts_flat["cookiesfrombrowser"] = (browser_cookies,)

        try:
            with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
                info = ydl.extract_info(url, download=False)
                if info.get("_type") == "playlist" or info.get("entries"):
                    entries = list(info.get("entries") or [])
                    playlist_count = info.get("playlist_count") or len(entries)
                    has_single_video = bool(re.search(r"(?:[?&]v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})", url))

                    thumbnail = ""
                    if entries and entries[0]:
                        first = entries[0]
                        thumbnail = first.get("thumbnail") or (first.get("thumbnails") and first.get("thumbnails")[0].get("url")) or ""
                    if not thumbnail and info.get("thumbnails"):
                        thumbnail = info.get("thumbnails")[0].get("url")

                    return jsonify({
                        "is_playlist": True,
                        "has_single_video": has_single_video,
                        "title": info.get("title") or "Playlist",
                        "video_title": entries[0].get("title", "") if has_single_video and entries else "",
                        "playlist_count": playlist_count,
                        "thumbnail": thumbnail,
                        "playlist_id": info.get("id", ""),
                        "duration": None,
                        "filesize": None,
                    })
        except Exception:
            # Fallback para consulta padrão se a extração flat falhar
            pass

    # 2. Consulta padrão de vídeo único
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
        "noplaylist": True,
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
                "is_playlist": False,
                "title": title,
                "duration": duration,
                "filesize": total_bytes,
                "approximate": approximate,
                "thumbnail": info.get("thumbnail", ""),
            })
    except Exception as e:
        return jsonify({"error": clean_error_message(str(e))}), 400


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/download", methods=["POST"])
def start_download():
    data = request.get_json() or {}
    url = data.get("url", "").strip()
    output_dir = data.get("output_dir", "").strip() or os.path.expanduser("~/Downloads")
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    container = data.get("container", "mp4")
    browser_cookies = data.get("browser_cookies", "").strip()
    cookies_file = data.get("cookies_file", "").strip()
    h264_compat = data.get("h264_compat", False)
    download_playlist = data.get("download_playlist", False)
    create_subfolder = data.get("create_subfolder", True)

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
        args=(download_id, url, output_dir, fmt, audio_only, container, browser_cookies, cookies_file, h264_compat, download_playlist, create_subfolder),
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