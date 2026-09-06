# YT/DL - YouTube Downloader Local

Aplicativo local para baixar vídeos (ou extrair áudio em MP3) usando:

- **Frontend:** `index.html` (interface no navegador)
- **Backend:** `app.py` (API Flask)
- **Engine de download:** `yt-dlp`

O projeto foi feito para rodar localmente no seu computador, sem deploy em nuvem.

---

## Como o app funciona (visão geral)

1. Você informa a URL do vídeo na interface.
2. O frontend chama o endpoint `/info` para buscar título, duração e tamanho estimado.
3. Ao clicar em **Baixar**, o frontend chama `/download`.
4. O backend inicia o download em **thread separada** (não trava a API).
5. O frontend consulta `/progress/<download_id>` periodicamente e atualiza a barra.
6. Ao finalizar, a interface mostra sucesso; em caso de erro, mostra a mensagem retornada.

---

## Funcionalidades principais

- Download completo de playlists do YouTube:
  - Detecção automática da playlist e contagem de vídeos.
  - Opção para baixar a playlist inteira ou somente o vídeo individual em URLs mistas.
  - Criação automática de subpasta com o nome da playlist e ordenação sequencial numérica dos arquivos.
  - Acompanhamento do progresso item a item (ex: vídeo X de Y).
- Download de vídeo com qualidade selecionável:
  - Melhor disponível
  - 1080p
  - 720p
  - 480p
- Escolha de container final:
  - MP4
  - MKV
  - WebM
  - Original (sem conversão)
- Modo **Só áudio (MP3)**.
- Seleção de pasta de destino via diálogo nativo do Windows.
- Uso opcional de cookies do navegador (Chrome/Firefox/Edge/Brave/Opera).
- Barra de progresso com:
  - percentual
  - velocidade (KB/s)
  - ETA
- Indicador de status do backend:
  - **Backend: online**
  - **Backend: offline**

---

## Requisitos

- Python 3.x
- `pip`
- `ffmpeg` (necessário para mesclar/converter áudio e vídeo)

---

## Instalação

No terminal, dentro da pasta do projeto:

```bash
pip install flask yt-dlp
```

Instale o ffmpeg (Windows):

```bash
winget install ffmpeg
```

Depois de instalar o ffmpeg, feche e reabra o terminal.

---

## Como executar

### Opção recomendada (sem Live Server)

1. Rode o backend:

```bash
python app.py
```

2. Abra no navegador:

```text
http://127.0.0.1:5000
```

### Atalho de inicializacao (sem alterar o codigo)

Se quiser evitar iniciar tudo manualmente, use:

```bat
iniciar_projeto.bat
```

Esse atalho:
- ativa o `.venv` automaticamente (se existir);
- abre uma janela para rodar `python app.py`;
- abre o navegador em `http://127.0.0.1:5000`.

Para encerrar, feche a janela chamada **YT/DL Backend**.

### Opção com Live Server

- O frontend pode rodar em outra porta (ex.: `5500`), e a API continua em `5000`.
- O projeto já está preparado para isso.
- **Importante:** o `app.py` precisa estar rodando.

---

## Estrutura de arquivos

- `app.py`  
  API Flask com rotas de info/download/progresso, health-check e seleção de pasta.

- `index.html`  
  Interface completa (HTML + CSS + JavaScript) e lógica de chamadas da API.

- `LEIAME.txt`  
  Guia em texto simples com passos rápidos.

---

## Endpoints da API

### `GET /`
Serve a página principal (`index.html`).

### `GET /health`
Retorna status do backend.

Resposta esperada:

```json
{ "status": "ok" }
```

### `POST /info`
Recebe URL e opções para consultar metadados sem baixar.

### `POST /download`
Inicia download e retorna `download_id`.

### `GET /progress/<download_id>`
Retorna o estado atual do download (starting, downloading, finished, error).

### `POST /browse-folder`
Abre seletor de pasta no Windows e retorna o caminho escolhido.

---

## Fluxo interno de download

- O backend gera um `download_id` único.
- Cria uma thread daemon para executar o `yt-dlp`.
- Um hook de progresso atualiza um dicionário global (`progress_data`) protegido por lock.
- O frontend faz polling a cada ~800ms e atualiza a UI.

Esse desenho evita travar o servidor durante downloads longos.

---

## Solução de problemas

### "Servidor indisponível" / "Não foi possível conectar ao servidor Flask"

Causa comum: backend não iniciado.

1. Rode `python app.py`
2. Confirme no terminal: `Running on http://127.0.0.1:5000`
3. Recarregue a página

### "ffmpeg is not installed"

- Instale com `winget install ffmpeg`
- Reabra o terminal

### "Join this channel to get access to members-only content" / Conteúdo exclusivo

- O vídeo ou um dos vídeos da playlist requer assinatura de membro do canal (*"Seja Membro"*).
- Em playlists, o app **pula automaticamente** esses vídeos restritos para não travar o restante do download.
- Se você **for membro** do canal, selecione o navegador em que você está logado no seletor **"Cookies do navegador"** ou forneça seu arquivo `cookies.txt`.

---

## Conteúdos e Playlists Exclusivos para Membros (Seja Membro)

O YouTube bloqueia o acesso anônimo a vídeos exclusivos para membros de canais. O YT/DL lida com isso das seguintes formas:

1. **Em Playlists com vídeos mistos (públicos e exclusivos):**
   - O app não interrompe o download ao encontrar um vídeo restrito.
   - Os vídeos exclusivos ou indisponíveis são pulados automaticamente, e todos os vídeos públicos continuam sendo baixados normalmente.
   - Ao finalizar a playlist, o app informa se algum vídeo foi pulado.

2. **Como baixar vídeos exclusivos se você é assinante/membro:**
   - Certifique-se de estar conectado à sua conta do YouTube em seu navegador (Chrome, Edge, Firefox, Brave ou Opera).
   - Na interface do aplicativo, no campo **"Cookies do navegador"**, selecione o navegador correspondente.
   - Alternativamente, exporte os cookies da sua sessão para um arquivo `cookies.txt` e aponte o arquivo no campo **"Arquivo cookies.txt"**.
   - Com a autenticação ativa, o aplicativo terá permissão de membro e baixará os conteúdos exclusivos com sucesso.

---

## Observações importantes

- O app é local, não precisa de banco de dados.
- O uso de cookies do navegador pode ser necessário para conteúdos privados/restritos (como vídeos de membros ou Instagram Stories).
- O download depende das regras e disponibilidade da plataforma de origem.

---

## Licença

Uso pessoal/educacional.

