"""경로·파일명 처리용 순수 함수 모음.

'순수 함수'란 같은 입력에 항상 같은 출력을 내고, 바깥(파일시스템, 전역 변수)을
건드리지 않는 함수다. 이 모듈의 함수는 디스크에 접근하지 않으므로
테스트가 빠르고, 어느 OS에서 실행해도 결과가 같다.

한글 파일명 관련 배경은 README 9장 참고.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 1. 유니코드 정규화 (NFC)
# ─────────────────────────────────────────────────────────────


def to_nfc(text: str) -> tuple[str, bool]:
    r"""NFC(조합형)로 정규화하고, 원래 값이 달랐는지 함께 돌려준다.

    >>> to_nfc("가")          # 이미 NFC
    ('가', False)
    >>> to_nfc("가")  # ㄱ + ㅏ (NFD)
    ('가', True)

    주의: NFC 정규화는 한글 자모 결합 외에도 일부 문자를 바꾼다.
    예) 한자 '호환 문자'(U+F900~U+FAFF)는 같은 모양의 통합 한자로 바뀐다.
    그래서 두 번째 값은 정확히 말해 'NFC가 아니었음'을 뜻한다.
    """
    # is_normalized()는 normalize()보다 빠르다. 대부분의 이름은 이미 NFC이므로 먼저 확인한다.
    if unicodedata.is_normalized("NFC", text):
        return text, False
    return unicodedata.normalize("NFC", text), True


# ─────────────────────────────────────────────────────────────
# 2. 저장 가능한 문자열로 변환 (잘못된 바이트 처리)
# ─────────────────────────────────────────────────────────────


def safe_text(text: str) -> tuple[str, bool]:
    r"""UTF-8로 저장할 수 없는 문자(짝 없는 surrogate)를 '\udcXX' 표기로 바꾼다.

    배경:
        macOS/Linux에서 파일명 바이트가 UTF-8로 유효하지 않으면, Python은 이름을
        버리지 않고 해당 바이트를 surrogate 문자(U+DC80~U+DCFF)로 바꿔서 str로 준다.
        Windows에서도 짝이 맞지 않는 UTF-16 이름은 같은 형태로 들어올 수 있다.
        이 문자들은 화면 출력이나 SQLite 저장 시 UnicodeEncodeError를 일으킨다.

    돌려주는 값은 '기록용'이다. 실제 파일에 접근할 때는 원래 문자열을 그대로 써야 한다.

    >>> safe_text("정상.pdf")
    ('정상.pdf', False)
    >>> safe_text("bad\udcff.pdf")
    ('bad\\udcff.pdf', True)
    """
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return text.encode("utf-8", errors="backslashreplace").decode("utf-8"), True
    return text, False


# ─────────────────────────────────────────────────────────────
# 3. 깨진 이름(mojibake) 추정
# ─────────────────────────────────────────────────────────────

# 한글 바이트를 '잘못 읽을 때' 흔히 쓰이는 코덱
#   cp437   : ZIP 표준의 기본 인코딩. 압축 프로그램이 한글 이름을 이것으로 풀면 '░°╗τ'
#   cp1252  : 서유럽 Windows 기본 인코딩
#   latin-1 : 서유럽 표준 인코딩. '°ø»ç' 형태
_WRONG_CODECS = ("cp437", "cp1252", "latin-1")
# 원래 한글을 저장했던 인코딩 후보
_KOREAN_CODECS = ("cp949", "utf-8")
_MIN_HANGUL_SYLLABLES = 2


def _count_hangul_syllables(text: str) -> int:
    return sum("가" <= ch <= "힣" for ch in text)


def _is_common_hangul(ch: str) -> bool:
    """KS X 1001 완성형 2,350자(실제 문서에서 쓰는 거의 모든 한글)에 속하는지.

    한글 음절은 11,172자지만, 나머지 8,822자('뢮', '봫' 등)는 실제로 거의 쓰이지 않는다.
    cp949에서 완성형 2,350자는 첫 바이트 0xB0~0xC8, 둘째 바이트 0xA1~0xFE 범위에 있다.
    (참고: Python의 euc-kr 코덱은 드문 글자도 8바이트 조합형으로 인코딩해 버려서 판별에 못 쓴다)
    """
    if not ("가" <= ch <= "힣"):
        return False
    lead, trail = ch.encode("cp949")
    return 0xB0 <= lead <= 0xC8 and 0xA1 <= trail <= 0xFE


def _count_common_hangul(text: str) -> int:
    return sum(_is_common_hangul(ch) for ch in text)


def looks_like_mojibake(name: str) -> bool:
    """파일명이 '한글이 잘못된 인코딩으로 읽혀 깨진 것'으로 보이면 True.

    원리 — 깨지는 과정을 거꾸로 되돌려 본다:
        깨질 때:   "공사" →(cp949로 저장)→ b'\\xb0\\xf8\\xbb\\xe7' →(cp437로 읽음)→ "░°╗τ"
        되돌릴 때: "░°╗τ" →(cp437로 다시 바이트화)→ b'\\xb0\\xf8\\xbb\\xe7' →(cp949로 읽음)→ "공사"
        되돌린 결과에 한글 음절이 나오면 깨진 이름으로 의심한다.

    오탐(정상 이름을 깨졌다고 판단) 방지:
        - 이미 한글이 들어 있는 이름은 깨진 이름이 아니다.
        - 'Ångström'은 cp437 → cp949로 되돌리면 우연히 '뢮gstr봫'이 된다.
          그래서 '자주 쓰는 한글 2,350자'가 2글자 이상 복원될 때만 의심한다.
        - 그래도 추정이므로 결과는 '의심' 표시로만 쓴다.
    """
    if "�" in name:  # '�'(대체 문자): 디코딩에 실패한 흔적 → 확실히 깨짐
        return True
    if name.isascii() or _count_hangul_syllables(name) > 0:
        return False

    for wrong in _WRONG_CODECS:
        try:
            raw = name.encode(wrong)
        except UnicodeEncodeError:
            continue  # 이 코덱으로 만들 수 없는 문자가 있음 → 이 코덱으로 깨진 게 아님
        for korean in _KOREAN_CODECS:
            try:
                restored = raw.decode(korean)
            except UnicodeDecodeError:
                continue
            if _count_common_hangul(restored) >= _MIN_HANGUL_SYLLABLES:
                return True
    return False


# ─────────────────────────────────────────────────────────────
# 4. 파일명 분석 (위 함수들을 한 번에)
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class NameInfo:
    text: str  # 저장용 이름 (안전 변환 + NFC 정규화 완료)
    was_nfd: bool
    had_invalid_chars: bool
    suspect_mojibake: bool


def analyze_name(raw: str) -> NameInfo:
    """파일명 하나를 저장용으로 정리하고 진단 플래그를 붙인다.

    순서가 중요하다: ① 잘못된 문자를 먼저 안전하게 바꾼 뒤 ② NFC 정규화 ③ 깨짐 추정.
    """
    safe, had_invalid = safe_text(raw)
    nfc, was_nfd = to_nfc(safe)
    return NameInfo(
        text=nfc,
        was_nfd=was_nfd,
        had_invalid_chars=had_invalid,
        suspect_mojibake=looks_like_mojibake(nfc),
    )


# ─────────────────────────────────────────────────────────────
# 5. 경로 분해
# ─────────────────────────────────────────────────────────────


def to_rel_posix(path: Path, root: Path) -> str:
    """root 기준 상대경로를 '/' 구분 문자열로 바꾼다.

    Windows는 '\\', macOS는 '/'를 쓰지만, DB에는 OS와 무관하게 같은 형태로 저장해야
    다른 PC에서 만든 스캔 결과와 비교할 수 있다.

    path가 root 밖에 있으면 ValueError.
    """
    return path.relative_to(root).as_posix()


def split_rel_path(rel_posix: str) -> tuple[str, str, int]:
    """'/' 구분 상대경로를 (상위 폴더, 파일명, 깊이)로 나눈다.

    >>> split_rel_path("사건A/01_계약서/계약서.pdf")
    ('사건A/01_계약서', '계약서.pdf', 2)
    >>> split_rel_path("메모.txt")
    ('', '메모.txt', 0)
    """
    parent, _, name = rel_posix.rpartition("/")
    depth = rel_posix.count("/")
    return parent, name, depth


def split_extension(name: str) -> str:
    """소문자 확장자(점 포함)를 돌려준다. 없으면 "".

    >>> split_extension("SCAN_0001.PDF")
    '.pdf'
    >>> split_extension("2024.03.15_회의록.v2.hwp")   # 마지막 점 뒤만 확장자
    '.hwp'
    >>> split_extension(".DS_Store")                  # 맨 앞 점은 '숨김' 표시이지 확장자가 아님
    ''

    pathlib의 Path.suffix를 쓰지 않고 직접 구현한 이유:
        'file.' 처럼 점으로 끝나는 이름의 처리가 Python 버전마다 달라서,
        규칙을 명확히 고정하기 위해서다.
    """
    body = name.lstrip(".")
    base, dot, ext = body.rpartition(".")
    if not dot or not base or not ext:
        return ""
    return "." + ext.lower()


def is_hidden_name(name: str) -> bool:
    """이름 규칙상 숨김 파일인지 (macOS/Linux: '.'으로 시작).

    Windows의 '숨김' 속성은 이름이 아니라 파일 속성이므로 metadata 모듈에서 따로 확인한다.
    """
    return name.startswith(".")
