from pathlib import Path
import sys
from datetime import datetime

def scan_files(folder_path):

    file_lists = []

    for dir_path, _, file_names in folder_path.walk():
        for file_name in file_names:
            file_path = dir_path / file_name
            info = file_path.stat()
            file_lists.append(
                (file_path.relative_to(folder_path).as_posix(),
                info.st_size, 
                datetime.fromtimestamp(info.st_mtime)
                )
            )

    return file_lists

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

    return 0

if __name__ == "__main__":
    if len(sys.argv) == 2:
        
        folder_path = Path(sys.argv[1])

        if not folder_path.is_dir():
            print(f"오류: 폴더를 찾을 수 없습니다: {folder_path}")
            sys.exit(1)
        else:
            records = scan_files(Path(sys.argv[1]))
            sys.exit(print_report(records))
    else:
        print("사용법: python inventory.py <폴더경로>")
        sys.exit(2)