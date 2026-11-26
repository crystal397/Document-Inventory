from inventory import scan_files, save_csv, is_inside, print_report
import os
from datetime import datetime
import pytest
from pathlib import Path

def test_empty_folder_returns_empty_list(tmp_path):
    records, _ = scan_files(tmp_path)
    assert records == []


def test_two_files_have_correct_sizes(tmp_path):
    new_file1 = tmp_path / "apple.txt"
    new_file1.write_text("example")

    new_file2 = tmp_path / "pale.txt"
    new_file2.write_text("full")

    records, _ = scan_files(tmp_path)

    relative_path_size = {}
    for relative_path, size, _ in records:
        relative_path_size[relative_path] = size

    assert len(relative_path_size) == 2
    assert relative_path_size["apple.txt"] == 7
    assert relative_path_size["pale.txt"] == 4


def test_file_in_subfolder_uses_slash(tmp_path):
    new_folder1 = tmp_path / "apple"
    new_folder1.mkdir()

    new_file1 = new_folder1 / "apple.txt"
    new_file1.write_text("example")

    new_folder2 = tmp_path / "pale"
    new_folder2.mkdir()

    new_file2 = new_folder2 / "pale.txt"
    new_file2.write_text("full")

    new_folder3 = new_folder2 / "grapefruit"
    new_folder3.mkdir()

    new_file3 = new_folder3 / "grapefruit.txt"
    new_file3.write_text("good")

    records, _ = scan_files(tmp_path)

    actual_relative_paths = set()
    for relative_path, _, _ in records:
        actual_relative_paths.add(relative_path)

    assert actual_relative_paths == {"apple/apple.txt", "pale/pale.txt", "pale/grapefruit/grapefruit.txt"}


def test_empty_subfolder_is_not_recorded(tmp_path):
    new_folder = tmp_path / "grapefruit"
    new_folder.mkdir()

    records, _ = scan_files(tmp_path)

    assert records == []


def test_modified_date_is_recorded(tmp_path):
    new_file = tmp_path / "grapefruit.txt"
    new_file.write_text("grapefruit")
    access_time = os.stat(new_file).st_atime

    expected_date = datetime(2026, 1, 2, 3, 4, 5)
    os.utime(new_file, (access_time, expected_date.timestamp()))

    records, _ = scan_files(tmp_path)

    assert records[0][2] == expected_date


def test_save_csv_writes_header_and_rows(tmp_path):
    records = [("도면/계약서.pdf", 7, datetime(2026, 1, 2, 3, 4, 5))]
    csv_path = tmp_path / "result.csv"

    save_csv(records, csv_path)

    text = csv_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    assert lines == ["상대경로,크기,수정일", "도면/계약서.pdf,7,2026-01-02 03:04:05"]


def test_save_csv_starts_with_bom(tmp_path):
    csv_path = tmp_path / "result.csv"
    save_csv([], csv_path)

    data = csv_path.read_bytes()                # 글자로 바꾸지 않고 바이트 그대로 읽기

    assert data.startswith(b"\xef\xbb\xbf")       # 이것으로 시작하면 True


def test_save_csv_does_not_overwrite_existing_file(tmp_path):
    csv_path = tmp_path / "result.csv"
    csv_path.write_text("original")

    with pytest.raises(FileExistsError):
        save_csv([], csv_path)

    assert csv_path.read_text() == "original"


def test_csv_in_scanned_folder_is_inside(tmp_path):
    folder_path = tmp_path / "sample"
    csv_path = folder_path / "result.csv"
    
    assert is_inside(folder_path, csv_path) == True
    

def test_csv_going_up_is_not_inside(tmp_path):
    folder_path = tmp_path / "sample"
    csv_path = folder_path / ".." / "result.csv"

    assert is_inside(folder_path, csv_path) == False


def test_unreadable_files_are_skipped(tmp_path, monkeypatch):
    new_file1 = tmp_path / "apple.txt"
    new_file2 = tmp_path / "banana.txt"

    new_file1.touch()
    new_file2.touch()

    def fake_stat(self):
        raise PermissionError("권한 없음")

    monkeypatch.setattr(Path, "stat", fake_stat)

    file_lists, errors = scan_files(tmp_path)

    assert len(file_lists) == 0
    assert len(errors) == 2


def test_print_report_shows_errors(capsys):
    records = [("도면/계약서.pdf", 7, datetime(2026, 1, 2, 3, 4, 5))]
    errors = [("도면/설계서.pdf", "권한 없음")]

    print_report(records, errors)

    out = capsys.readouterr().out
    assert out.splitlines() == ["도면/계약서.pdf\t7\t2026-01-02 03:04:05", "합계: 파일 1개, 7 바이트", "읽지 못한 파일: 1개", "도면/설계서.pdf\t권한 없음"]


def test_print_report_hides_errors_when_none(capsys):
    records = [("도면/계약서.pdf", 7, datetime(2026, 1, 2, 3, 4, 5))]
    errors = []

    print_report(records, errors)

    out = capsys.readouterr().out
    assert out.splitlines() == ["도면/계약서.pdf\t7\t2026-01-02 03:04:05", "합계: 파일 1개, 7 바이트"]