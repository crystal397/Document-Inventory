"""models.py 테스트: 데이터 구조의 검증 규칙과 불변성."""

import dataclasses
from datetime import UTC, datetime

import pytest

from doc_inventory.models import ErrorType, FileRecord, ScanError

NOW = datetime(2024, 3, 15, 9, 0, tzinfo=UTC)


def make_record(**overrides) -> FileRecord:
    """테스트용 FileRecord. 필요한 필드만 바꿔서 쓴다."""
    values = {
        "rel_path": "사건A/01_계약서/계약서.pdf",
        "name": "계약서.pdf",
        "extension": ".pdf",
        "size_bytes": 1024,
        "modified_at": NOW,
        "created_at": NOW,
        "depth": 2,
        "parent_dir": "사건A/01_계약서",
        "is_hidden": False,
        "name_was_nfd": False,
        "name_suspect_mojibake": False,
    }
    values.update(overrides)
    return FileRecord(**values)


def test_valid_record():
    record = make_record()
    assert record.category is None  # 분류 전 기본값


def test_record_is_immutable():
    record = make_record()
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.size_bytes = 0


def test_replace_creates_new_record():
    """불변 객체의 값을 '바꾸는' 방법: 새 객체를 만든다."""
    record = make_record()
    classified = dataclasses.replace(record, category="문서")
    assert classified.category == "문서"
    assert record.category is None  # 원래 객체는 그대로


def test_created_at_may_be_none():
    assert make_record(created_at=None).created_at is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"size_bytes": -1},
        {"depth": -1},
        {"modified_at": datetime(2024, 3, 15, 9, 0)},  # 시간대 없음(naive)
        {"created_at": datetime(2024, 3, 15, 9, 0)},
    ],
)
def test_invalid_record_rejected(overrides):
    with pytest.raises(ValueError):
        make_record(**overrides)


def test_error_type_behaves_like_string():
    error = ScanError("a/b.pdf", ErrorType.PERMISSION, "Access is denied")
    assert error.error_type == "permission"
    assert ErrorType("not_found") is ErrorType.NOT_FOUND
