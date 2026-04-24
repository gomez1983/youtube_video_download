import os
import threading
import tkinter as tk
from tkinter import filedialog
from flask import Flask, request, jsonify, send_from_directory

import yt_dlp

# Inicialização da aplicação Flask e configuração de arquivos estáticos
app = Flask(__name__, static_folder=".", static_url_path="")

# Estado global de progresso por download_id para rastreamento em tempo real
progress_data = {}
# Lock para garantir thread-safety ao manipular o dicionário de progresso
progress_lock = threading.Lock()


@app.after_request
def add_cors_headers(response):
    """
    Permite que o front-end rodando em outra porta (ex.: Live Server)
    faça chamadas para esta API local durante o desenvolvimento.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def make_progress_hook(download_id):
    """
    Cria uma função de hook personalizada para capturar o progresso do yt-dlp.

    Args:
        download_id: Identificador único do download.

    Returns:
        Uma função interna (hook) que será chamada pelo yt-dlp durante o processo.
    """
    def hook(d):
        with progress_lock:
            # Tratamento de status durante o download ativo
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                
                # Atualiza o dicionário global com métricas de velocidade e tempo
                progress_data[download_id] = {
                    "status": "downloading",
                    "percent": round(percent, 1),
                    "speed": round(speed / 1024, 1) if speed else 0,  # KB/s
                    "eta": eta,
                    "filename": d.get("filename", ""),
                }
            # Tratamento para conclusão do processo
            elif d["status"] == "finished":
                progress_data[download_id] = {
                    "status": "finished",
                    "percent": 100,
                    "filename": d.get("filename", ""),
                }
            # Tratamento de erros reportados pelo yt-dlp
            elif d["status"] == "error":
                progress_data[download_id] = {
                    "status": "error",
                    "message": str(d.get("error", "Erro desconhecido")),
                }

    return hook


def run_download(download_id, url, output_dir, fmt, audio_only, container, browser_cookies):
    """
    Executa o processo de download em segundo plano utilizando a biblioteca yt-dlp.

    Args:
        download_id: ID de controle do progresso.
        url: URL do vídeo para download.
        output_dir: Diretório de destino dos arquivos.
        fmt: Formato/Qualidade selecionada.
        audio_only: Booleano para extração apenas de áudio.
        container: Formato de saída final (mp4, mkv, etc).
        browser_cookies: Nome do navegador para extração de cookies.
    """
    with progress_lock:
        progress_data[download_id] = {"status": "starting", "percent": 0}

    # Define o template do nome do arquivo de saída
    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")

    # Configurações base do YoutubeDL
    ydl_opts = {
        "outtmpl": outtmpl,
        "progress_hooks": [make_progress_hook(download_id)],
        "quiet": True,
        "no_warnings": True,
    }

    # Passa cookies do navegador se informado (útil para vídeos com restrição)
    if browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)

    # Configurações específicas para extração de Áudio (MP3)
    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    # Configurações para Vídeo
    else:
        if fmt == "best":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        else:
            ydl_opts["format"] = fmt
        
        # Define o formato de agrupamento (muxing) final
        if container != "original":
            ydl_opts["merge_output_format"] = container

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        with progress_lock:
            progress_data[download_id] = {"status": "error", "message": str(e)}


@app.route("/browse-folder", methods=["POST"])
def browse_folder():
    """
    Interface para abrir o seletor de pastas nativo do sistema operacional via Tkinter.
    Retorna o caminho da pasta selecionada em formato JSON.
    """
    # Abre a janela de seleção de pasta nativa do Windows via tkinter
    root = tk.Tk()
    root.withdraw()           # Oculta a janela principal do tkinter
    root.wm_attributes("-topmost", True)  # Garante que o diálogo fica na frente das outras janelas
    folder = filedialog.askdirectory(parent=root, title="Selecionar pasta de destino")
    root.destroy()

    if folder:
        # Converte separadores para o padrão do Windows (\)
        folder = os.path.normpath(folder)
        return jsonify({"folder": folder})
    return jsonify({"folder": None})


@app.route("/browse-folder", methods=["OPTIONS"])
@app.route("/info", methods=["OPTIONS"])
@app.route("/download", methods=["OPTIONS"])
@app.route("/progress/<download_id>", methods=["OPTIONS"])
def options_handler(download_id=None):
    """Responde preflight CORS para requisições feitas de outra origem."""
    return ("", 204)


@app.route("/info", methods=["POST"])
def get_info():
    """
    Obtém metadados do vídeo (título, duração e tamanho estimado) sem iniciar o download.
    """
    data = request.get_json()
    url = data.get("url", "").strip()
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    browser_cookies = data.get("browser_cookies", "").strip()

    if not url:
        return jsonify({"error": "URL não informada"}), 400

    # Determina o formato de consulta
    if audio_only:
        ydl_fmt = "bestaudio/best"
    else:
        ydl_fmt = "bestvideo+bestaudio/best" if fmt == "best" else fmt

    ydl_opts = {
        "format": ydl_fmt,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    if browser_cookies:
        ydl_opts["cookiesfrombrowser"] = (browser_cookies,)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrai informações sem baixar o arquivo
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            duration = info.get("duration", 0)

            # Cálculo do tamanho total considerando múltiplos fluxos (vídeo + áudio)
            requested = info.get("requested_formats") or [info]
            total_bytes = 0
            approximate = False
            for f in requested:
                b = f.get("filesize") or f.get("filesize_approx")
                if b:
                    total_bytes += b
                    # Marca se o tamanho é apenas uma estimativa
                    if not f.get("filesize"):
                        approximate = True

            return jsonify({
                "title": title,
                "duration": duration,
                "filesize": total_bytes,
                "approximate": approximate,
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/")
def index():
    """Serve a página principal (index.html) da aplicação."""
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    """Endpoint simples para verificar disponibilidade do backend."""
    return jsonify({"status": "ok"})


@app.route("/download", methods=["POST"])
def start_download():
    """
    Endpoint principal para iniciar o download. 
    Cria um ID único e dispara uma nova thread para não bloquear o servidor Flask.
    """
    data = request.get_json()
    url = data.get("url", "").strip()
    output_dir = data.get("output_dir", "").strip() or os.path.expanduser("~/Downloads")
    fmt = data.get("format", "best")
    audio_only = data.get("audio_only", False)
    container = data.get("container", "mp4")
    browser_cookies = data.get("browser_cookies", "").strip()

    if not url:
        return jsonify({"error": "URL não informada"}), 400

    # Valida e cria o diretório de destino se necessário
    if not os.path.isdir(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            return jsonify({"error": f"Diretório inválido: {e}"}), 400

    import uuid
    # Gera um identificador único para rastrear este download específico
    download_id = str(uuid.uuid4())

    # Inicia o download em uma thread separada (daemon=True para fechar com o app)
    thread = threading.Thread(
        target=run_download,
        args=(download_id, url, output_dir, fmt, audio_only, container, browser_cookies),
        daemon=True,
    )
    thread.start()

    return jsonify({"download_id": download_id})


@app.route("/progress/<download_id>")
def get_progress(download_id):
    """
    Retorna o status atual e o percentual de progresso de um download específico.
    """
    with progress_lock:
        data = progress_data.get(download_id, {"status": "not_found"})
    return jsonify(data)


if __name__ == "__main__":
    # Inicializa o servidor na porta 5000. Debug desativado para evitar conflitos com threads/Tkinter.
    app.run(debug=False, port=5000)