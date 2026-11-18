"""pathutils.py 테스트.

@pytest.mark.parametrize 로 (입력, 기대값) 표를 나열하면,
pytest가 표의 각 행을 별도 테스트로 실행하고 실패한 행만 정확히 알려준다.
"""

import unicodedata
from pathlib import Path

import pytest
from make_fake_dataset import _mojibake, special_cases

from doc_inventory.pathutils import (
    analyze_name,
    is_hidden_name,
    looks_like_mojibake,
    safe_text,
    split_extension,
    split_rel_path,
    to_nfc,
    to_rel_posix,
)


def nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


# ── NFC 정규화 ───────────────────────────────────────────


def test_nfc_unchanged():
    assert to_nfc("현장_확인서.pdf") == ("현장_확인서.pdf", False)


def test_nfd_is_composed():
    decomposed = nfd("현장_확인서.pdf")
    assert len(decomposed) > len("현장_확인서.pdf")  # 자모로 분해되어 글자 수가 늘어남
    text, changed = to_nfc(decomposed)
    assert text == "현장_확인서.pdf"
    assert changed is True


def test_nfc_makes_equal_and_sorts_correctly():
    """정규화 전에는 같은 이름이 다르게 취급되고 정렬도 틀어진다 (README 9장 7번)."""
    names = ["나_도면.dwg", nfd("가_계약서.pdf"), "다_사진.jpg"]
    assert nfd("가_계약서.pdf") != "가_계약서.pdf"
    normalized = sorted(to_nfc(n)[0] for n in names)
    assert normalized == ["가_계약서.pdf", "나_도면.dwg", "다_사진.jpg"]


def test_nfc_changes_compatibility_hanja():
    """NFC는 한글 외에도 '호환 한자'를 바꾼다 → 플래그가 True가 되는 다른 경우."""
    compat = "豈"  # 豈 (호환 한자)
    text, changed = to_nfc(compat)
    assert changed is True
    assert text == "豈"  # 豈 (통합 한자) — 모양은 같고 코드만 다름


# ── 안전한 문자열 ─────────────────────────────────────────


def test_safe_text_normal():
    assert safe_text("정상_파일.pdf") == ("정상_파일.pdf", False)


def test_safe_text_replaces_surrogate():
    raw = "깨진\udcff바이트.pdf"  # macOS/Linux에서 잘못된 바이트가 들어온 형태
    with pytest.raises(UnicodeEncodeError):
        raw.encode("utf-8")  # 그대로는 저장 불가

    text, changed = safe_text(raw)
    assert changed is True
    assert text == "깨진\\udcff바이트.pdf"
    text.encode("utf-8")  # 이제 저장 가능 (예외 없음)


# ── 깨진 이름 추정 ────────────────────────────────────────


@pytest.mark.parametrize("codec", ["cp437", "cp1252", "latin-1"])
@pytest.mark.parametrize("original", ["공사계약서", "하도급대금", "현장사진_001", "준공 검사"])
def test_detects_cp949_mojibake(original, codec):
    """cp949 한글을 잘못된 코덱으로 읽은 이름을 감지한다."""
    try:
        broken = _mojibake(original, codec)
    except UnicodeDecodeError:
        pytest.skip(f"{codec}로 표현할 수 없는 바이트 포함")  # cp1252 미정의 바이트
    assert looks_like_mojibake(broken + ".pdf")


def test_detects_utf8_read_as_cp1252():
    """UTF-8 한글을 cp1252로 읽은 경우 (예: 'ê³µì‚¬')."""
    broken = "공사계약서".encode().decode("cp1252", errors="ignore")
    assert looks_like_mojibake(broken + ".pdf")


def test_detects_replacement_character():
    assert looks_like_mojibake("계약�.pdf")


@pytest.mark.parametrize(
    "name",
    [
        "IMG_0001.jpg",
        "계약서.pdf",
        "工事契約書.pdf",  # 한자
        "㈜가상건설_견적서.pdf",
        "①번_도면.dwg",
        "면적산출_120㎡.xlsx",
        "현장사진_📷_001.jpg",
        "Café_menu.pdf",  # 서유럽 문자
        "Résumé.docx",
        "Größe_Tabelle.xlsx",
        "Àlex.pdf",  # cp949로 읽으면 우연히 한글 1글자가 되는 이름
        "naïve.txt",
        "Ångström.dat",
    ],
)
def test_no_false_positive(name):
    assert not looks_like_mojibake(name)


