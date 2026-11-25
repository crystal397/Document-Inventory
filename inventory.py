from pathlib import Path
import sys
from datetime import datetime
import csv

def scan_files(folder_path):

    file_lists = []
    errors = []

    for dir_path, _, file_names in folder_path.walk():
        for file_name in file_names:
            file_path = dir_path / file_name
            info = file_path.stat()
            file_lists.append((
                file_path.relative_to(folder_path).as_posix(),
                info.st_size,
                datetime.fromtimestamp(info.st_mtime)
            ))

    return file_lists, errors

def print_report(records):

    count_items = 0
    count_size = 0

    for relative_path, size, modified_date in records:
        print(
            relative_path,
            size,
            modified_date.strftime("%Y-%m-%d %H:%M:%S"),
            sep="\t"
        )

        count_items += 1
        count_size += size

    print(f"합계: 파일 {count_items}개, {count_size} 바이트")


def save_csv(records, csv_path):
    with open(csv_path, "x", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["상대경로", "크기", "수정일"])
        for relative_path, size, modified_date in records:
            writer.writerow([
                    relative_path,
                    size,
                    modified_date.strftime("%Y-%m-%d %H:%M:%S")
            ])


def is_inside(folder_path, csv_path):
    folder = Path(folder_path).resolve()
    csv_file = Path(csv_path).resolve()

    return csv_file.is_relative_to(folder)


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print("사용법: python inventory.py <폴더경로> [저장할 CSV]")
        sys.exit(2)

    folder_path = Path(sys.argv[1])
    csv_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not folder_path.is_dir():
        print(f"오류: 폴더를 찾을 수 없습니다: {folder_path}")
        sys.exit(1)
    elif csv_path is not None and is_inside(folder_path, csv_path):   
        print(f"오류: 스캔하는 폴더 안에는 저장할 수 없습니다: {csv_path}")
        sys.exit(1)
    else:
        records, _ = scan_files(folder_path)
        print_report(records)

        if csv_path is not None:
            try:
                save_csv(records, csv_path)
                print(f"csv 파일이 생성되었습니다: {csv_path}")
            except FileExistsError:
                print(f"오류: 파일이 이미 있습니다: {csv_path}")
                sys.exit(1)
            except FileNotFoundError:
                print(f"오류: 저장할 폴더가 없습니다: {csv_path}")
                sys.exit(1)