# 🎨 FFH (Font From Hand) 프로젝트 가이드

이 프로젝트는 사용자의 손글씨를 분석하여 개인화된 폰트(.ttf)를 생성하고 관리하며, 생성된 폰트를 자서전 PDF에 활용하는 서비스입니다. **Next.js, Spring Boot, MySQL, Python**이 결합된 모노레포 구조로 운영됩니다.

---

## 🛠 1. 공통 필수 설치 도구

개발 시작 전 본인 노트북에 아래 도구들을 설치해 주세요.

- **Docker Desktop**: 전체 서비스 실행 및 MySQL/폰트 엔진/자서전 엔진 실행용
- **Git**: 코드 버전 관리
- **Java 17 (LTS)**: 백엔드를 로컬에서 직접 실행할 때 필요
- **Node.js (v18 이상)**: 프론트엔드를 로컬에서 직접 실행할 때 필요
- **Python 3.9 이상**: Python 엔진을 로컬에서 직접 실행할 때 필요

> 현재는 `docker compose up --build`로 실행하는 방식을 권장합니다.

---

## 🚀 2. 초기 세팅 및 실행 순서

### 1단계: 프로젝트 클론

```bash
git clone [Organization 레포지토리 주소]
cd Font-from-Hand
```

### 2단계: DM-Font 가중치 파일 준비

AI 폰트 생성에 필요한 모델 weight 파일은 용량 문제로 Git에 포함하지 않습니다. 팀 공유 드라이브에서 `dm.pth`를 내려받아 아래 경로에 넣어 주세요.

```text
fewshot-font-generation/write2font/pth/dm.pth
```

현재 AI 폰트 생성은 **DM-Font만 사용**합니다.

```text
FONT_ENGINE_AI_MODEL=DM
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/dm.pth
```

### 3단계: 자서전 API 키 설정

자서전 기능을 사용하는 경우 `autobiography/.env` 파일을 직접 생성해야 합니다.

```text
autobiography/.env
```

`autobiography/.env.example` 파일을 복사한 뒤, 실제 API 키 값은 팀 노션 또는 공유 채널을 참고해 채워 주세요.

> `.env` 파일은 절대 Git에 커밋하지 않습니다.

### 4단계: Docker Compose 실행

프론트엔드, 백엔드, MySQL, 폰트 엔진, 자서전 엔진 의존성을 한 번에 실행합니다.

```powershell
docker compose up --build
```

- 프론트엔드: http://localhost:3000
- 백엔드: http://localhost:8080
- MySQL: localhost:3306

자세한 Docker 실행 정보는 `DOCKER.md`를 참고해 주세요.

---

## 🗄 3. 데이터베이스 설정

현재 기본 데이터베이스는 **MySQL 8.4**입니다. Docker Compose 실행 시 MySQL 컨테이너가 함께 생성됩니다.

개발용 기본 설정은 아래와 같습니다.

```text
SPRING_DATASOURCE_URL=jdbc:mysql://mysql:3306/font_from_hand
SPRING_DATASOURCE_USERNAME=ffh
SPRING_DATASOURCE_PASSWORD=ffh_dev_password
```

DB 데이터는 Docker volume인 `mysql-data`에 저장됩니다. 컨테이너를 껐다 켜도 데이터는 유지되며, 완전히 초기화하려면 해당 volume을 삭제해야 합니다.

---

## 🤖 4. AI 폰트 생성 설정

AI 폰트 생성은 vendored `fewshot-font-generation` 엔진의 **DM-Font**를 사용합니다.

- 기준 글자 수: 38자
- 기준 글자 순서: `fewshot-font-generation/write2font/ref_chars.json`
- 가중치 파일 위치: `fewshot-font-generation/write2font/pth/dm.pth`
- 실행 엔트리포인트: `fewshot-font-generation/write2font/run_pipeline.py`

업로드된 샘플 이미지는 `ref_chars.json` 순서대로 crop되며, DM-Font가 요구하는 검은 배경/흰 글자 형식으로 변환된 뒤 추론에 사용됩니다.

---

## 📖 5. 자서전 기능 설정

자서전 기능은 `autobiography/` 폴더의 Python CLI를 Spring Boot 백엔드가 subprocess로 실행하는 구조입니다.

Docker Compose 환경에서는 `./autobiography` 폴더가 백엔드 컨테이너의 `/workspace/autobiography`로 마운트됩니다.

- 환경변수 파일: `autobiography/.env`
- 예시 파일: `autobiography/.env.example`
- 생성 PDF 위치: `autobiography/output/`

자서전 PDF 생성 시 선택한 사용자 폰트가 있으면 해당 TTF를 우선 사용합니다. 숫자나 문장부호처럼 AI 폰트에 없는 glyph는 PDF 생성 과정에서 경고가 날 수 있습니다.

---

## 💻 6. 로컬 직접 실행

Docker Compose 전체 실행을 권장하지만, 필요하면 일부 서비스만 로컬에서 직접 실행할 수 있습니다.

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 백엔드

백엔드를 로컬에서 직접 실행할 때도 MySQL은 필요합니다.

```powershell
docker compose up -d mysql
cd backend
.\gradlew.bat bootRun
```

단, 폰트 생성과 자서전 기능은 native 도구와 Python 패키지 의존성이 많으므로 제출/시연 환경에서는 전체 Docker Compose 실행을 권장합니다.

---

## ✏️ 7. 코드 스타일 통일 설정

우리 프로젝트는 `.editorconfig`를 통해 들여쓰기와 줄 바꿈 규칙을 통일합니다. 팀원분들은 본인이 사용하는 IDE에 맞춰 아래 설정을 완료해 주세요.

### 🔹 VS Code

1. **확장 프로그램 설치**: `Extensions(Ctrl+Shift+X)`에서 "EditorConfig for VS Code"를 검색하여 설치합니다.
2. **저장 시 자동 정렬 활성화**:
   - `Ctrl + ,` 설정을 엽니다.
   - "Format On Save"를 검색합니다.
   - `Editor: Format On Save` 항목을 체크합니다.

### 🔹 IntelliJ

IntelliJ는 별도의 설치 없이 바로 작동하지만, 저장 시 자동 적용을 위해 아래 설정을 권장합니다.

1. `Settings` 또는 `Preferences` -> `Tools` -> `Actions on Save`로 이동합니다.
2. `Reformat code` 항목에 체크합니다.
3. `Optimize imports`에도 체크하여 안 쓰는 import 문을 자동으로 정리합니다.

---

## 🚫 8. Git에 올리면 안 되는 파일

아래 파일들은 Git에 커밋하지 않습니다.

- `.env` 파일
- `.pth`, `.pt`, `.ckpt` 등 AI 모델 weight 파일
- 업로드된 이미지와 생성된 폰트 파일
- 생성된 자서전 PDF
- `node_modules`, `.next`, Gradle build output, Python cache 파일

해당 파일들은 `.gitignore`와 `.dockerignore`에서 제외 처리되어 있습니다.
