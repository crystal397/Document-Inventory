"""가상 건설감정 자료 폴더 트리 생성기.

원칙 9(가상 데이터만 사용)를 지키기 위해 개발·테스트용 가짜 자료를 만든다.
파일 '내용'은 의미 없는 무작위 바이트다. 1단계 스캐너가 보는 것은 메타데이터
(이름, 확장자, 크기, 수정일, 폴더 구조)뿐이므로 내용은 필요 없다.

사용법:
    python tools/make_fake_dataset.py                  # fake_data/ 에 일반 파일 200개
    python tools/make_fake_dataset.py --files 50000    # 성능 테스트용
    python tools/make_fake_dataset.py --out D:/tmp/fake --seed 7

테스트 코드에서는 generate_dataset() 함수를 직접 호출한다.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# 1. 결과 기록용 데이터 구조
#    생성기가 "무엇을 만들었는지" 목록(manifest)을 돌려주면,
#    테스트는 스캐너 결과를 이 목록과 비교해 정답 여부를 판단할 수 있다.
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FakeFile:
    """생성된 파일 하나의 정보 (frozen=True: 만든 뒤 값 변경 불가)."""

    rel_path: str  # 루트 기준 상대경로, '/' 구분. 디스크에 만든 이름 그대로(NFD 등 포함)
    kind: str  # "regular" 또는 특수 사례 종류 ("nfd", "mojibake", "noise" ...)
    size: int  # 바이트
    mtime: datetime  # 수정일 (UTC)


@dataclass
class FakeDataset:
    """생성 결과 전체."""

    root: Path
    files: list[FakeFile] = field(default_factory=list)
    empty_dirs: list[str] = field(default_factory=list)

    def by_kind(self, kind: str) -> list[FakeFile]:
        return [f for f in self.files if f.kind == kind]


# ─────────────────────────────────────────────────────────────
# 2. 일반 파일: 감정 자료 폴더 구조와 파일명 규칙
# ─────────────────────────────────────────────────────────────

# 가상 수정일 범위
DATE_START = datetime(2019, 1, 1, tzinfo=UTC)
DATE_END = datetime(2024, 12, 31, tzinfo=UTC)

LETTER_SUBJECTS = ["공기연장요청", "설계변경통보", "준공검사요청", "하자보수요청", "기성금청구"]


def _random_datetime(rng: random.Random) -> datetime:
    span = int((DATE_END - DATE_START).total_seconds())
    return DATE_START + timedelta(seconds=rng.randint(0, span))


# 각 함수는 rng(난수 생성기)를 받아 확장자 없는 파일명(stem)을 돌려준다.
def _contract_name(rng: random.Random) -> str:
    return rng.choice(
        ["공사도급계약서", "하도급계약서", f"변경계약서_제{rng.randint(1, 9)}차", "계약특수조건"]
    )


def _drawing_name(rng: random.Random) -> str:
    return rng.choice(
        [
            f"{rng.randint(101, 115)}동_{rng.randint(1, 25)}층_평면도",
            f"단면도_{rng.randint(1, 40):02d}",
            f"구조도_S-{rng.randint(1, 300):03d}",
            f"입면도_{rng.choice('동서남북')}측",
        ]
    )


def _photo_name(rng: random.Random) -> str:
    return rng.choice(
        [
            f"IMG_{rng.randint(1, 9999):04d}",
            f"DSC{rng.randint(1, 99999):05d}",
            f"현장사진_{_random_datetime(rng):%Y%m%d}_{rng.randint(1, 99):02d}",
        ]
    )


def _letter_name(rng: random.Random) -> str:
    return f"공문_{_random_datetime(rng):%Y%m%d}_{rng.choice(LETTER_SUBJECTS)}"


def _estimate_name(rng: random.Random) -> str:
    return rng.choice(
        [
            f"공사비내역서_{rng.randint(1, 5)}차",
            "물량산출서",
            "단가산출서",
            f"기성내역_{rng.randint(1, 30)}회",
        ]
    )


def _misc_name(rng: random.Random) -> str:
    return f"{rng.choice(['회의록', '참고자료', '검토의견', '백업'])}_{rng.randint(1, 99):02d}"


# 하위 폴더 이름 → (확장자 후보, 파일명 생성 함수)
FOLDERS: dict[str, tuple[tuple[str, ...], Callable[[random.Random], str]]] = {
    "01_계약서": ((".pdf", ".hwp", ".docx"), _contract_name),
    "02_설계도면": ((".dwg", ".dxf", ".pdf"), _drawing_name),
    "03_현장사진": ((".jpg", ".png", ".heic"), _photo_name),
    "04_공문": ((".pdf", ".hwp", ".hwpx"), _letter_name),
    "05_내역서": ((".xlsx", ".xls", ".csv"), _estimate_name),
    "06_기타": ((".zip", ".txt", ".7z"), _misc_name),
}


# ─────────────────────────────────────────────────────────────
# 3. 특수 사례: 스캐너가 반드시 올바르게 처리해야 하는 까다로운 파일들
#    (README 8장, 9장의 예상 문제를 재현)
# ─────────────────────────────────────────────────────────────

CASE1 = "사건_가상001"
SPECIAL = f"{CASE1}/99_특수사례"


def _nfd(text: str) -> str:
    """'가' → 'ㄱ'+'ㅏ' 처럼 한글을 자모로 분해한 형태(macOS 방식)로 바꾼다."""
    return unicodedata.normalize("NFD", text)


def _mojibake(text: str, wrong_codec: str) -> str:
    """한글을 cp949 바이트로 바꾼 뒤 '잘못된 코덱'으로 읽어 깨진 이름을 재현한다.

    예: Windows에서 만든 ZIP을 다른 환경에서 풀 때 실제로 생기는 현상.
    """
    return text.encode("cp949").decode(wrong_codec)


def special_cases() -> list[tuple[str, str]]:
    """(상대경로, 종류) 목록. 결과가 항상 같도록 난수를 쓰지 않는다."""
    # macOS 파일명 한도는 255바이트. 한글은 글자당 3바이트(UTF-8)이므로 78자 + '.pdf' = 238바이트
    long_stem = ("공사비감정보고서" * 10)[:78]
    deep_dir = "/".join(f"{i:02d}_하위폴더" for i in range(1, 11))  # 폴더 깊이 10단계

    return [
        # 한글 정규화 (NFD)
        (f"{SPECIAL}/{_nfd('현장_확인서.pdf')}", "nfd"),
        (f"{SPECIAL}/{_nfd('공사_일지_2023.hwp')}", "nfd"),
        # 깨진 파일명 (mojibake)
        (f"{SPECIAL}/{_mojibake('공사계약서', 'cp437')}.pdf", "mojibake"),
        (f"{SPECIAL}/{_mojibake('하도급대금', 'latin-1')}.hwp", "mojibake"),
        # 특수문자
        (f"{SPECIAL}/㈜가상건설_견적서.pdf", "special_char"),
        (f"{SPECIAL}/①번_도면_검토.dwg", "special_char"),
        (f"{SPECIAL}/면적산출_120㎡.xlsx", "special_char"),
        (f"{SPECIAL}/전각\u3000공백_문서.hwp", "special_char"),  # U+3000 전각 공백
        (f"{SPECIAL}/현장사진_📷_001.jpg", "special_char"),
        (f"{SPECIAL}/工事契約書.pdf", "special_char"),
        (f"{SPECIAL}/보고서(최종)[수정본].pdf", "special_char"),
        # 확장자 변형
        (f"{SPECIAL}/2024.03.15_회의록.v2.hwp", "multi_dot"),
        (f"{SPECIAL}/SCAN_0001.PDF", "upper_ext"),
        (f"{SPECIAL}/배치도.DWG", "upper_ext"),
        (f"{SPECIAL}/메모", "no_ext"),
        # 크기 0
        (f"{SPECIAL}/빈파일.txt", "empty_file"),
        # 길이·깊이
        (f"{SPECIAL}/{long_stem}.pdf", "long_name"),
        (f"{SPECIAL}/{deep_dir}/깊은위치_문서.pdf", "deep"),
        # 잡음 파일 (OS·Office가 자동으로 만드는 파일)
        (f"{CASE1}/03_현장사진/Thumbs.db", "noise"),
        (f"{CASE1}/.DS_Store", "noise"),
        (f"{CASE1}/desktop.ini", "noise"),
        (f"{CASE1}/05_내역서/~$공사비내역서_1차.xlsx", "noise"),
        # 숨김 파일 (macOS/Linux 방식: 이름이 '.'으로 시작)
        (f"{CASE1}/.숨김_메모.txt", "hidden"),
    ]


EMPTY_DIRS = [f"{CASE1}/07_빈폴더"]


# ─────────────────────────────────────────────────────────────
# 4. 생성 로직
# ─────────────────────────────────────────────────────────────


def _collision_key(rel_path: str) -> str:
    """Windows·macOS는 대소문자와 NFC/NFD 차이를 '같은 이름'으로 본다.

    그래서 디스크에서 충돌할 이름인지 판단할 때는 둘 다 정규화해서 비교한다.
    """
    return unicodedata.normalize("NFC", rel_path).casefold()


def _unique_path(parent: str, stem: str, ext: str, used: set[str]) -> str:
    """이미 쓴 이름이면 '_(2)', '_(3)' ... 을 붙여 겹치지 않게 한다."""
    candidate = f"{parent}/{stem}{ext}"
    n = 2
    while _collision_key(candidate) in used:
        candidate = f"{parent}/{stem}_({n}){ext}"
        n += 1
    used.add(_collision_key(candidate))
    return candidate


def _ensure_empty_target(root: Path) -> None:
    """안전장치: 비어 있지 않은 폴더에는 절대 생성하지 않는다.

    실수로 실제 자료 폴더를 지정했을 때 가짜 파일이 섞여 들어가는 사고를 막는다.
    """
    if root.exists():
        if not root.is_dir():
            raise FileExistsError(f"폴더가 아닌 파일이 이미 있습니다: {root}")
        if any(root.iterdir()):
            raise FileExistsError(f"대상 폴더가 비어 있지 않습니다: {root}")
    root.mkdir(parents=True, exist_ok=True)


def _write_file(root: Path, rel_path: str, size: int, mtime: datetime, rng: random.Random) -> None:
    path = root / rel_path  # pathlib은 '/' 구분 문자열을 Windows에서도 올바르게 처리한다
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rng.randbytes(size))
    # 수정일을 과거 날짜로 바꾼다. (이 생성기가 방금 만든 가짜 파일에만 적용)
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


def generate_dataset(
    root: Path,
    *,
    n_files: int = 200,
    n_cases: int = 3,
    seed: int = 42,
    max_size: int = 8192,
) -> FakeDataset:
    """가상 자료 트리를 root 아래에 만들고, 만든 목록을 돌려준다.

    Args:
        root: 생성할 폴더. 없거나 비어 있어야 한다.
        n_files: 일반 파일 개수. 특수 사례 파일은 이와 별도로 항상 추가된다.
        n_cases: 가상 사건 폴더 개수.
        seed: 난수 시드. 같은 시드 → 항상 같은 결과 (테스트 재현성).
        max_size: 일반 파일의 최대 크기(바이트).
    """
    if n_files < 0 or n_cases < 1:
        raise ValueError("n_files는 0 이상, n_cases는 1 이상이어야 합니다.")

    root = Path(root)
    _ensure_empty_target(root)

    # random.Random(seed): 전역 난수와 분리된 '나만의' 난수 생성기.
    # 시드가 같으면 뽑히는 숫자 순서가 항상 같다.
    rng = random.Random(seed)
    dataset = FakeDataset(root=root)
    used: set[str] = set()
    cases = [f"사건_가상{i:03d}" for i in range(1, n_cases + 1)]
    folder_names = list(FOLDERS)

    # (1) 특수 사례 먼저 — 이름을 선점해 일반 파일과 겹치지 않게 한다.
    for rel_path, kind in special_cases():
        used.add(_collision_key(rel_path))
        size = 0 if kind == "empty_file" else rng.randint(64, 1024)
        mtime = _random_datetime(rng)
        _write_file(root, rel_path, size, mtime, rng)
        dataset.files.append(FakeFile(rel_path, kind, size, mtime))

    # (2) 빈 폴더
    for rel_dir in EMPTY_DIRS:
        (root / rel_dir).mkdir(parents=True, exist_ok=True)
        dataset.empty_dirs.append(rel_dir)

    # (3) 일반 파일
    for _ in range(n_files):
        folder = rng.choice(folder_names)
        extensions, make_name = FOLDERS[folder]
        mtime = _random_datetime(rng)
        parent = f"{rng.choice(cases)}/{folder}"
        if rng.random() < 0.3:  # 30%는 한 단계 더 깊은 하위 폴더에 둔다
            sub = (
                f"{mtime:%Y-%m}"
                if folder == "03_현장사진"
                else rng.choice(["원본", "사본", "검토본"])
            )
            parent = f"{parent}/{sub}"

        rel_path = _unique_path(parent, make_name(rng), rng.choice(extensions), used)
        size = rng.randint(64, max_size)
        _write_file(root, rel_path, size, mtime, rng)
        dataset.files.append(FakeFile(rel_path, "regular", size, mtime))

    return dataset


# ─────────────────────────────────────────────────────────────
# 5. 명령행 실행
# ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="가상 건설감정 자료 폴더 트리를 생성합니다.")
    parser.add_argument(
        "--out", type=Path, default=Path("fake_data"), help="생성 위치 (기본: fake_data)"
    )
    parser.add_argument("--files", type=int, default=200, help="일반 파일 개수 (기본: 200)")
    parser.add_argument("--cases", type=int, default=3, help="가상 사건 폴더 개수 (기본: 3)")
    parser.add_argument("--seed", type=int, default=42, help="난수 시드 (기본: 42)")
    args = parser.parse_args(argv)

    try:
        dataset = generate_dataset(args.out, n_files=args.files, n_cases=args.cases, seed=args.seed)
    except (FileExistsError, ValueError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    kinds = Counter(f.kind for f in dataset.files)
    total_size = sum(f.size for f in dataset.files)
    print(f"생성 완료: {dataset.root.resolve()}")
    print(f"  파일 {len(dataset.files):,}개, 빈 폴더 {len(dataset.empty_dirs)}개")
    print(f"  총 크기 {total_size:,} 바이트")
    for kind, count in sorted(kinds.items()):
        print(f"  - {kind}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
