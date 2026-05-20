# Docker run guide

## Full app

```powershell
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8080

The backend image runs `handwrite2350-engine` locally inside the container with
FontForge and Potrace installed, so it does not need access to the host Docker
socket.

For AI font generation, download the model weights from the shared Google Drive
folder and place them here:

```text
fewshot-font-generation/write2font/pth/last_lf.pth
fewshot-font-generation/write2font/pth/last.pth
```

The Docker Compose backend uses MX-Font by default:

```text
FONT_ENGINE_AI_MODEL=MX
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/last.pth
```

Switch to LF-Font by changing:

```text
FONT_ENGINE_AI_MODEL=LF
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/last_lf.pth
```

## Local backend with Docker font engine

If you run the Spring backend directly on Windows, build the font engine image
once:

```powershell
docker compose build handwrite2350
docker compose build write2font-ai
```

Then run the backend normally:

```powershell
cd backend
.\gradlew.bat bootRun
```

Manual scan uploads call:

```text
docker run --rm -v <upload>/input:/app/samples/input -v <upload>/handwrite-output:/app/outputs handwrite2350:latest
```

AI uploads call the `write2font-ai:cpu` image by default. Set the weight path
before `bootRun` only if you want to override the default MX model:

```powershell
$env:FONT_ENGINE_AI_WEIGHT_PATH="C:\absolute\path\to\last.pth"
$env:FONT_ENGINE_AI_MODEL="MX"
.\gradlew.bat bootRun
```

If `last.pth` is already placed under
`fewshot-font-generation/write2font/pth`, the checked-in development defaults
are enough for MX-Font.

## Notes

- `handwrite2350` expects 14 photographed template pages for the upload-based
  direct-input flow.
- Browser drawing mode still uses the existing legacy `font-engine` because its
  input is per-character canvas PNGs, not 14 scanned pages.
- AI font generation uses the same marked 11x17 template format as
  `handwrite2350`. It reads the first 64 cells in `write2font/ref_chars.json`
  order, or 64 individual PNG files named `<character>.png`.
- AI sheet inputs are tightly cropped, then converted to black background with
  white glyphs before inference. Generated black-background PNGs are inverted
  during TTF conversion.
- Useful settings:
  - `FONT_ENGINE_HANDWRITE_USE_DOCKER=true|false`
  - `FONT_ENGINE_HANDWRITE_DOCKER_IMAGE=handwrite2350:latest`
  - `FONT_ENGINE_HANDWRITE_WORKERS=8`
  - `FONT_ENGINE_HANDWRITE_ENGINE_DIR=/workspace/handwrite2350-engine`
  - `FONT_ENGINE_AI_USE_DOCKER=true|false`
  - `FONT_ENGINE_AI_DOCKER_IMAGE=write2font-ai:cpu`
  - `FONT_ENGINE_AI_MODEL=LF|MX`
  - `FONT_ENGINE_AI_WEIGHT_PATH=.../last.pth`
