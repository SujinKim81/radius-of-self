#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "people.json"
ARTICLE_ROOT = ROOT / "article"
KST = timezone(timedelta(hours=9))
DEFAULT_MODEL = "gpt-4.1"
OPENAI_URL = "https://api.openai.com/v1/responses"
PROTECTED_SLUGS = {"autumn-peltier"}

CANDIDATES = [
    {
        "slug": "xiye-bastida",
        "name_ko": "시예 바스티다",
        "name_en": "Xiye Bastida",
        "focus": "원주민 관점의 기후정의와 미래세대 책임",
    },
    {
        "slug": "vanessa-nakate",
        "name_ko": "버네사 나카테",
        "name_en": "Vanessa Nakate",
        "focus": "아프리카 기후정의와 보이지 않는 피해의 가시화",
    },
    {
        "slug": "helena-gualinga",
        "name_ko": "헬레나 구알링가",
        "name_en": "Helena Gualinga",
        "focus": "아마존 원주민 권리와 생태 방어",
    },
    {
        "slug": "mitzi-jonelle-tan",
        "name_ko": "미치 조넬 탄",
        "name_en": "Mitzi Jonelle Tan",
        "focus": "필리핀 기후정의와 식민주의 이후의 생태 책임",
    },
    {
        "slug": "ayisha-siddiqa",
        "name_ko": "아이샤 시디카",
        "name_en": "Ayisha Siddiqa",
        "focus": "기후정의, 인권, 미래세대의 정치적 목소리",
    },
    {
        "slug": "mari-copeny",
        "name_ko": "마리 코프니",
        "name_en": "Mari Copeny",
        "focus": "식수 정의와 지역 공동체 돌봄",
    },
    {
        "slug": "tokata-iron-eyes",
        "name_ko": "토카타 아이언 아이즈",
        "name_en": "Tokata Iron Eyes",
        "focus": "원주민 토지권, 물 보호, 청소년 운동",
    },
    {
        "slug": "nalleli-cobo",
        "name_ko": "날렐리 코보",
        "name_en": "Nalleli Cobo",
        "focus": "도시 환경정의와 공기, 건강, 계급 문제",
    },
    {
        "slug": "disha-ravi",
        "name_ko": "디샤 라비",
        "name_en": "Disha Ravi",
        "focus": "기후정의, 민주주의, 청년 시민권",
    },
    {
        "slug": "leah-namugerwa",
        "name_ko": "레아 나무게르와",
        "name_en": "Leah Namugerwa",
        "focus": "우간다 기후운동과 청소년 생태 시민성",
    },
    {
        "slug": "isra-hirsi",
        "name_ko": "이스라 히르시",
        "name_en": "Isra Hirsi",
        "focus": "기후정의와 인종, 계급, 세대의 교차성",
    },
    {
        "slug": "melati-wijsen",
        "name_ko": "멜라티 위즌",
        "name_en": "Melati Wijsen",
        "focus": "플라스틱 감축과 청소년 생태 실천",
    },
    {
        "slug": "sunaura-taylor",
        "name_ko": "수나우라 테일러",
        "name_en": "Sunaura Taylor",
        "focus": "장애권, 동물권, 의존성의 윤리",
    },
    {
        "slug": "alice-wong",
        "name_ko": "앨리스 웡",
        "name_en": "Alice Wong",
        "focus": "장애권, 돌봄, 기술과 접근성",
    },
    {
        "slug": "mariame-kaba",
        "name_ko": "마리암 카바",
        "name_en": "Mariame Kaba",
        "focus": "감옥 폐지, 비폭력, 공동체 책임",
    },
    {
        "slug": "mya-rose-craig",
        "name_ko": "마이아로즈 크레이그",
        "name_en": "Mya-Rose Craig",
        "focus": "조류 관찰, 생물다양성, 인종과 자연 접근성",
    },
]


class GenerationError(Exception):
    pass


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def today_kst() -> str:
    return datetime.now(KST).strftime("%Y.%m.%d")


def load_people() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GenerationError(f"data/people.json을 읽을 수 없습니다: {exc}") from exc
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and isinstance(raw.get("people"), list):
        return raw["people"]
    raise GenerationError("data/people.json은 배열이어야 합니다.")


