import os
import json
import shutil

folder_path = "D:\projects\write2font/png"
json_path = "D:\projects\write2font/ref_chars.json"
backup_path = "D:\projects\write2font/ref_chars_backup.json"

# 1. 안전을 위해 기존 JSON 파일 백업
if os.path.exists(json_path):
    shutil.copy(json_path, backup_path)
    print("💾 기존 JSON 파일을 'ref_chars_backup.json'으로 백업했습니다.")

# 2. 폴더에서 실제 파일명(글자) 추출
file_chars = []
for filename in os.listdir(folder_path):
    if filename.lower().endswith('.png'):
        char = filename.split('.')[0]
        file_chars.append(char)

# 보기 좋게 정렬
file_chars.sort()

# 3. 추출한 글자 목록을 JSON 파일로 저장 (자소 분리된 상태 그대로)
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(file_chars, f, ensure_ascii=False, indent=4)

print(f"✅ 완료! 총 {len(file_chars)}개의 실제 파일명으로 JSON 파일이 업데이트되었습니다.")