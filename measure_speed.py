from inventory import scan_files, print_report, save_csv
import sys
from pathlib import Path
import time

def count_time(func, *args):
    start = time.perf_counter()      # 지금 시각(초)
    result = func(*args)
    seconds = time.perf_counter() - start
    return result, seconds

folder_path = Path(sys.argv[1])

records_and_errors, scan_seconds = count_time(scan_files, folder_path)
records, errors = records_and_errors
_, print_seconds = count_time(print_report, records, errors)
_, save_seconds = count_time(save_csv, records, errors, "speed_test.csv")

print(f"scan files 걸린 시간: {scan_seconds:.2f}초")   # .2f는 소수점 둘째 자리까지
print(f"print report 걸린 시간: {print_seconds:.2f}초")
print(f"save csv 걸린 시간: {save_seconds:.2f}초")