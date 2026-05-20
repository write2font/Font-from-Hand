# Font From Hand

손글씨 이미지를 업로드해 개인 폰트(`.ttf`)를 생성하는 웹 애플리케이션입니다.

- Frontend: Next.js
- Backend: Spring Boot
- Font engines: Python, FontForge, Potrace
- Manual scan: `handwrite2350-engine`
- AI generation: `fewshot-font-generation` with MX-Font by default

## Quick Start

### 1. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at http://localhost:3000.

### 2. Backend

```powershell
cd backend
.\gradlew.bat bootRun
```

Backend runs at http://localhost:8080.

The local backend uses H2 by default, so a separate database is not required for
development.

## AI Font Weights

AI generation requires model weights that are not committed to Git.

Place the downloaded files here:

```text
fewshot-font-generation/write2font/pth/last.pth
fewshot-font-generation/write2font/pth/last_lf.pth
```

The default AI model is MX-Font:

```text
FONT_ENGINE_AI_MODEL=MX
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/last.pth
```

LF-Font can still be used by changing those environment variables.

## Templates

- Manual scan generation uses the 2350-character `handwrite2350` template flow.
- AI generation uses the same marked 11x17 template format, but reads only the
  first 64 cells in `fewshot-font-generation/write2font/ref_chars.json` order.
- AI input cells are cropped tightly and converted to the model format
  (black background, white glyph) before inference.

## Docker

For full Docker instructions, see [DOCKER.md](./DOCKER.md).

```powershell
docker compose up --build
```

The compose setup runs the backend, frontend, and local font engine dependencies
inside containers. Model weight files remain mounted from
`fewshot-font-generation/write2font/pth`.

## Notes

- `.pth`, `.pt`, `.ckpt`, generated PNGs, and generated uploads are ignored by
  Git.
- If port `8080` is already in use, stop the existing backend process or change
  the compose/backend port before running.
