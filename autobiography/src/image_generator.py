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
        prompt = self._make_prompt(keywords, summary_text, cover_title)
        print(f"[이미지] 프롬프트: {prompt[:120]}...")

        print("[이미지] 충남대 Gateway로 이미지 생성 중... (10~30초)")
        return self._call_gateway(prompt, output_path)

    # 매번 다른 스타일을 선택하기 위한 스타일 목록
    _STYLES = [
        ("watercolor", "soft watercolor illustration, delicate brushstrokes, translucent layers, gentle color washes"),
        ("oil_painting", "impressionist oil painting, rich textured brushwork, vibrant yet warm tones, painterly style"),
        ("korean_ink", "Korean ink wash painting, minimalist brushwork, misty mountains, subtle ink gradients, hanji texture"),
        ("gouache", "gouache illustration, flat warm colors, graphic yet painterly, folk art inspired"),
        ("pencil_sketch", "detailed pencil and watercolor sketch, soft hand-drawn lines, gentle color washes, intimate feel"),
    ]

    def _make_prompt(self, keywords, summary_text, cover_title=None) -> str:
        import random
        kw_str = ", ".join(keywords)
        title_line = f"'{cover_title}'" if cover_title else "한 사람의 삶"

        style_key, style_desc = random.choice(self._STYLES)

        llm_prompt = (
            f"자서전 표지 일러스트를 위한 영문 이미지 생성 프롬프트를 만들어라.\n\n"
            f"자서전 제목: {title_line}\n"
            f"핵심 키워드: {kw_str}\n"
            f"그림 스타일: {style_desc}\n\n"
            f"[프롬프트 작성 규칙]\n"
            f"1. 제목과 키워드의 정서를 자연/사물/풍경으로 시각화 (하늘, 들판, 나무, 빛, 바람, 꽃, 강, 산 등)\n"
            f"2. 위에 지정된 스타일을 반드시 반영할 것\n"
            f"3. 사람, 건물, 글자 절대 없음\n"
            f"4. 키워드마다 다른 장면이 나오도록 창의적으로 구성\n"
            f"5. 50단어 이내 영어로만. 프롬프트 텍스트만 출력.\n\n"
            f"예시 (키워드: 중장비, 고향, 성실):\n"
            f"'wide open construction site at golden hour, distant mountains, "
            f"warm dust in the air, {style_desc}'\n"
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
                "peaceful countryside path lined with wildflowers, "
                f"warm golden afternoon light through tree canopy, soft breeze, {style_desc}"
            )

        return (
            base
            + f", {style_desc}, "
            + "book cover art, no people, no buildings, no text, no letters, "
            + "high quality, masterpiece"
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
