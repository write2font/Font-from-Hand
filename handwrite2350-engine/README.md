# handwrite2350

손글씨 표 이미지를 TTF 폰트로 변환하는 Docker 기반 폰트 생성 엔진입니다.

14장의 손글씨 표 이미지를 입력받아 Basic Latin 94자와 KS X 1001 한글 2,350자, 총 2,444자의 glyph를 추출하고 하나의 TTF 폰트로 빌드합니다.

## Pipeline

```text
손글씨 표 이미지
→ 마커 검출 및 원근 보정
→ 셀 분리
→ glyph 정규화
→ Potrace SVG 변환
→ FontForge TTF 빌드
→ 폰트 파일 출력
```

처리 흐름은 다음과 같습니다.

1. `samples/`에 손글씨 표 이미지 14장을 넣습니다.
2. Docker 컨테이너가 각 페이지의 4개 마커를 기준으로 원근 보정을 수행합니다.
3. 보정된 페이지를 셀 단위로 분리합니다.
4. 각 셀의 glyph를 `512 x 512` 캔버스 기준으로 정규화합니다.
5. Potrace로 glyph bitmap을 SVG로 변환합니다.
6. FontForge로 SVG glyph를 등록하고 TTF 폰트를 생성합니다.

## Outputs

주요 결과물은 `outputs/` 아래에 생성됩니다.

```text
outputs/
├─ fonts/                 # 생성된 TTF 폰트
├─ svg/                   # glyph별 SVG
├─ normalized/            # 정규화 glyph PNG, 옵션 사용 시 저장
├─ warped/                # 원근 보정 페이지, 옵션/모드에 따라 저장
├─ trace_report.txt       # SVG 변환 결과
├─ font_build_report.txt  # TTF 생성 결과
└─ performance_report.txt # 전체 실행 시간 및 단계별 성능
```

최종 폰트는 보통 다음 경로에 생성됩니다.

```text
outputs/fonts/{postscript_name}.ttf
```

## Build

```bash
docker build -t handwrite2350 .
```

## Run

macOS/Linux:

```bash
docker run --rm \
  -v "$(pwd)/samples:/app/samples" \
  -v "$(pwd)/outputs:/app/outputs" \
  handwrite2350
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}/samples:/app/samples" `
  -v "${PWD}/outputs:/app/outputs" `
  handwrite2350
```

폰트 이름과 제작자명을 함께 지정하려면 다음처럼 실행합니다.

```bash
docker run --rm \
  -v "$(pwd)/samples:/app/samples" \
  -v "$(pwd)/outputs:/app/outputs" \
  handwrite2350 \
  --family-name "MyHandwrite" \
  --designer "ccomet"
```

## Common Options

| Option | Description |
| --- | --- |
| `--family-name` | 생성할 폰트 family name |
| `--designer` | 제작자 이름 |
| `--interactive` | 실행 중 폰트 metadata 입력 |
| `--workers` | 병렬 처리 worker 수 |
| `--fast` | 검수용 산출물을 줄이고 빠르게 실행 |
| `--save-normalized` | 정규화 glyph PNG 저장 |
| `--save-debug-artifacts` | 마커, 셀, contact sheet 등 검수용 파일 저장 |
| `--font-quality` | FontForge cleanup 모드, `fast` 또는 `high` |

예시:

```bash
docker run --rm \
  -v "$(pwd)/samples:/app/samples" \
  -v "$(pwd)/outputs:/app/outputs" \
  handwrite2350 \
  --fast \
  --workers 8 \
  --save-normalized \
  --family-name "test-font" \
  --designer "ccomet"
```

## Notes

- 기본 실행은 TTF 생성에 필요한 최소 산출물을 중심으로 동작합니다.
- 검수용 이미지가 필요하면 `--save-normalized` 또는 `--save-debug-artifacts`를 사용합니다.
- 실험적인 glyph 배치 보정은 `--layout-mode adaptive`로 실행할 수 있습니다.
- 자모 mask 생성 실험 코드는 메인 폰트 엔진과 분리했습니다.
