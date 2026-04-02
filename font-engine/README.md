# font-engine (2444 mapping + tight spacing, fast fix)

이 버전은 이전 버전에서 느렸던 부분을 줄인 수정본입니다.

바뀐 점:
- 기본값으로 `normalized_png` 저장을 끔
- FontForge 진행 로그가 콘솔에 바로 보이도록 수정
- `removeOverlap()` / `correctDirection()` 제거
- 정규화 캔버스를 1024 → 512로 축소
- 래스터 단계 진행 로그 추가

## 실행

```powershell
cd font-engine
python main.py "C:\path\to\input_pages" "C:\path\to\output\MyFont.ttf" --rows 14 --cols 10 --family-name MyHandFont
```

정규화 PNG까지 저장하고 싶을 때만:

```powershell
python main.py "C:\path\to\input_pages" "C:\path\to\output\MyFont.ttf" --rows 14 --cols 10 --save-normalized-debug
```


## 속도 관련 옵션

- 기본적으로 potrace를 병렬 실행합니다. `--workers 8`처럼 워커 수를 조절할 수 있습니다.
- 중간 PBM 파일은 기본적으로 완료 후 삭제합니다. 유지하려면 `--keep-pbm`을 사용하세요.

예시:

```powershell
python main.py "..\input_pages" "..\output\MyFont.ttf" --rows 14 --cols 10 --family-name MyHandFont --workers 8
```
