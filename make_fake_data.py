from pathlib import Path
import sys
import random

KINDS = [
    ("01_계약서", "계약서", ".pdf"),
    ("02_도면/상세도", "도면", ".dwg"),
    ("03_현장사진", "현장사진", ".jpg"),
    ("04_작업일지", "작업일지", ".xlsx"),
    ("05_공문", "공문", ".hwpx")
]

def make_files(folder_path, count):
    fake_folder = folder_path
    fake_folder.mkdir()

    rng = random.Random(42)

    for i in range(1, count+1):
        folder_name, file_name, file_extension = rng.choice(KINDS)
        new_folder = fake_folder / folder_name
        new_folder.mkdir(parents=True, exist_ok=True)
        new_file = new_folder / f"{file_name}_{i:05d}{file_extension}"
        new_file.write_bytes(b"0" * rng.randint(0,2000))


if __name__ == "__main__":
    if len(sys.argv) == 3:

        folder_path = Path(sys.argv[1])

        if folder_path.is_dir():
            print(f"오류: 폴더가 이미 존재합니다: {folder_path}")
            sys.exit(1)
        else:
            try:
                count = int(sys.argv[2])
            except ValueError:
                print(f"사용법 오류: 만들 파일갯수에 숫자를 입력하지 않았습니다: {sys.argv[2]}")
                sys.exit(2)
            try:
                make_files(folder_path, count)
                print(f"{count}개 파일이 생성되었습니다")
            except FileExistsError:
                print(f"오류: 파일이 이미 있습니다: {folder_path}")
                sys.exit(1)

            sys.exit(0)
    else:
        print("사용법: python make_fake_data.py <폴더명> <만들 파일갯수>")
        sys.exit(2)