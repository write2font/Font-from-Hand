import os, sys, subprocess, cv2, numpy as np, uuid
from PIL import Image, ImageOps

if len(sys.argv) < 3:
    print("Usage: python main.py <input_dir> <output_ttf>")
    sys.exit(1)

INPUT_DIR = sys.argv[1] 
OUTPUT_TTF = sys.argv[2]
BASE_DIR = os.path.dirname(OUTPUT_TTF)

CROP_DIR = os.path.join(BASE_DIR, "temp_crop")
SVG_DIR = os.path.join(BASE_DIR, "temp_svg")
POTRACE_PATH = "/opt/homebrew/bin/potrace"
FONTFORGE_PATH = "/opt/homebrew/bin/fontforge"

for d in [CROP_DIR, SVG_DIR]:
    if not os.path.exists(d): os.makedirs(d)

full_chars = list("!\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~")
korean_2350 = []
for i in range(0xB0, 0xC9):
    for j in range(0xA1, 0xFF):
        try:
            char = bytes([i, j]).decode('euc-kr')
            korean_2350.append(char)
        except: continue
full_chars += korean_2350[:2350]

img_files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
char_pointer = 0

for img_file in img_files:
    img_path = os.path.join(INPUT_DIR, img_file)
    img = Image.open(img_path)
    bw_img = img.convert("L")
    inverted = ImageOps.invert(bw_img)
    bbox = inverted.getbbox()
    
    if bbox:
        left, top, right, bottom = bbox
        rows, cols = 14, 10
        w, h = (right-left)/cols, (bottom-top)/rows
        
        for r in range(rows):
            for c in range(cols):
                if char_pointer >= len(full_chars): break
                
                p = 12
                char_img = img.crop((left+c*w+p, top+r*h+p, left+(c+1)*w-p, top+(r+1)*h-p))
                
                char = full_chars[char_pointer]
                u_code = hex(ord(char))[2:].upper().zfill(4)
                char_img.save(os.path.join(CROP_DIR, f"char_U{u_code}.png"))
                
                char_pointer += 1
    print(f"Log: {img_file} 이미지 글자 추출 완료 (현재까지 {char_pointer}자)")

print("Log: 이미지 최적화 및 SVG 변환 시작 (시간이 꽤 걸립니다)...")
for fn in os.listdir(CROP_DIR):
    if not fn.endswith(".png"): continue
    path = os.path.join(CROP_DIR, fn)
    cv_img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    
    _, binary = cv2.threshold(cv_img, 170, 255, cv2.THRESH_BINARY_INV)
    
    h_img, w_img = binary.shape
    mask = np.zeros((h_img + 2, w_img + 2), np.uint8)
    for i in range(5):
        for x in range(w_img):
            if binary[i, x] == 255: cv2.floodFill(binary, mask, (x, i), 0)
            if binary[h_img-1-i, x] == 255: cv2.floodFill(binary, mask, (x, h_img-1-i), 0)
        for y in range(h_img):
            if binary[y, i] == 255: cv2.floodFill(binary, mask, (i, y), 0)
            if binary[y, w_img-1-i] == 255: cv2.floodFill(binary, mask, (w_img-1-i, y), 0)

    cleaned = cv2.bitwise_not(binary)
    temp_bmp = path.replace(".png", ".bmp")
    cv2.imwrite(temp_bmp, cleaned)
    
    svg_path = os.path.join(SVG_DIR, fn.replace(".png", ".svg"))
    subprocess.run([POTRACE_PATH, "-s", temp_bmp, "-o", svg_path])
    os.remove(temp_bmp)

print("Log: TTF 파일 생성 중...")
temp_id = str(uuid.uuid4())[:8]
ff_script_path = os.path.join(BASE_DIR, "build_ttf.py")

ff_code = f"""import fontforge, os
font = fontforge.font()
font.fontname = "CustomFont_{temp_id}"
font.fullname = "Custom Handwriting {temp_id}"
font.familyname = "CustomFont_{temp_id}"
font.ascent = 800
font.descent = 200

svg_dir = r"{SVG_DIR}"
for fn in os.listdir(svg_dir):
    if not fn.endswith(".svg"): continue
    try:
        hex_str = fn.split("_U")[-1].split(".")[0]
        glyph = font.createChar(int(hex_str, 16))
        glyph.importOutlines(os.path.join(svg_dir, fn))
        glyph.simplify()
        glyph.correctDirection()
    except: continue

font.generate(r"{OUTPUT_TTF}")
"""

with open(ff_script_path, "w", encoding="utf-8") as f:
    f.write(ff_code)

subprocess.run([FONTFORGE_PATH, "-lang=py", "-script", ff_script_path])

print(f"Success: {OUTPUT_TTF} 생성 완료!")