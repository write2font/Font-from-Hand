from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
import os

def read_font(path):
    """폰트 파일을 읽어서 Pillow ImageFont 객체로 반환"""
    try:
        # MX-Font 모델 기본 크기 128
        return ImageFont.truetype(path, size=128)
    except Exception as e:
        print(f"Error reading font {path}: {e}")
        return None

def render(font, char):
    """글자를 이미지로 렌더링 (Pillow 10+ 호환 대응)"""
    try:
        # 1. Pillow 10.0.0 이상 대응 (getsize -> getbbox)
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox(char)
            if bbox:
                # bbox: (left, top, right, bottom)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                xy = (-bbox[0], -bbox[1])
            else:
                width, height = 10, 10
                xy = (0, 0)
        else:
            # 구버전 Pillow 호환
            width, height = font.getsize(char)
            xy = (0, 0)

        if width <= 0: width = 10
        if height <= 0: height = 10
            
        img = Image.new('L', (width, height), 0)
        draw = ImageDraw.Draw(img)
        draw.text(xy, char, font=font, fill=255)
        
        return img

    except Exception as e:
        # 렌더링 실패 시 빈 이미지 반환
        return Image.new('L', (128, 128), 0)

def get_filtered_chars(font_path, chars):
    """해당 폰트 파일이 실제로 지원하는 글자만 남기고 필터링"""
    try:
        # fontTools를 사용하여 폰트 내부의 문자맵(Cmap) 확인
        font = TTFont(font_path)
        cmap = font.getBestCmap()
        
        filtered_chars = []
        for char in chars:
            # 유니코드 코드가 폰트의 cmap에 존재하는지 확인
            if ord(char) in cmap:
                filtered_chars.append(char)
                
        return filtered_chars
        
    except Exception as e:
        print(f"Warning: Failed to filter chars for {font_path} ({e})")
        # 에러 발생 시, 일단 입력된 모든 글자를 반환 (학습 중단 방지)
        return chars
