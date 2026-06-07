# Docker 실행 가이드

## 전체 앱 실행

```powershell
docker compose up --build
```

- 프론트엔드: http://localhost:3000
- 백엔드: http://localhost:8080
- MySQL: localhost:3306

백엔드 이미지는 컨테이너 내부에서 `handwrite2350-engine`을 직접 실행합니다. FontForge와 Potrace도 백엔드 이미지에 설치되므로 host Docker socket에 접근할 필요가 없습니다.

## MySQL

Docker Compose는 애플리케이션 데이터 저장용 MySQL 8.4 컨테이너를 함께 실행합니다.

개발용 기본 계정은 아래와 같습니다.

```text
SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/font_from_hand
SPRING_DATASOURCE_USERNAME=ffh
SPRING_DATASOURCE_PASSWORD=ffh_dev_password
```

DB 파일은 `mysql-data` Docker volume에 저장됩니다. 컨테이너를 중지해도 데이터는 유지됩니다. DB를 완전히 초기화하고 싶을 때만 해당 volume을 삭제하세요.

## DM-Font 가중치

AI 폰트 생성을 사용하려면 팀 공유 드라이브에서 DM-Font weight 파일을 내려받아 아래 경로에 넣어 주세요.

```text
fewshot-font-generation/write2font/pth/dm.pth
```

Docker Compose 백엔드는 DM-Font만 사용합니다.

```text
FONT_ENGINE_AI_MODEL=DM
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/dm.pth
```

`dm.pth`는 Git과 Docker 이미지에 포함하지 않고, 실행 시 volume mount로 컨테이너에 연결합니다.

## 자서전 환경변수

자서전 생성을 사용하려면 로컬에 아래 파일을 만들어야 합니다.

```text
autobiography/.env
```

`autobiography/.env.example`을 템플릿으로 사용하고, 실제 API 키는 팀 노션 또는 공유 채널의 값을 넣어 주세요.

이 파일은 Docker Compose 실행 시 백엔드 컨테이너의 `/workspace/autobiography/.env`로 마운트됩니다. Git과 Docker 이미지에는 포함되지 않습니다.

## 백엔드만 로컬에서 직접 실행하는 경우

Spring Boot 백엔드를 Windows에서 직접 실행하려면 먼저 MySQL 컨테이너를 켭니다.

```powershell
docker compose up -d mysql
cd backend
.\gradlew.bat bootRun
```

AI 폰트 weight 경로를 기본값과 다르게 쓰고 싶다면 실행 전에 환경변수를 지정합니다.

```powershell
$env:FONT_ENGINE_AI_WEIGHT_PATH="C:\absolute\path\to\dm.pth"
$env:FONT_ENGINE_AI_MODEL="DM"
.\gradlew.bat bootRun
```

`dm.pth`가 `fewshot-font-generation/write2font/pth` 아래에 있으면 별도 환경변수 없이 기본값으로 동작합니다.

## 도구 이미지

필요한 경우 폰트 엔진 도구 이미지만 별도로 빌드할 수 있습니다.

```powershell
docker compose build handwrite2350
docker compose build write2font-ai
```

수동 스캔 업로드 흐름은 `handwrite2350` 엔진을 사용합니다.

```text
docker run --rm -v <upload>/input:/app/samples/input -v <upload>/handwrite-output:/app/outputs handwrite2350:latest
```

## 참고

- `handwrite2350`은 업로드 기반 직접 입력 흐름에서 14장의 템플릿 사진을 기대합니다.
- 브라우저에서 직접 그리는 방식은 기존 legacy `font-engine`을 사용합니다. 입력이 14장 템플릿이 아니라 글자별 canvas PNG이기 때문입니다.
- AI 폰트 생성은 DM-Font와 marked template 형식을 사용합니다.
- AI 폰트 생성은 `write2font/ref_chars.json` 순서의 38개 셀 또는 `<character>.png` 형식의 38개 개별 PNG를 읽습니다.
- AI 샘플 이미지는 padding 0으로 crop되며, DM-Font 추론을 위해 검은 배경/흰 글자 형식으로 변환됩니다.
- 자서전 생성은 백엔드 컨테이너 내부의 `/workspace/autobiography`에서 실행되며, 생성 PDF는 `autobiography/output` 아래에 저장됩니다.

## 주요 환경변수

```text
FONT_ENGINE_HANDWRITE_USE_DOCKER=true|false
FONT_ENGINE_HANDWRITE_DOCKER_IMAGE=handwrite2350:latest
FONT_ENGINE_HANDWRITE_WORKERS=8
FONT_ENGINE_HANDWRITE_ENGINE_DIR=/workspace/handwrite2350-engine

FONT_ENGINE_AI_USE_DOCKER=true|false
FONT_ENGINE_AI_DOCKER_IMAGE=write2font-ai:cpu
FONT_ENGINE_AI_MODEL=DM
FONT_ENGINE_AI_WEIGHT_PATH=.../dm.pth
```
