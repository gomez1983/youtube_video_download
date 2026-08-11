# CHANGELOG — YT/DL Downloader Local

---

## [1.7.0] — Player embed e detecção dinâmica do ffmpeg

### Adicionado
- Player embed do YouTube exibido diretamente no info box para URLs `youtube.com/watch`, `youtu.be` e `youtube.com/shorts`
- Suporte a URLs curtas e Shorts do YouTube na detecção do ID do vídeo

### Alterado
- Detecção do ffmpeg substituída por busca dinâmica via glob em todas as versões Gyan.FFmpeg instaladas pelo winget — elimina necessidade de atualização manual do caminho após upgrades

### Comportamento
- Fallback automático para thumbnail quando a URL não é do YouTube (Globoplay, Instagram, TikTok etc.)

---

## [1.6.0] — Compatibilidade com Adobe Premiere

### Adicionado
- Toggle "Compatível com Premiere (H.264)" na interface
- Após o download, o app executa remux via ffmpeg com `-c copy -movflags +faststart`, gerando um arquivo `_premiere.mp4` na mesma pasta
- Status "Convertendo para Premiere..." exibido na barra de progresso durante o remux
- Caminho do ffmpeg passado diretamente ao `yt-dlp` via `ffmpeg_location`, eliminando dependência do PATH do sistema

### Corrigido
- Vídeos do Globoplay baixados em container MPEG-TS (incompatível com Premiere) agora são convertidos para MP4 real com estrutura correta

---

## [1.5.0] — Suporte a cookies via arquivo e melhoria de autenticação

### Adicionado
- Campo "Arquivo cookies.txt" com botão 📄 para abrir seletor de arquivo nativo (tkinter)
- Rota `/browse-file` no Flask para abrir o seletor de arquivo nativo do Windows
- `cookies_file` tem prioridade sobre o seletor de navegador quando ambos estão preenchidos
- Info box exibe "Requer autenticação — use cookies" quando o site bloqueia a consulta de metadados

### Corrigido
- Erro "Could not copy Chrome cookie database" contornado via exportação manual de cookies.txt

---

## [1.4.0] — Suporte a autenticação via cookies do navegador

### Adicionado
- Seletor "Cookies do navegador" (Chrome, Firefox, Edge, Brave, Opera)
- Parâmetro `cookiesfrombrowser` repassado ao `yt-dlp` nas rotas `/download` e `/info`
- Suporte a Instagram Stories e conteúdo privado via autenticação

---

## [1.3.0] — Thumbnail preview e modo claro/escuro

### Adicionado
- Thumbnail do vídeo exibida automaticamente no info box após consulta de metadados
- Botão fixo no canto superior direito para alternar entre modo escuro e claro
- Variáveis CSS para tema claro (`:root.light`)
- Transições suaves ao trocar de tema

---

## [1.2.0] — Info box e seletor de formato de container

### Adicionado
- Info box automático: exibe título, tamanho estimado e duração ao colar uma URL
- Consulta disparada 0,8s após parar de digitar, e atualizada ao trocar qualidade ou toggle de áudio
- Rota `/info` no Flask para consultar metadados via `yt-dlp` sem iniciar o download
- Seletor de formato de container: MP4, MKV, WebM, Original (sem conversão)
- MP4 definido como padrão de saída

### Alterado
- Interface reorganizada: seletores de qualidade e container na mesma linha

---

## [1.1.0] — Seletor de pasta nativo e melhorias de interface

### Adicionado
- Botão 📁 ao lado do campo "Pasta de destino" abre o seletor de pasta nativo do Windows via tkinter
- Rota `/browse-folder` no Flask integrada ao `filedialog.askdirectory`
- Caminho retornado já normalizado para o padrão Windows (`os.path.normpath`)

---

## [1.0.0] — Versão inicial

### Adicionado
- Servidor Flask (`app.py`) com rotas `/download` e `/progress/<id>`
- Interface web (`index.html`) com campo de URL, pasta de destino, seletor de qualidade e toggle de áudio MP3
- Download assíncrono em thread separada com progresso em tempo real (velocidade, ETA, percentual)
- Suporte a mais de 1000 sites via `yt-dlp`
- Extração de áudio em MP3 via ffmpeg
- Design dark com tipografia DM Mono + Syne