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

### Download não inicia

- Verifique se a URL é válida/pública
- Teste sem cookies primeiro
- Se necessário, selecione o navegador correto em "Cookies do navegador"

### Pasta inválida

- Informe um caminho existente ou use o botão de pasta da interface

---

## Observações importantes

- O app é local, não precisa de banco de dados.
- O uso de cookies do navegador pode ser necessário para conteúdos privados/restritos.
- O download depende das regras e disponibilidade da plataforma de origem.

---

## Licença

Uso pessoal/educacional.