def save_people(people: list[dict[str, Any]]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(people, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def existing_slugs() -> set[str]:
    slugs = set(PROTECTED_SLUGS)
    if ARTICLE_ROOT.exists():
        slugs.update(path.name for path in ARTICLE_ROOT.iterdir() if path.is_dir())
    return slugs


def select_candidate(people: list[dict[str, Any]]) -> dict[str, str]:
    used_slugs = {clean_text(item.get("slug")).lower() for item in people}
    used_names = {clean_text(item.get("name")).lower() for item in people if item.get("name")}
    used_slugs.update(existing_slugs())

    for candidate in CANDIDATES:
        names = {candidate["name_ko"].lower(), candidate["name_en"].lower()}
        if candidate["slug"] in used_slugs:
            continue
        if names & used_names:
            continue
        return candidate

    raise GenerationError("사용 가능한 새 인물 후보가 없습니다. CANDIDATES를 확장해 주세요.")


def response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "person_name",
            "slug",
            "summary",
            "intro",
            "sections",
            "translation_note",
            "lasting_sentences",
            "further_reading",
        ],
        "properties": {
            "person_name": {"type": "string"},
            "slug": {"type": "string"},
            "summary": {"type": "string"},
            "intro": {"type": "string"},
            "sections": {
                "type": "array",
                "minItems": 6,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["heading", "paragraphs"],
                    "properties": {
                        "heading": {"type": "string"},
                        "paragraphs": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4,
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "translation_note": {"type": "string"},
            "lasting_sentences": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {"type": "string"},
            },
            "further_reading": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "description", "url"],
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
            },
        },
    }


def build_input(candidate: dict[str, str], people: list[dict[str, Any]], date_text: str) -> list[dict[str, str]]:
    recent = [clean_text(item.get("name")) for item in people[:12] if item.get("name")]
    system = """
당신은 한국어 인물 에세이를 쓰는 편집자입니다. 반드시 웹 검색으로 사실을 확인한 뒤, 깊이 있는 장문 에세이를 JSON으로만 반환하세요.

문체:
- 한국어 존대말.
- 위키피디아식 생애 요약 금지.
- 보고서식 번호 나열 금지.
- 한 장면에서 시작하고, 구체적인 사건과 말과 활동으로 밀고 가세요.
- 추상적인 프로젝트 설명, "지능" 개념 설명, 불교·부처·연기 연결은 쓰지 마세요.
- 영어 표현은 독자가 읽기 힘들지 않게 되도록 한글 번역 또는 음역을 우선하세요.
- 사진은 생성하지 말고, 이미지 언급도 하지 마세요.

내용:
- 오늘의 인물과 한 줄 결론이 자연스럽게 드러나야 합니다.
- 삶의 핵심 장면 1~2개를 반드시 넣으세요.
- 대표 활동, 글, 연설, 캠페인, 제도적 역할 중 3~5개를 구체적으로 다루세요.
- 그 사람이 넓힌 윤리의 범위를 구체적 생활 장면으로 보여주세요.
- 비판적으로 볼 점과 한계도 한 섹션에 넣으세요.
- 한국어 번역서가 확인되면 제목·원제·저자·출판사를 쓰고, 확인되지 않으면 "확인된 한국어 번역서는 찾지 못했습니다."라고 쓰세요.
- "오늘 남는 문장"은 정확히 3개입니다.
- "더 읽을 자료"는 3~5개이며, 실제 확인한 URL만 넣으세요.
""".strip()

    user = {
        "date": date_text,
        "target_person": candidate,
        "already_covered_recently": recent,
        "never_select": ["Autumn Peltier", "오텀 펠티어"],
        "quality_reference": "오텀 펠티어 글처럼 장면, 구조적 질문, 구체적 사실, 비판적 단락이 있는 깊이와 분량으로 작성",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False, indent=2)},
    ]


def extract_output_text(response: dict[str, Any]) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    texts: list[str] = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if texts:
        return "\n".join(texts)
    raise GenerationError("OpenAI API 응답에서 텍스트를 찾지 못했습니다.")


