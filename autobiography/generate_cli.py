"""
generate_cli.py - Spring Boot subprocess용 자서전 생성 CLI 래퍼
사용법: python3 generate_cli.py <json_file_path>
입력 JSON:
  {
    "name": "이름",
    "birth": "YYYY-MM-DD",
    "hometown": "고향 주소",
    "user_id": "사용자 ID",
    "questions": ["Q2. 부모님은...", ...],
    "transcriptions": ["답변1", "답변2", ...],
    "followup_transcriptions": ["추가답변1", ...],
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "title": "자서전 제목",        (비어있으면 AI가 자동 생성)
    "cover_image_path": "/path/to/image.jpg"  (선택)
  }
출력: {"pdf_path": "/path/to/output.pdf"}  (JSON, stdout)
"""

import os
import sys
import json
import base64
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
        free_text     = data.get("free_text", "") or ""
        cover_image   = data.get("cover_image_path", None)
        font_path     = data.get("font_path", None)

        # Q번호 붙이기 — seg_map에서 Q1, Q2... 패턴으로 매핑하기 위해
        numbered_questions = [f"Q{i+1}. {q}" for i, q in enumerate(questions)]
        segments = [
            {"question": nq, "answer": transcriptions[i] if i < len(transcriptions) else ""}
            for i, nq in enumerate(numbered_questions)
            if i < len(transcriptions) and transcriptions[i].strip()
        ]

        transcript_text = f"이름: {name}\n생년월일: {birth}\n고향: {hometown}\n\n"
        for seg in segments:
            transcript_text += f"{seg['question']}\n답변: {seg['answer']}\n\n"
        if followup_tx:
            transcript_text += "\n[추가 답변]\n" + "\n".join(t for t in followup_tx if t.strip())
        if free_text.strip():
            transcript_text += f"\n[직접 남긴 이야기]\n{free_text}"

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

        nlp = NLPProcessor()
        autobiography = nlp.generate_autobiography(
            transcript_text=transcript_text,
            birth_date_str=birth,
            user_name=name,
            region_info=region_info,
            selected_keywords=keywords if keywords else None,
            segments=segments,
        )
        if title.strip():
            autobiography["cover_title"] = title.strip()
        autobiography["hometown"] = hometown
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
            except Exception as e:
                print(f"[이미지] 표지 생성 실패 (건너뜀): {e}")
                cover_image = None

        # 이미지 분석 및 챕터 배치
        extra_images = data.get("extra_image_paths", [])
        chapter_images = {}
        if extra_images and config.OPENAI_API_KEY:
            chapter_images = _assign_images_to_chapters(extra_images, autobiography["chapters"])

        pdf_path = PDFGenerator(user_id=user_id, font_path=font_path).generate(
            autobiography, cover_image_path=cover_image, chapter_images=chapter_images
        )
        print(json.dumps({"pdf_path": pdf_path}, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


def _assign_images_to_chapters(image_paths: list, chapters: list) -> dict:
    """각 이미지를 Vision API로 분석 후 LLM이 가장 어울리는 챕터에 배치. {챕터인덱스: 이미지경로}"""
    import config
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

    chapter_images = {}
    used_chapters = set()

    # 챕터 목록 (인덱스 포함)
    chapter_list = "\n".join(
        f"{i}. {ch.get('title', '')} — {ch.get('content', '')[:80]}"
        for i, ch in enumerate(chapters)
    )

    for img_path in image_paths:
        if not os.path.exists(img_path):
            continue
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = os.path.splitext(img_path)[1].lower().lstrip(".")
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

            # 이미지 내용 분석
            desc_resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": (
                            "이 사진에 무엇이 담겨 있나요? "
                            "사람, 장소, 시기(어린 시절/학창 시절/청년/중년 등), 분위기를 한국어로 2~3문장으로 설명해주세요."
                        )},
                    ],
                }],
                max_tokens=200,
            )
            img_desc = desc_resp.choices[0].message.content.strip()
            print(f"[이미지] 분석: {img_path} → {img_desc[:80]}")

            # 이미 사용된 챕터 제외한 후보 목록
            available = [
                f"{i}. {chapters[i].get('title', '')} — {chapters[i].get('content', '')[:80]}"
                for i in range(len(chapters))
                if i not in used_chapters
            ]
            if not available:
                break

            available_str = "\n".join(available)
            match_resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{
                    "role": "user",
                    "content": (
                        f"사진 설명: {img_desc}\n\n"
                        f"아래 챕터 목록 중 이 사진이 가장 잘 어울리는 챕터의 번호(숫자만)를 답하라.\n\n"
                        f"{available_str}\n\n"
                        "숫자 하나만 출력."
                    ),
                }],
                max_tokens=5,
            )
            raw = match_resp.choices[0].message.content.strip()
            try:
                best_idx = int("".join(c for c in raw if c.isdigit()))
                if best_idx < 0 or best_idx >= len(chapters):
                    best_idx = None
            except ValueError:
                best_idx = None

            if best_idx is not None and best_idx not in used_chapters:
                chapter_images[best_idx] = img_path
                used_chapters.add(best_idx)
                print(f"[이미지] 배치: 챕터 {best_idx}({chapters[best_idx]['title']}) ← {os.path.basename(img_path)}")

        except Exception as e:
            print(f"[이미지] 분석 실패 ({img_path}): {e}")

    return chapter_images


if __name__ == "__main__":
    main()