def test_generated_names_classified_correctly(tmp_path):
    """생성기의 모든 특수 사례·일반 파일에 대해: 깨진 이름만 감지되어야 한다."""
    from make_fake_dataset import generate_dataset

    dataset = generate_dataset(tmp_path / "d", n_files=500, seed=3)
    for f in dataset.files:
        name = f.rel_path.rsplit("/", 1)[1]
        assert looks_like_mojibake(name) == (f.kind == "mojibake"), name


# ── analyze_name: 전체 흐름 ───────────────────────────────


def test_analyze_name_nfd():
    info = analyze_name(nfd("현장_확인서.pdf"))
    assert info.text == "현장_확인서.pdf"
    assert (info.was_nfd, info.had_invalid_chars, info.suspect_mojibake) == (True, False, False)


def test_analyze_name_invalid_bytes():
    info = analyze_name("문서\udc80.pdf")
    assert info.had_invalid_chars is True
    info.text.encode("utf-8")  # 저장 가능


def test_analyze_every_special_case():
    """생성기 특수 사례 전부를 분석해도 예외 없이 저장 가능한 문자열이 나와야 한다."""
    for rel_path, kind in special_cases():
        info = analyze_name(rel_path.rsplit("/", 1)[1])
        info.text.encode("utf-8")
        assert unicodedata.is_normalized("NFC", info.text)
        assert info.was_nfd == (kind == "nfd")
        assert info.suspect_mojibake == (kind == "mojibake")


# ── 경로 분해 ────────────────────────────────────────────


def test_to_rel_posix(tmp_path):
    root = tmp_path / "root"
    path = root / "사건A" / "01_계약서" / "계약서.pdf"
    assert to_rel_posix(path, root) == "사건A/01_계약서/계약서.pdf"  # Windows에서도 '/'


def test_to_rel_posix_outside_root(tmp_path):
    with pytest.raises(ValueError):
        to_rel_posix(Path(tmp_path / "other" / "a.pdf"), tmp_path / "root")


@pytest.mark.parametrize(
    ("rel", "expected"),
    [
        ("사건A/01_계약서/계약서.pdf", ("사건A/01_계약서", "계약서.pdf", 2)),
        ("사건A/메모.txt", ("사건A", "메모.txt", 1)),
        ("메모.txt", ("", "메모.txt", 0)),
    ],
)
def test_split_rel_path(rel, expected):
    assert split_rel_path(rel) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("계약서.pdf", ".pdf"),
        ("SCAN_0001.PDF", ".pdf"),  # 대문자 → 소문자
        ("배치도.DWG", ".dwg"),
        ("2024.03.15_회의록.v2.hwp", ".hwp"),  # 점이 여러 개
        ("archive.tar.gz", ".gz"),  # 마지막 확장자만
        ("메모", ""),  # 확장자 없음
        (".DS_Store", ""),  # 숨김 파일 (확장자 아님)
        (".숨김_메모.txt", ".txt"),  # 숨김 + 확장자
        ("file.", ""),  # 점으로 끝남
        ("...", ""),
    ],
)
def test_split_extension(name, expected):
    assert split_extension(name) == expected


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (".DS_Store", True),
        (".숨김_메모.txt", True),
        ("계약서.pdf", False),
        ("~$내역서.xlsx", False),
    ],
)
def test_is_hidden_name(name, expected):
    assert is_hidden_name(name) == expected


def test_common_hangul_is_exactly_ks_x_1001():
    """'자주 쓰는 한글' 판별 기준이 KS X 1001 완성형 2,350자와 정확히 일치해야 한다."""
    from doc_inventory.pathutils import _is_common_hangul

    all_syllables = [chr(c) for c in range(ord("가"), ord("힣") + 1)]
    assert len(all_syllables) == 11172
    assert sum(_is_common_hangul(ch) for ch in all_syllables) == 2350
    assert _is_common_hangul("공") and not _is_common_hangul("뢮")
