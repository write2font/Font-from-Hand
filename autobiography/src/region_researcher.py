"""
src/region_researcher.py
지역 역사/문화 정보 수집기
- 저자의 고향 지역 정보를 LLM으로 수집
- 자서전 챕터에 시대적/지역적 맥락을 풍부하게 추가
"""

import os
import sys
import json
import re

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)


class RegionResearcher:

    def research(self, region: str, birth_year: str) -> dict:
        """
        지역명과 출생연도를 받아 자서전에 활용할 지역/시대 정보를 수집합니다.

        Returns:
            {
                "region_history":   str,  # 지역 역사 및 특징
                "era_background":   str,  # 출생연도 전후 시대적 배경
                "local_culture":    str,  # 지역 문화/풍습/특산물
                "landmarks":        str,  # 지역 대표 장소/건물
                "era_events":       str,  # 해당 시대 주요 사건들
            }
        """
        print(f"[Region] '{region}' 지역 정보 수집 중...")

        prompt = f"""'{region}'과 {birth_year}년대 한국에 대해 자서전 집필에 활용할 정보를 알려주세요.

다음 JSON 형식으로만 응답하세요 (코드블록 없이):
{{
  "region_history": "{region}의 역사, 지리적 특징, 행정 변천사 등 (200자 내외)",
  "era_background": "{birth_year}년대 ~ {int(birth_year)+20}년대 한국의 시대적 배경, 사회상 (200자 내외)",
  "local_culture": "{region} 또는 충남 지역의 전통 문화, 풍습, 특산물, 사투리 등 (150자 내외)",
  "landmarks": "{region} 또는 인근의 실제 장소, 산, 하천, 시장, 학교 등 (150자 내외)",
  "era_events": "{birth_year}년대 한국의 주요 역사적 사건들 (6.25 전쟁, 산업화 등) (200자 내외)"
}}"""

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        try:
            result = json.loads(raw)
            print(f"[Region] 수집 완료: {region}")
            return result
        except Exception as e:
            print(f"[Region] ⚠️  파싱 실패 ({e}), 기본값 사용")
            return {
                "region_history":  f"{region}은 충청남도에 위치한 유서 깊은 고을입니다.",
                "era_background":  f"{birth_year}년대는 한국 전쟁 직후 재건의 시대였습니다.",
                "local_culture":   "충남 지역 특유의 정겨운 풍습과 따뜻한 인심이 있었습니다.",
                "landmarks":       f"{region} 일대의 냇가와 들판, 장터가 삶의 중심이었습니다.",
                "era_events":      "6.25 전쟁 이후 국가 재건과 경제 성장의 시대였습니다.",
            }

    def extract_region_from_transcript(self, transcript_text: str) -> str:
        """트랜스크립트에서 고향 지역명을 추출합니다."""
        prompt = (
            f"다음 인터뷰 텍스트에서 저자의 고향 지역명을 추출하세요.\n"
            f"지역명만 짧게 답하세요 (예: '전의면', '대전 중구', '부산 동래').\n\n"
            f"텍스트:\n{transcript_text[:500]}"
        )
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
        )
        region = response.choices[0].message.content.strip()
        region = re.sub(r"[\"'\n]", "", region).strip()
        print(f"[Region] 추출된 고향: {region}")
        return region