def call_openai(candidate: dict[str, str], people: list[dict[str, Any]], date_text: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise GenerationError("OPENAI_API_KEY 환경변수가 없습니다. GitHub Secrets에 OPENAI_API_KEY를 추가해 주세요.")

    payload = {
        "model": os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        "input": build_input(candidate, people, date_text),
        "tools": [{"type": "web_search_preview"}],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "person_essay",
                "schema": response_schema(),
                "strict": True,
            }
        },
    }
    request = urllib.request.Request(
        OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GenerationError(f"OpenAI API 요청 실패 ({exc.code}): {detail[:1600]}") from exc
    except urllib.error.URLError as exc:
        raise GenerationError(f"OpenAI API에 연결할 수 없습니다: {exc}") from exc

    try:
        text = extract_output_text(json.loads(body))
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GenerationError(f"OpenAI 응답 JSON 파싱 실패: {body[:1600]}") from exc


def validate_generated(generated: dict[str, Any], candidate: dict[str, str]) -> None:
    if generated.get("slug") != candidate["slug"]:
        raise GenerationError("생성 결과의 slug가 선택한 인물과 다릅니다.")
    if len(generated.get("sections", [])) < 6:
        raise GenerationError("본문 섹션이 너무 적습니다.")
    paragraph_count = sum(len(section.get("paragraphs", [])) for section in generated["sections"])
    if paragraph_count < 14:
        raise GenerationError("본문 문단이 너무 적습니다.")
    if len(generated.get("lasting_sentences", [])) != 3:
        raise GenerationError("'오늘 남는 문장'은 정확히 3개여야 합니다.")
    if not 3 <= len(generated.get("further_reading", [])) <= 5:
        raise GenerationError("'더 읽을 자료'는 3~5개여야 합니다.")
    for item in generated["further_reading"]:
        if not clean_text(item.get("url")).startswith(("https://", "http://")):
            raise GenerationError("더 읽을 자료에는 실제 URL이 필요합니다.")

    visible = json.dumps(generated, ensure_ascii=False)
    forbidden = ["지능", "불교", "부처", "연기", "위키피디아"]
    found = [word for word in forbidden if word in visible]
    if found:
        raise GenerationError(f"금지한 추상 표현이 포함되었습니다: {', '.join(found)}")


def render_article(slug: str, date_text: str, generated: dict[str, Any]) -> str:
    sections = []
    for section in generated["sections"]:
        paragraphs = "\n".join(f"          <p>{html.escape(clean_text(p))}</p>" for p in section["paragraphs"])
        sections.append(
            f"""        <section>
          <h2>{html.escape(clean_text(section["heading"]))}</h2>
{paragraphs}
        </section>"""
        )

    sentences = "\n".join(
        f"          <li>{html.escape(clean_text(sentence))}</li>"
        for sentence in generated["lasting_sentences"]
    )
    readings = "\n".join(
        f'          <li><a href="{html.escape(clean_text(item["url"]), quote=True)}" target="_blank" rel="noopener">{html.escape(clean_text(item["title"]))}</a><br>{html.escape(clean_text(item["description"]))}</li>'
        for item in generated["further_reading"]
    )

    name = html.escape(clean_text(generated["person_name"]))
    summary = html.escape(clean_text(generated["summary"]))
    intro = html.escape(clean_text(generated["intro"]))
    translation_note = html.escape(clean_text(generated["translation_note"]))
    body = "\n\n".join(sections)

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="{name}에 관한 자아의 반경 인물 에세이">
  <title>{name} - 자아의 반경</title>
  <link rel="stylesheet" href="../../style.css">
</head>
<body>
  <main>
    <a class="back-link" href="../../">목록으로 돌아가기</a>

    <article class="essay-doc">
      <p class="date">{html.escape(date_text)}</p>
      <h1>{name}</h1>
      <p class="lead">{summary}</p>
      <p class="essay-intro">{intro}</p>

      <div class="essay-body">
{body}
      </div>

      <section class="info-box" aria-labelledby="translation-title">
        <h2 id="translation-title">한국어 번역서에 관하여</h2>
        <p>{translation_note}</p>
      </section>

      <section class="essay-note" aria-labelledby="sentences-title">
        <h2 id="sentences-title">오늘 남는 문장</h2>
        <ol>
{sentences}
        </ol>
      </section>

      <section class="reading-list" aria-labelledby="reading-title">
        <h2 id="reading-title">더 읽을 자료</h2>
        <ul>
{readings}
        </ul>
      </section>
    </article>
  </main>
</body>
</html>
"""


def page_url_for(path: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" not in repo:
        return f"https://sujinkim81.github.io/radius-of-self/{path}"
    owner, name = repo.split("/", 1)
    if name.lower() == f"{owner.lower()}.github.io":
        return f"https://{owner}.github.io/{path}"
    return f"https://{owner}.github.io/{name}/{path}"


def set_outputs(values: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={str(value).replace(chr(10), ' ').strip()}\n")


def main() -> int:
    try:
        people = load_people()
        candidate = select_candidate(people)
        date_text = today_kst()
        generated = call_openai(candidate, people, date_text)
        validate_generated(generated, candidate)

        slug = candidate["slug"]
        article_dir = ARTICLE_ROOT / slug
        article_file = article_dir / "index.html"
        if article_dir.exists() or article_file.exists():
            raise GenerationError(f"article/{slug}/가 이미 있어 덮어쓰지 않습니다.")

        article_dir.mkdir(parents=True, exist_ok=False)
        article_file.write_text(render_article(slug, date_text, generated), encoding="utf-8")

        entry = {
            "slug": slug,
            "name": clean_text(generated["person_name"]),
            "date": date_text,
            "summary": clean_text(generated["summary"]),
            "url": f"article/{slug}/",
            "tags": [candidate["focus"]],
        }
        people.insert(0, entry)
        save_people(people)

        page_path = f"article/{slug}/"
        page_url = page_url_for(page_path)
        set_outputs(
            {
                "person_name": entry["name"],
                "summary": entry["summary"],
                "page_url": page_url,
            }
        )
        print(f"오늘의 인물: {entry['name']}")
        print(f"한 줄 결론: {entry['summary']}")
        print(f"새 글 주소: {page_url}")
        return 0
    except GenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
