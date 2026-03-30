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

    def _make_prompt(self, keywords, summary_text, cover_title=None) -> str:
        kw_str = ", ".join(keywords)
        title_line = f"'{cover_title}'" if cover_title else "한 여성의 삶"

        llm_prompt = (
            f"자서전 표지 일러스트를 위한 영문 이미지 생성 프롬프트를 만들어라.\n\n"
            f"자서전 제목: {title_line}\n"
            f"핵심 키워드: {kw_str}\n\n"
            f"[프롬프트 작성 규칙]\n"
            f"1. 제목의 정서를 자연 풍경(하늘, 들판, 나무, 빛, 바람, 꽃)으로 시각화\n"
            f"2. 스타일: Studio Ghibli inspired watercolor illustration\n"
            f"   - 부드럽고 따뜻한 색감, 섬세한 붓터치\n"
            f"   - 빛과 그림자가 아름다운 자연 풍경\n"
            f"   - 감성적이고 서정적인 분위기\n"
            f"3. 사람, 건물, 글자 절대 없음\n"
            f"4. 50단어 이내 영어로만. 프롬프트 텍스트만 출력.\n\n"
            f"좋은 예시:\n"
            f"'냇물' 제목 → 'gentle stream winding through lush green meadow, "
            f"soft morning sunlight filtering through willow branches, "
            f"Studio Ghibli style watercolor, warm golden tones'\n"
            f"'달리기' 제목 → 'wide open field under vast blue sky, "
            f"golden wheat swaying in wind, endless horizon, "
            f"Studio Ghibli style watercolor, hopeful warm light'"
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
                "warm golden afternoon light through tree canopy, "
                "soft breeze, lush greenery, Studio Ghibli style watercolor"
            )

        return (
            base
            + ", Studio Ghibli inspired watercolor illustration, "
            + "beautiful detailed brushwork, soft warm lighting, "
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
