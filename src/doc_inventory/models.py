"""데이터 구조 정의.

스캐너 → 메타데이터 → 분류기 → 저장소로 이어지는 파이프라인에서
모듈끼리 주고받는 '규격'을 이 파일에 모아 둔다.

왜 dict가 아니라 dataclass인가?
    record["szie"] 같은 오타는 dict에서는 실행해 봐야 알 수 있지만,
    dataclass에서는 record.szie 를 쓰는 순간 편집기와 ruff가 알려준다.
    또 필드 목록이 한곳에 문서처럼 정리된다.

frozen=True
    만든 뒤 값을 바꿀 수 없다(불변). 파이프라인 중간에서 누군가 몰래 값을 바꾸는
    버그를 원천 차단한다. 값을 바꾼 '새 객체'가 필요하면 dataclasses.replace()를 쓴다.

slots=True
    객체마다 속성 저장용 dict를 만들지 않아 메모리를 줄이고 속성 접근이 빨라진다.
    수만 개 레코드를 다루는 이 프로젝트에 적합하다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ErrorType(StrEnum):
    """스캔 중 발생할 수 있는 오류 종류.

    StrEnum은 문자열처럼 비교·저장되면서도, 허용된 값만 쓰도록 강제한다.
    (ErrorType.PERMISSION == "permission" 은 True)
    """

    PERMISSION = "permission"  # 접근 권한 없음
    NOT_FOUND = "not_found"  # 스캔 도중 파일이 사라짐
    PATH_TOO_LONG = "path_too_long"  # 경로 길이 제한 초과
    INVALID_NAME = "invalid_name"  # 유니코드로 표현할 수 없는 이름 (잘못된 바이트)
    OTHER = "other"


def _require_aware(value: datetime | None, field_name: str) -> None:
    """시간대 정보가 없는(naive) datetime을 거부한다.

    '2024-03-15 09:00'만으로는 한국 시간인지 UTC인지 알 수 없다.
    서로 다른 PC·OS에서 만든 기록을 비교하려면 모든 시각을 UTC로 통일해야 하므로,
    시간대가 빠진 값이 들어오면 즉시 오류로 알린다.
    """
    if value is not None and value.tzinfo is None:
        raise ValueError(f"{field_name}에는 시간대(UTC)가 있는 datetime이 필요합니다: {value!r}")


@dataclass(frozen=True, slots=True)
class FileRecord:
    """파일 하나의 메타데이터. 문자열 필드는 모두 NFC 정규화된 값이다."""

    rel_path: str  # 스캔 루트 기준 상대경로, '/' 구분 (예: "사건A/01_계약서/계약서.pdf")
    name: str  # 파일명 (예: "계약서.pdf")
    extension: str  # 소문자 확장자, 점 포함 (예: ".pdf"). 없으면 ""
    size_bytes: int
    modified_at: datetime  # 수정일 (UTC)
    created_at: datetime | None  # 생성일 (UTC). OS가 제공하지 않으면 None
    depth: int  # 루트로부터 폴더 깊이. 루트 바로 아래 파일은 0
    parent_dir: str  # 상위 폴더 상대경로. 루트면 ""
    is_hidden: bool
    name_was_nfd: bool  # 원래 이름이 NFC가 아니었는지 (대부분 macOS식 자모 분리 한글)
    name_suspect_mojibake: bool  # 깨진 이름으로 의심되는지 (추정값)
    category: str | None = None  # 분류기가 채운다. 분류 전에는 None

    def __post_init__(self) -> None:
        # __post_init__은 dataclass가 객체를 만든 직후 자동으로 호출한다 → 값 검증에 사용
        if self.size_bytes < 0:
            raise ValueError(f"size_bytes는 0 이상이어야 합니다: {self.size_bytes}")
        if self.depth < 0:
            raise ValueError(f"depth는 0 이상이어야 합니다: {self.depth}")
        _require_aware(self.modified_at, "modified_at")
        _require_aware(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class ScanError:
    """처리하지 못한 경로 하나. 스캔은 중단하지 않고 이 기록만 남긴다."""

    rel_path: str
    error_type: ErrorType
    message: str
