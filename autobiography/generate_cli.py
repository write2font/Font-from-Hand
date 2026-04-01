"""
generate_cli.py - Spring Boot subprocess용 자서전 생성 CLI 래퍼
사용법: python3 generate_cli.py <json_file_path>
입력 JSON:
  {
    "name": "홍길동",
    "birth": "1950-03-15",
    "hometown": "충남 공주시",
    "user_id": "abc123",
    "questions": ["Q2. 부모님은...", ...],
    "transcriptions": ["답변1", "답변2", ...],
    "followup_transcriptions": ["추가답변1", ...],
    "keywords": ["고향의 추억", "가족의 사랑", "청춘의 열정"],
    "title": "홍길동의 이야기",
    "cover_image_path": "/path/to/image.jpg"  (선택)
  }
출력: {"pdf_path": "/path/to/output.pdf"}  (JSON, stdout)
"""

import os
import sys
import json
from cli_utils import exit_error, load_json_file, setup_path

setup_path()
import config


def main():
    if len(sys.argv) < 2:
        exit_error("사용법: generate_cli.py <json_file_path>")

    try:
        data = load_json_file(sys.argv[1])

        name          = data["name"]
        birth         = data["birth"]
        hometown      = data.get("hometown", "")
        user_id       = data.get("user_id", "api_user")
        questions     = data.get("questions", [])
        transcriptions = data.get("transcriptions", [])
        followup_tx   = data.get("followup_transcriptions", [])
        keywords      = data.get("keywords", [])
        title         = data.get("title", "") or ""  # 비어있으면 AI가 자동 생성
        cover_image   = data.get("cover_image_path", None)

        segments = [
            {"question": q, "answer": transcriptions[i] if i < len(transcriptions) else ""}
            for i, q in enumerate(questions)
        ]

        transcript_text = f"이름: {name}\n생년월일: {birth}\n고향: {hometown}\n\n"
        for seg in segments:
            transcript_text += f"{seg['question']}\n{seg['answer']}\n\n"
        if followup_tx:
            transcript_text += "\n[추가 답변]\n" + "\n".join(followup_tx)

        from src.nlp_processor import NLPProcessor
        from src.pdf_generator import PDFGenerator

        region_info = None
        if hometown and os.getenv("TAVILY_API_KEY"):
            try:
                from src.web_researcher import WebResearcher
                birth_year  = birth.split("-")[0] if birth else "1950"
                region_info = WebResearcher().research(hometown, birth_year)
                print(f"[지역 정보] {hometown} 수집 완료")
            except Exception as e:
                print(f"[지역 정보] 수집 실패 (건너뜀): {e}")

        nlp = NLPProcessor(extended=False)
        autobiography = nlp.generate_autobiography(
            transcript_text=transcript_text,
            birth_date_str=birth,
            user_name=name,
            region_info=region_info,
            selected_keywords=keywords,
            segments=segments,
        )
        nlp.save_summary(autobiography, user_id)

        if not cover_image and config.OPENAI_API_KEY:
            try:
                from src.image_generator import ImageGenerator
                img_path     = os.path.join(config.OUTPUT_DIR, f"{user_id}_cover.png")
                summary_text = " ".join(
                    ch.get("content", "")[:100] for ch in autobiography["chapters"][:2]
                )
                cover_image = ImageGenerator().generate_cover_image(
                    user_name=name,
                    birth_year=autobiography.get("birth_year", 1950),
                    region=autobiography.get("region", hometown),
                    keywords=keywords,
                    summary_text=summary_text,
                    output_path=img_path,
                    cover_title=title,
                )
            except Exception:
                cover_image = None

        pdf_path = PDFGenerator(user_id=user_id).generate(autobiography, cover_image_path=cover_image)
        print(json.dumps({"pdf_path": pdf_path}, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
