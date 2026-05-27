# 🎨 FFH (Font From Hand) 프로젝트 가이드

이 프로젝트는 사용자의 손글씨를 분석하여 개인화된 폰트(.ttf)를 생성하고 관리하는 서비스입니다. **Next.js, Spring Boot, Python**이 결합된 모노레포 구조로 운영됩니다.

---

## 🛠 1. 공통 필수 설치 도구

개발 시작 전 본인 노트북에 아래 도구들을 반드시 설치해 주세요.

- **Java 17 (LTS)**: 백엔드 실행용 (Eclipse Temurin 권장)
- **Node.js (v18 이상)**: 프론트엔드 실행용
- **Python 3.9 이상**: AI 엔진 및 스크립트 실행용
- **Git**: 코드 버전 관리
- **Docker Desktop**: 폰트 생성 엔진 실행용

---

## 🚀 2. 초기 세팅 및 실행 순서

### 1단계: 프로젝트 클론

터미널을 열고 아래 명령어를 입력하여 프로젝트를 내려받습니다.

```bash
git clone [Organization 레포지토리 주소]
cd FFH
```

### 2단계: 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

- 접속: http://localhost:3000

### 3단계: Python 의존성 설치

폰트 엔진과 자서전 기능에 필요한 패키지를 설치합니다.

```bash
pip install -r font-engine/requirements.txt
pip install -r autobiography/requirements.txt
```

> **자서전 기능을 사용하는 경우** `autobiography/.env` 파일을 직접 생성해야 합니다.
> API 키 값은 팀 노션을 참고해 주세요.

### 4단계: Docker 및 폰트 엔진 준비

수동 스캔 폰트 생성과 AI 폰트 생성 기능을 사용하려면 Docker Desktop이 실행 중이어야 합니다.

백엔드를 IntelliJ에서 직접 실행하는 경우에도 폰트 엔진은 Docker 이미지를 호출하므로, 최초 1회 아래 명령어로 이미지를 빌드해 주세요.

```bash
docker compose build handwrite2350
docker compose build write2font-ai
```

### 5단계: 백엔드

- IntelliJ에서 FFH/backend 폴더만 선택하여 엽니다.
- Gradle 빌드 완료 후 FfhApplication을 실행합니다.
- 접속: http://localhost:8080

---

## 🤖 3. AI 폰트 모델 파일 설정

AI 폰트 생성에 필요한 모델 weight 파일은 용량 문제로 Git에 포함하지 않습니다. 팀 공유 드라이브에서 파일을 내려받아 아래 경로에 넣어 주세요.

```text
fewshot-font-generation/write2font/pth/last.pth
fewshot-font-generation/write2font/pth/last_lf.pth
```
기본 AI 모델은 MX-Font이며, 기본 weight 경로는 아래와 같습니다.

```
FONT_ENGINE_AI_MODEL=MX
FONT_ENGINE_AI_WEIGHT_PATH=write2font/pth/last.pth
```

## ✏️ 4. 코드 스타일 통일 설정

우리 프로젝트는 `.editorconfig`를 통해 들여쓰기와 줄 바꿈 규칙을 통일합니다. 팀원분들은 본인이 사용하는 IDE에 맞춰 아래 설정을 완료해 주세요.

### 🔹 VS Code

1. **확장 프로그램 설치**: `Extensions(Ctrl+Shift+X)`에서 "EditorConfig for VS Code"를 검색하여 설치합니다.
2. **저장 시 자동 정렬 활성화**:
   - `Ctrl + ,` (설정)를 누릅니다.
   - "Format On Save"를 검색합니다.
   - `Editor: Format On Save` 항목을 체크합니다.

### 🔹 IntelliJ

IntelliJ는 별도의 설치 없이 바로 작동하지만, 저장 시 자동 적용을 위해 아래 설정을 권장합니다.

1. `Settings` (또는 `Preferences`) -> `Tools` -> `Actions on Save`로 이동합니다.
2. `Reformat code` 항목에 체크합니다.
3. `Optimize imports`에도 체크하여 안 쓰는 import 문을 자동으로 정리합니다.