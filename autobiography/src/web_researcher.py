"""
src/web_researcher.py
실제 뉴스/역사 정보 검색기 (Tavily API)

지역 입력 형식:
  --region "충청남도 연기군 전의면"
  --region "전라북도 전주시 완산구"
  --region "경상남도 거제시"
  --region "서울 마포구"
"""

import os
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError("pip install tavily-python 을 먼저 실행하세요.")


class WebResearcher:

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY", "")
        if not api_key:
            raise ValueError(".env 파일에 TAVILY_API_KEY 를 추가해주세요.")
        self.client = TavilyClient(api_key)

    def _clean(self, text: str) -> str:
        """마크다운, HTML, 특수기호 제거하고 순수 텍스트만 남깁니다."""
        text = re.sub(r"#{1,6}\s*", "", text)
        text = re.sub(r"\*+", "", text)
        text = re.sub(r"\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"<.*?>", "", text)
        text = re.sub(r"[-─]{3,}", "", text)
        text = re.sub(r"\|.*?\|", "", text)
        text = re.sub(r"[\.]{4,}", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # URL 제거
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"/edit/\S+", "", text)
        return text.strip()

    def _search(self, query: str, max_results: int = 3) -> str:
        try:
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
            )
            results = []
            for r in response.get("results", []):
                content = r.get("content", "").strip()
                if content:
                    cleaned = self._clean(content)
                    if cleaned:
                        results.append(cleaned[:400])
            return "\n".join(results)
        except Exception as e:
            print(f"[Web] ⚠️  검색 실패 ({query}): {e}")
            return ""

    def parse_region(self, region: str) -> dict:
        """
        지역명을 도/시군/면읍동으로 파싱합니다.

        입력 예:
          "충청남도 연기군 전의면"  → {도: "충청남도", 시군: "연기군", 면읍동: "전의면"}
          "전라북도 전주시"         → {도: "전라북도", 시군: "전주시", 면읍동: ""}
          "전의면"                  → {도: "", 시군: "", 면읍동: "전의면"}
        """
        parts = region.strip().split()
        result = {"도": "", "시군": "", "면읍동": "", "전체": region}

        for p in parts:
            if re.search(r"(도|특별시|광역시|특별자치시|특별자치도)$", p):
                result["도"] = p
            elif re.search(r"(시|군|구)$", p):
                result["시군"] = p
            elif re.search(r"(면|읍|동|리)$", p):
                result["면읍동"] = p

        # 파싱 안 된 경우 전체를 면읍동으로
        if not any([result["도"], result["시군"], result["면읍동"]]):
            result["면읍동"] = region

        print(f"[Web] 지역 파싱: {result}")
        return result

    def research(self, region: str, birth_year: str) -> dict:
        """
        지역 + 출생연도 기반으로 실제 역사/문화 정보를 수집합니다.
        """
        parsed = self.parse_region(region)
        decade = f"{birth_year[:3]}0년대"

        # 검색에 쓸 지역 조합
        small  = parsed["면읍동"] or parsed["시군"] or region   # 가장 작은 단위
        medium = " ".join(filter(None, [parsed["도"], parsed["시군"]])) or region
        large  = parsed["도"] or region

        print(f"[Web] 검색 중: {region} / {decade}...")

        region_history = self._search(f"{small} 역사 유래 지명", max_results=2)
        if not region_history:
            region_history = self._search(f"{medium} 역사 유래", max_results=2)

        era_background = self._search(f"한국 {decade} 농촌 생활상 서민 사회", max_results=2)

        local_culture  = self._search(f"{large} 전통 문화 풍습 음식 사투리", max_results=2)
        if not local_culture:
            local_culture = self._search(f"충청도 전통 문화 풍습", max_results=2)

        landmarks = self._search(f"{small} 장소 냇가 시장 학교 지명", max_results=2)
        if not landmarks:
            landmarks = self._search(f"{medium} 명소 하천 시장", max_results=2)

        era_events = self._search(f"한국 {decade} 6.25 전후 역사 사건 농촌", max_results=2)

        result = {
            "region_history": region_history or f"{region}은 유서 깊은 고을이다.",
            "era_background": era_background or f"{decade}는 전쟁 이후 재건의 시대였다.",
            "local_culture":  local_culture  or f"{large} 특유의 정겨운 풍습이 있었다.",
            "landmarks":      landmarks      or f"{small} 일대의 냇가와 들판, 장터.",
            "era_events":     era_events     or "6.25 이후 국가 재건과 경제 성장의 시대.",
        }

        print(f"[Web] 수집 완료 ✓")
        return result
