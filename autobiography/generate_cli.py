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
        writing_style    = data.get("writing_style", "서술체")
        gender           = data.get("gender", "")
        military_service = data.get("military_service", "")
        education        = data.get("education", "")
        religion         = data.get("religion", "")

        # Q번호 붙이기 — seg_map에서 Q1, Q2... 패턴으로 매핑하기 위해
        numbered_questions = [f"Q{i+1}. {q}" for i, q in enumerate(questions)]
        segments = [
            {"question": nq, "answer": transcriptions[i] if i < len(transcriptions) else ""}
            for i, nq in enumerate(numbered_questions)
            if i < len(transcriptions) and transcriptions[i].strip()
        ]

        meta_lines = f"이름: {name}\n생년월일: {birth}\n고향: {hometown}\n"
        if gender:           meta_lines += f"성별: {gender}\n"
        if military_service: meta_lines += f"병역: {military_service}\n"
        if education:        meta_lines += f"학력: {education}\n"
        if religion:         meta_lines += f"종교: {religion}\n"
        transcript_text = meta_lines + "\n"
        for seg in segments:
            transcript_text += f"{seg['question']}\n답변: {seg['answer']}\n\n"
        if followup_tx:
            transcript_text += "\n[추가 답변]\n" + "\n".join(t for t in followup_tx if t.strip())
        if free_text.strip():
            transcript_text += f"\n[직접 남긴 이야기]\n{free_text}"

        from src.nlp_processor import NLPProcessor
        from src.latex_renderer import LaTeXRenderer

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
            writing_style=writing_style,
            military_service=military_service,
            education=education,
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
        # 새 포맷: extra_images = [{"path": "...", "tag": "..."}]
        # 구 포맷: extra_image_paths = ["path1", ...]  (하위 호환)
        extra_images_raw = data.get("extra_images", None)
        if extra_images_raw is not None:
            tagged_images = extra_images_raw
        else:
            tagged_images = [{"path": p, "tag": ""} for p in data.get("extra_image_paths", [])]

        chapter_images = {}
        chapter_captions = {}
        if tagged_images:
            if config.OPENAI_API_KEY:
                chapter_images, chapter_captions = _assign_images_to_chapters(tagged_images, autobiography["chapters"])
            else:
                chapter_images = _assign_images_by_tag(tagged_images, autobiography["chapters"])
                if not chapter_images:
                    print("[이미지] OPENAI_API_KEY가 없고 tag도 없어 이미지 배정을 건너뜁니다.")

        pdf_path = LaTeXRenderer(user_id=user_id, font_path=font_path).generate(
            autobiography, cover_image_path=cover_image,
            chapter_images=chapter_images, chapter_captions=chapter_captions
        )
        print(json.dumps({"pdf_path": pdf_path}, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


def _assign_images_by_tag(tagged_images: list, chapters: list) -> dict:
    """OPENAI_API_KEY 없을 때 tag 키워드로 챕터 내용과 매칭해 배정."""
    chapter_images = {}
    assignable_idxs = [
        i for i, ch in enumerate(chapters)
        if not ch.get("is_prologue") and not ch.get("is_epilogue")
    ]
    used_chs: set[int] = set()
    unmatched: list[str] = []

    for item in tagged_images:
        img_path = item.get("path", "")
        tag = item.get("tag", "").strip()
        if not os.path.exists(img_path):
            continue
        if not tag:
            unmatched.append(img_path)
            continue

        tag_words = tag.replace(",", " ").lower().split()
        best_ch, best_score = None, 0
        for ch_idx in assignable_idxs:
            if ch_idx in used_chs:
                continue
            text = (chapters[ch_idx].get("title", "") + " " +
                    chapters[ch_idx].get("content", "")[:400]).lower()
            score = sum(1 for w in tag_words if w in text)
            if score > best_score:
                best_score, best_ch = score, ch_idx

        if best_ch is not None and best_score > 0:
            chapter_images[best_ch] = img_path
            used_chs.add(best_ch)
            print(f"[이미지] 태그 매칭: '{tag}' → 챕터{best_ch}({chapters[best_ch]['title']})")
        else:
            unmatched.append(img_path)

    # 태그 없거나 매칭 실패한 이미지 → 빈 챕터에 순서대로 배정
    for img_path in unmatched:
        for ch_idx in assignable_idxs:
            if ch_idx not in used_chs:
                chapter_images[ch_idx] = img_path
                used_chs.add(ch_idx)
                print(f"[이미지] 미매칭 순차 배정: {os.path.basename(img_path)} → 챕터{ch_idx}")
                break

    return chapter_images


def _assign_images_to_chapters(tagged_images: list, chapters: list) -> tuple:
    """각 이미지를 챕터에 배치하고 캡션을 생성한다.
    tagged_images: [{"path": str, "tag": str}, ...]
    Returns: ({챕터인덱스: 이미지경로}, {챕터인덱스: 캡션텍스트})
    """
    import json as _json
    import re as _re
    import config
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

    chapter_images  = {}
    chapter_captions = {}

    # 프롤로그·에필로그 제외한 배정 가능 챕터만
    assignable_idxs = [
        i for i, ch in enumerate(chapters)
        if not ch.get("is_prologue") and not ch.get("is_epilogue")
    ]
    if not assignable_idxs:
        return chapter_images, chapter_captions

    # ── 1단계: 이미지 설명 수집 ──────────────────────────────────────────────
    img_descs  = []
    valid_items = []
    for item in tagged_images:
        img_path = item.get("path", "")
        tag      = item.get("tag", "").strip()
        if not os.path.exists(img_path):
            continue
        try:
            if tag:
                img_desc = tag
                print(f"[이미지] 태그 사용: {os.path.basename(img_path)} → {tag}")
            else:
                with open(img_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                ext  = os.path.splitext(img_path)[1].lower().lstrip(".")
                mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
                desc_resp = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                        {"type": "text", "text": (
                            "이 사진에 무엇이 담겨 있나요? "
                            "사람, 장소, 시기(어린 시절/학창 시절/청년/중년 등), 분위기를 한국어로 2~3문장으로 설명해주세요."
                        )},
                    ]}],
                    max_tokens=200,
                )
                img_desc = desc_resp.choices[0].message.content.strip()
                print(f"[이미지] Vision 분석: {os.path.basename(img_path)} → {img_desc[:60]}")
            img_descs.append(img_desc)
            valid_items.append(item)
        except Exception as e:
            print(f"[이미지] Vision 분석 실패 ({os.path.basename(img_path)}): {e} → 파일명으로 대체")
            img_descs.append(os.path.splitext(os.path.basename(img_path))[0])
            valid_items.append(item)

    if not valid_items:
        return chapter_images, chapter_captions

    # ── 2단계: 전체 이미지↔챕터 동시 최적 배정 (LLM 1회 호출) ──────────────
    chapter_list_str = "\n".join(
        f"{i}. {chapters[i].get('title', '')} — {chapters[i].get('content', '')[:200]}"
        for i in assignable_idxs
    )
    img_list_str = "\n".join(
        f"{j}. {desc}" for j, desc in enumerate(img_descs)
    )
    assign_prompt = (
        f"사진 목록:\n{img_list_str}\n\n"
        f"챕터 목록 (프롤로그·에필로그 제외):\n{chapter_list_str}\n\n"
        f"각 사진을 내용이 가장 잘 어울리는 챕터에 배정하라. "
        f"한 챕터에 사진 하나씩만, 겹치지 않게. "
        f"사진보다 챕터가 적으면 일부 사진은 배정하지 않아도 된다.\n"
        f"JSON만 출력: {{\"assignments\": [{{\"image\": 0, \"chapter\": 챕터번호}}, ...]}}"
    )
    assignments: dict[int, int] = {}  # img_idx → ch_idx
    try:
        assign_resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": assign_prompt}],
            max_tokens=300,
        )
        raw = assign_resp.choices[0].message.content.strip()
        raw = _re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
        data = _json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        used_chs: set[int] = set()
        for entry in data.get("assignments", []):
            img_idx = int(entry["image"])
            ch_idx  = int(entry["chapter"])
            if (0 <= img_idx < len(valid_items)
                    and ch_idx in assignable_idxs
                    and ch_idx not in used_chs):
                assignments[img_idx] = ch_idx
                used_chs.add(ch_idx)
                print(f"[이미지] 배정: 사진{img_idx} → 챕터{ch_idx}({chapters[ch_idx]['title']})")
    except Exception as e:
        print(f"[이미지] 전체 배정 실패 ({e}), 순차 폴백")
        used_chs = set()
        for j in range(len(valid_items)):
            for ch_i in assignable_idxs:
                if ch_i not in used_chs:
                    assignments[j] = ch_i
                    used_chs.add(ch_i)
                    break

    # ── 3단계: 캡션 생성 후 결과 저장 ────────────────────────────────────────
    for img_idx, ch_idx in assignments.items():
        item        = valid_items[img_idx]
        img_path    = item.get("path", "")
        tag         = item.get("tag", "").strip()
        img_desc    = img_descs[img_idx]
        chapter_title = chapters[ch_idx]["title"]

        chapter_images[ch_idx] = img_path

        # 태그 20자 이하면 그대로, 길거나 없으면 LLM으로 15자 이내 캡션 생성
        if tag and len(tag) <= 20:
            caption = tag
        else:
            caption = _generate_caption(client, img_desc, chapter_title)
        if caption:
            chapter_captions[ch_idx] = caption

    return chapter_images, chapter_captions


def _generate_caption(client, img_desc: str, chapter_title: str) -> str:
    """이미지 설명 + 챕터 제목으로 15자 이내 명사형 캡션을 생성한다."""
    try:
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": (
                f"사진 설명: {img_desc}\n챕터 제목: {chapter_title}\n\n"
                "이 사진에 붙일 캡션을 한국어로 15자 이내 명사형으로만 출력하라. "
                "예) '어린 시절 가족과 함께' / '첫 직장 동료들과' / '고향 마을 전경'"
            )}],
            max_tokens=30,
        )
        caption = resp.choices[0].message.content.strip().strip('"\'.')
        print(f"[이미지] 캡션: {caption}")
        return caption
    except Exception as e:
        print(f"[이미지] 캡션 생성 실패: {e}")
        return ""


if __name__ == "__main__":
    main()
