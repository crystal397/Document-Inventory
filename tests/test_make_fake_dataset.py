"""가상 데이터 생성기 테스트.

생성기는 이후 모든 테스트의 '정답지'가 되므로, 생성기 자체가 정확한지 먼저 검증한다.
"""

import os
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

import pytest
from make_fake_dataset import generate_dataset, main, special_cases


def _files_on_disk(root: Path) -> set[str]:
    """디스크에 실제로 있는 파일의 상대경로('/' 구분) 집합."""
    result = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            rel = Path(dirpath, name).relative_to(root)
            result.add(rel.as_posix())
    return result


# ── 기본 동작 ─────────────────────────────────────────────


def test_manifest_matches_disk(fake_dataset):
    """목록(manifest)에 적힌 파일과 디스크의 파일이 정확히 일치해야 한다."""
    manifest = {f.rel_path for f in fake_dataset.files}
    assert manifest == _files_on_disk(fake_dataset.root)


def test_file_counts(fake_dataset):
    assert len(fake_dataset.by_kind("regular")) == 30
    assert len(fake_dataset.files) == 30 + len(special_cases())


def test_sizes_match_disk(fake_dataset):
    for f in fake_dataset.files:
        assert (fake_dataset.root / f.rel_path).stat().st_size == f.size


def test_mtime_is_set_in_the_past(fake_dataset):
    """수정일이 2019~2024년 사이 과거 날짜로 설정되어야 한다."""
    for f in fake_dataset.files:
        disk_mtime = (fake_dataset.root / f.rel_path).stat().st_mtime
        assert disk_mtime == pytest.approx(f.mtime.timestamp(), abs=2)
        assert datetime(2019, 1, 1, tzinfo=UTC) <= f.mtime <= datetime(2024, 12, 31, tzinfo=UTC)


def test_empty_dir_exists(fake_dataset):
    for rel_dir in fake_dataset.empty_dirs:
        path = fake_dataset.root / rel_dir
        assert path.is_dir()
        assert list(path.iterdir()) == []


# ── 재현성 ───────────────────────────────────────────────


def test_same_seed_gives_same_result(tmp_path):
    a = generate_dataset(tmp_path / "a", n_files=50, seed=7)
    b = generate_dataset(tmp_path / "b", n_files=50, seed=7)
    assert a.files == b.files


def test_different_seed_gives_different_result(tmp_path):
    a = generate_dataset(tmp_path / "a", n_files=50, seed=7)
    b = generate_dataset(tmp_path / "b", n_files=50, seed=8)
    assert a.files != b.files


# ── 안전장치 ─────────────────────────────────────────────


def test_refuses_non_empty_folder(tmp_path):
    """이미 파일이 있는 폴더에는 생성하지 않고, 기존 파일도 건드리지 않아야 한다."""
    existing = tmp_path / "기존자료.pdf"
    existing.write_bytes(b"original")

    with pytest.raises(FileExistsError):
        generate_dataset(tmp_path)

    assert existing.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [existing]


def test_refuses_path_that_is_a_file(tmp_path):
    target = tmp_path / "file.txt"
    target.write_bytes(b"x")
    with pytest.raises(FileExistsError):
        generate_dataset(target)


def test_creates_missing_folder(tmp_path):
    target = tmp_path / "새폴더" / "하위"
    generate_dataset(target, n_files=1)
    assert target.is_dir()


@pytest.mark.parametrize("kwargs", [{"n_files": -1}, {"n_cases": 0}])
def test_rejects_invalid_arguments(tmp_path, kwargs):
    with pytest.raises(ValueError):
        generate_dataset(tmp_path / "x", **kwargs)


# ── 특수 사례가 디스크에 '그대로' 만들어졌는지 ───────────────


def test_nfd_names_are_preserved_on_disk(fake_dataset):
    """NFD(자모 분리) 이름이 디스크에서도 NFD로 유지되어야 한다.

    이 테스트가 실패하면 해당 OS/파일시스템이 이름을 자동 정규화한다는 뜻이다.
    (macOS 검증은 CI가 담당)
    """
    nfd_files = fake_dataset.by_kind("nfd")
    assert nfd_files
    special_dir = fake_dataset.root / "사건_가상001" / "99_특수사례"
    names_on_disk = {p.name for p in special_dir.iterdir()}
    for f in nfd_files:
        name = f.rel_path.rsplit("/", 1)[1]
        assert name != unicodedata.normalize("NFC", name)  # 정말 NFD 형태인지
        assert name in names_on_disk


def test_mojibake_names_contain_no_hangul(fake_dataset):
    """깨진 이름에는 한글 음절이 없어야 한다 (한글이 다른 문자로 깨졌으므로)."""
    for f in fake_dataset.by_kind("mojibake"):
        assert not any("가" <= ch <= "힣" for ch in f.rel_path.rsplit("/", 1)[1])


def test_long_name_fits_macos_limit(fake_dataset):
    """macOS 파일명 한도(255바이트) 이내여야 macOS CI에서도 생성된다."""
    (long_file,) = fake_dataset.by_kind("long_name")
    name = long_file.rel_path.rsplit("/", 1)[1]
    assert 230 <= len(name.encode("utf-8")) <= 255


def test_deep_file_depth(fake_dataset):
    (deep_file,) = fake_dataset.by_kind("deep")
    assert deep_file.rel_path.count("/") >= 12  # 사건/99_특수사례/ + 하위폴더 10단계 + 파일


def test_empty_file_has_zero_size(fake_dataset):
    for f in fake_dataset.by_kind("empty_file"):
        assert (fake_dataset.root / f.rel_path).stat().st_size == 0


# ── 명령행 ───────────────────────────────────────────────


def test_main_success(tmp_path, capsys):
    out = tmp_path / "cli"
    assert main(["--out", str(out), "--files", "5"]) == 0
    assert "생성 완료" in capsys.readouterr().out
    assert out.is_dir()


def test_main_refuses_non_empty(tmp_path, capsys):
    (tmp_path / "x.txt").write_bytes(b"x")
    assert main(["--out", str(tmp_path)]) == 1
    assert "비어 있지 않습니다" in capsys.readouterr().err
