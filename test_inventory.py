from inventory import scan_files

def test_empty_folder_returns_empty_list(tmp_path):
    records = scan_files(tmp_path)
    assert records == []


def test_two_files_have_correct_sizes(tmp_path):
    new_file1 = tmp_path / "apple.txt"
    new_file1.write_text("example")

    new_file2 = tmp_path / "pale.txt"
    new_file2.write_text("full")

    records = scan_files(tmp_path)

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

    records = scan_files(tmp_path)

    actual_relative_paths = set()
    for relative_path, _, _ in records:
        actual_relative_paths.add(relative_path)

    assert actual_relative_paths == {"apple/apple.txt", "pale/pale.txt", "pale/grapefruit/grapefruit.txt"}


def test_empty_subfolder_is_not_recorded(tmp_path):
    new_folder = tmp_path / "grapefruit"
    new_folder.mkdir()

    records = scan_files(tmp_path)

    assert records == []