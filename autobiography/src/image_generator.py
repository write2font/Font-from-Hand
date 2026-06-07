"""
src/image_generator.py
충남대 Gateway 이미지 생성 API로 자서전 표지 이미지 생성
- 지브리 감성 + 수채화 일러스트 스타일
- 제목 은유적 자연 표현, 아름답고 따뜻한 분위기
"""

import os, sys, base64
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

try:
    import httpx
except ImportError:
    httpx = None

from openai import OpenAI
client_llm = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

IMAGE_API_URL = "https://factchat-cloud.mindlogic.ai/v1/gateway/images/generate/"
IMAGE_MODEL   = "gemini-2.5-flash-image"


class ImageGenerator:

    def generate_cover_image(self, user_name: str, birth_year: int,
                              region: str, keywords: list,
                              summary_text: str, output_path: str,
                              cover_title: str = None) -> str | None:
        if not config.OPENAI_API_KEY:
            print("[이미지] ⚠️  API 키 없음")
            return None
        if httpx is None:
            print("[이미지] ⚠️  httpx 미설치 → pip install httpx")
            return None

        print("[이미지] 표지 프롬프트 생성 중...")
        prompt = self._make_prompt(keywords)
        print(f"[이미지] 프롬프트: {prompt[:120]}...")

        print("[이미지] 충남대 Gateway로 이미지 생성 중... (10~30초)")
        return self._call_gateway(prompt, output_path)

    # 따뜻하고 서정적인 스타일 (수묵화·판화 제외)
    _STYLES = [
        ("watercolor", "soft watercolor illustration, warm pastel tones, gentle washes of color, dreamy and nostalgic mood, artistic book cover"),
        ("pencil_watercolor", "hand-drawn pencil sketch with loose watercolor washes, warm tones, imperfect organic feel, cozy sketchbook style"),
        ("gouache", "gouache illustration, warm earthy tones, painterly texture, soft light, nostalgic and heartfelt mood, book cover art"),
        ("oil_pastel", "oil pastel illustration, rich warm colors, textured strokes, soft glowing light, intimate and personal mood"),
    ]

    def _make_prompt(self, keywords) -> str:
        import random
        kw_str = ", ".join(keywords)

        _, style_desc = random.choice(self._STYLES)

        llm_prompt = (
            f"자서전 표지 일러스트를 위한 영문 이미지 생성 프롬프트를 만들어라.\n\n"
            f"핵심 키워드: {kw_str}\n"
            f"그림 스타일: {style_desc}\n\n"
            f"[프롬프트 작성 규칙]\n"
            f"1. 키워드의 감정·분위기·온도감을 자연/풍경으로 은유하라. 단어를 그대로 그리지 마라.\n"
            f"   예) '손' → 손의 온기를 암시하는 빛·불꽃·따뜻한 햇살로 표현\n"
            f"   예) '길' → 숲 사이 빛 드는 오솔길로 표현\n"
            f"2. 등장 요소: 자연(하늘, 들판, 나무, 빛, 바람, 꽃, 강, 산 등) + 사물(등불, 의자, 낡은 책 등)만 허용\n"
            f"3. 사람·손·발·신체 부위·건물·글자 절대 없음\n"
            f"4. 위에 지정된 그림 스타일을 반드시 반영할 것\n"
            f"5. 포토리얼리즘·3D렌더·디지털 느낌 완전 배제. 손으로 그린 느낌만.\n"
            f"6. 50단어 이내 영어로만. 프롬프트 텍스트만 출력.\n\n"
            f"예시 (키워드: 할머니, 치즈스틱, 어린 시절):\n"
            f"'warm kitchen window glowing at dusk, soft candlelight on wooden table, "
            f"autumn leaves outside, gentle amber light, {style_desc}'\n"
        )
        try:
            resp = client_llm.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": llm_prompt}],
                max_tokens=150,
                timeout=30,
            )
            base = resp.choices[0].message.content.strip().strip('"\'')
        except Exception as e:
            print(f"[이미지] 프롬프트 생성 실패 ({e}) → 기본값 사용")
            base = (
                "quiet village path at dusk, single lantern glowing, "
                f"autumn leaves drifting, {style_desc}"
            )

        return (
            base
            + f", {style_desc}, "
            + "no people, no hands, no feet, no body parts, no limbs, no buildings, "
            + "no text, no letters, no words, no title, no captions, no labels, "
            + "no dark banner, no title bar, no caption area, no text overlay, "
            + "hand-drawn illustration, not photorealistic, not 3D rendered"
        )

    def _call_gateway(self, prompt: str, output_path: str) -> str | None:
        try:
            client = httpx.Client(
                headers={
                    "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=60.0,
            )
            resp = client.post(IMAGE_API_URL, json={
                "model":            IMAGE_MODEL,
                "prompt":           prompt,
                "aspect_ratio":     "3:4",
                "number_of_images": 1,
            })
            resp.raise_for_status()
            data = resp.json()

            img_data = data["data"][0]["url"]
            if img_data.startswith("data:"):
                img_data = img_data.split(",", 1)[1]

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(img_data))

            tokens = data.get("usage", {}).get("total_tokens", "?")
            print(f"[이미지] ✓ 저장됨: {output_path} (토큰: {tokens})")
            return output_path

        except Exception as e:
            print(f"[이미지] ⚠️  생성 실패: {e}")
            return None
