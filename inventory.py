from pathlib import Path
import sys
from datetime import datetime

def list_files(folder_path):

    count_items = 0
    count_size = 0

    if not folder_path.is_dir():
        print(f"오류: 폴더를 찾을 수 없습니다: {folder_path}")
        return 1

    for windows_path, _, file_names in folder_path.walk():
        for file_name in file_names:
            file_path = windows_path / file_name
            info = file_path.stat()
            print(
                file_path.relative_to(folder_path).as_posix(),
                info.st_size, 
                datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                sep="\t"
            )
            
            count_items += 1
            count_size += info.st_size

    print(f"합계: 파일 {count_items}개, {count_size} 바이트")

    return 0

if __name__ == "__main__":
    if len(sys.argv) == 2:
        sys.exit(list_files(Path(sys.argv[1])))
    else:
        print("사용법: python inventory.py <폴더경로>")
        sys.exit(2)