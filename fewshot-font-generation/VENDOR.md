# Vendored DM-Font 엔진

이 디렉터리는 Font-from-Hand에서 사용하는 few-shot font generation 엔진을 프로젝트 안에 포함한 vendored copy입니다.

- 원본 저장소: https://github.com/write2font/fewshot-font-generation
- 2026-06-07 기준 확인한 upstream HEAD: `34747767d0ddbf63b10fe7a136799afecf81b0de`
- 현재 애플리케이션에서 사용하는 모델: DM-Font only
- 런타임 엔트리포인트: `write2font/run_pipeline.py`
- 필요한 로컬 weight 경로: `write2font/pth/dm.pth`

## vendored copy로 둔 이유

애플리케이션에서는 업로드된 기준 글자 이미지를 crop하고, DM-Font 추론을 실행한 뒤, 생성된 PNG 글리프를 TTF로 변환하는 프로젝트 전용 연결 코드가 필요합니다.

따라서 이 디렉터리는 원본 저장소를 그대로 둔 clean checkout이 아니라, Font-from-Hand 실행을 위해 일부 파일이 추가/수정된 vendored engine입니다.

원본 저장소의 변경사항을 반영해야 한다면 upstream과 직접 비교한 뒤, `write2font/` 아래의 Font-from-Hand 전용 변경사항을 의도적으로 다시 적용해 주세요.

## Docker build 범위

저장소에는 추적 가능성을 위해 엔진 소스를 포함하지만, Docker 런타임에는 DM-Font 실행 경로만 필요합니다.

루트 `.dockerignore`와 이 디렉터리의 `.dockerignore`는 Docker build context에서 사용하지 않는 LF/MX/FUNIT 모델 코드, 문서, 노트북, 학습 스크립트, 비한국어 샘플 데이터를 제외합니다.
