from pathlib import Path
import sys

def list_files(folder_path):
    if not folder_path.is_dir():
        print(f"오류: 폴더를 찾을 수 없습니다: {folder_path}")
        return 1

    for item in folder_path.iterdir():
        if item.is_file():
            print(item.name)

    return 0

if __name__ == "__main__":
    if len(sys.argv) == 2:
        sys.exit(list_files(Path(sys.argv[1])))
    else:
        print("사용법: python inventory.py <폴더경로>")