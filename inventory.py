from pathlib import Path
import sys

def main():
    for file in Path(sys.argv[1]).iterdir():
        if Path.is_file(file):
            print(file)
    return 0

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("사용법: python inventory.py <폴더경로>")
    elif len(sys.argv) == 2 and Path(sys.argv[1]).exists():
        main()
    elif len(sys.argv) == 2 :
        print("오류: 폴더를 찾을 수 없습니다: 없는폴더")
    else:
        sys.exit()