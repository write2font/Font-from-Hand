# graduation_project

## 폴더 내 녹음 파일(Whisper) 전사

### 1) 환경 준비

- Python: 3.8+
- FFmpeg: 설치되어 있어야 합니다 (`ffmpeg -version` 으로 확인)

의존성 설치:

```bash
python3 -m pip install -r requirements.txt
```

### 2) 전사 실행

아래 폴더들을 읽어서 전사 결과를 `data/02_transcripts/` 아래에 저장합니다.

- 입력: `data/01_raw_audio/할머니/`, `data/01_raw_audio/할아버지/`
- 출력: `data/02_transcripts/할머니/`, `data/02_transcripts/할아버지/`

실행:

```bash
python3 main.py
```

### 3) 키워드 추출 실행

전사 결과(`data/02_transcripts/`)에서 키워드를 뽑아 `data/03_keywords/`에 저장합니다.

```bash
python3 keywords.py
```

### 4) 요약 생성 실행

전사 결과(`data/02_transcripts/`)를 바탕으로 간단한 요약(핵심 문장/청크)을 생성해 `data/03_summaries/`에 저장합니다.

```bash
python3 summaries.py
```

### 5) Q/A 분리 + (답변 기반) 키워드 추출

전사 텍스트를 1~15번 질문 기준으로 Q/A로 나눈 뒤, **답변(A)만** 대상으로 키워드를 뽑습니다.

- Q/A 저장: `data/04_qa/<화자>/`
- 키워드 저장: `data/03_keywords_qa/<화자>/`

```bash
python3 qa_keywords.py
```

### 3) 동작 방식(요약)

- `src/stt_engine.py`의 `STTEngine.transcribe_folder()`가 폴더 내 오디오(`.m4a`, `.mp3`, `.wav` 등)를 찾아 같은 파일명으로 `.txt`를 생성합니다.
- 이미 동일 경로의 `.txt`가 있으면 기본값으로 스킵합니다(덮어쓰기 X).
- `src/keyword_extractor.py`의 `KeywordExtractor.extract_folder()`가 `.txt` 파일별 키워드와 폴더 전체 요약 키워드를 생성합니다.
- `src/summarizer.py`의 `Summarizer`가 키워드 점수를 활용해 extractive 요약을 생성합니다.
- `src/qa_parser.py`가 전사를 질문 번호 마커(예: `첫번째`, `10번`)로 분리하고, `qa_keywords.py`가 답변 단위 키워드를 생성합니다.
