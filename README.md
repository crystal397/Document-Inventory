# Document Inventory

대규모 건설감정 자료를 관리하기 위한 **문서 인벤토리 프로그램**입니다.
수천~수만 개의 파일이 있는 폴더를 스캔하여 파일 메타데이터(이름, 확장자, 크기, 날짜, 폴더 구조)를
로컬 데이터베이스에 기록하고, 통계와 목록을 CSV/Excel로 출력합니다.

> **현재 상태:** 1단계 구현 중 — 폴더 스캔 · 화면 출력 · CSV 저장 · 오류 처리까지 동작합니다.
> 아래 [지금 사용하는 법](#지금-사용하는-법)은 **현재 코드** 기준이고,
> [1장](#1-개발-원칙)부터는 설계 검토에서 정한 **목표 구조**입니다. 지금은 `inventory.py` 한 파일에서 시작해 단계별로 나누어 가고 있습니다.

---

## 지금 사용하는 법

**필요:** Python 3.12 이상 (폴더 순회에 `Path.walk()`를 사용합니다)

```powershell
python inventory.py <폴더경로>              # 목록과 합계를 화면에 출력
python inventory.py <폴더경로> <저장할 CSV>  # 화면 출력 + CSV 저장
```

### 출력

화면에는 파일마다 `상대경로 · 크기(바이트) · 수정일`이 탭으로 나뉘어 나오고, 끝에 합계가 나옵니다.
읽지 못한 파일이 있으면 합계 아래에 그 목록이 따로 나옵니다.

```
도면/평면도.pdf	1200	2026-01-02 03:04:05
합계: 파일 48개, 51234 바이트
읽지 못한 파일: 1개
도면/단면도.pdf	[Errno 13] Permission denied: ...
```

CSV는 `상대경로, 크기, 수정일` 열로 저장되고, 인코딩은 **UTF-8 (BOM 포함)** 이라 엑셀에서 한글이 깨지지 않습니다.

### 원본을 지키는 동작

| 상황 | 동작 |
|---|---|
| CSV를 **스캔하는 폴더 안**에 저장하려 함 | 거부 (원본 폴더에 파일이 섞이지 않도록) |
| 같은 이름의 CSV가 **이미 있음** | 거부 (덮어쓰지 않음) |
| CSV를 저장할 **폴더가 없음** | 거부 (오타로 엉뚱한 곳에 저장되지 않도록) |
| 읽을 수 없는 파일이 있음 | 건너뛰고 나머지를 계속 스캔, 끝에 목록으로 안내 |

### 종료 코드

다른 프로그램이나 작업 스케줄러가 결과를 판단할 때 씁니다. 사람은 화면의 안내 문구를 보면 됩니다.

| 코드 | 이름 (`inventory.py`) | 뜻 |
|---|---|---|
| 0 | `EXIT_OK` | 모두 성공 |
| 1 | `EXIT_FAILED` | 실패 — 폴더가 없거나 CSV를 저장하지 못함 |
| 2 | `EXIT_USAGE` | 사용법 오류 — 인자 개수가 틀림 |
| 3 | `EXIT_PARTIAL` | 부분 성공 — CSV는 저장했지만 읽지 못한 파일이 있음 |

PowerShell에서는 실행 직후 `echo $LASTEXITCODE`로 확인할 수 있습니다.

### 테스트와 보조 도구

```powershell
pytest                                          # 단위 테스트
python make_fake_data.py fake_data_10k 10000    # 가짜 시험 데이터 생성 (실제 자료 대신)
python measure_speed.py fake_data_10k           # 함수별 처리 시간 측정
```

`measure_speed.py`는 `speed_test.csv`를 만들기 때문에, 다시 실행하기 전에 지워야 합니다(덮어쓰기 방지가 작동합니다).

참고로 이 PC에서 파일 5만 개를 처리하는 데 약 4초가 걸렸습니다(스캔 약 60%, 화면 출력 약 38%).

---

## 목차

1. [개발 원칙](#1-개발-원칙)
2. [결정 사항](#2-결정-사항)
3. [아키텍처](#3-아키텍처)
4. [디렉터리 구성](#4-디렉터리-구성)
5. [모듈별 역할](#5-모듈별-역할)
6. [기술 스택과 선택 이유](#6-기술-스택과-선택-이유)
7. [4주 구현 계획](#7-4주-구현-계획)
8. [예상되는 기술적 문제](#8-예상되는-기술적-문제)
9. [한글 파일명 처리](#9-한글-파일명-처리)
10. [테스트 전략](#10-테스트-전략)
11. [CI (자동 테스트)](#11-ci-자동-테스트)
12. [2단계 로드맵](#12-2단계-로드맵)

---

## 1. 개발 원칙

1. Python을 사용한다.
2. Windows와 macOS에서 모두 실행 가능해야 한다.
3. **파일 원본은 수정하거나 삭제하지 않는다.**
4. **외부 서버에 파일을 전송하지 않는다.**
5. 처음에는 파일 내용이 아닌 **메타데이터만** 조사한다.
6. 수천~수만 개 파일 처리에 적합하게 설계한다.
7. 기능을 작은 모듈로 나누고 pytest로 검증한다.
8. 초보 개발자가 코드를 이해할 수 있도록 기술적 선택의 이유와 동작 원리를 설명한다.
9. **회사 자료, 실제 사건 자료는 사용하지 않고 가상 데이터만 사용한다.**

> ⚠️ 이 저장소는 **공개(public)** 저장소입니다.
> 실제 자료를 스캔한 결과물(DB, CSV, 로그)은 파일명 목록 자체가 민감 정보이므로
> 절대 커밋하지 않습니다. `output/` 폴더와 결과 파일은 `.gitignore`로 제외합니다.

---

## 2. 결정 사항

| 항목 | 결정 | 비고 |
|---|---|---|
| 프로젝트 위치 | `Document-Inventory/` (GitHub 저장소와 연결된 폴더) | `origin` = `github.com/crystal397/Document-Inventory` |
| Python 버전 | 3.12 이상 | 3.12부터 Windows에서도 `st_birthtime`(생성일) 지원 |
| 인터페이스 | 1단계는 CLI(명령행) | GUI는 2단계로 연기 |
| 출력 형식 | **CSV 기본** + xlsx는 선택 기능 | xlsx는 3주차 후반, 일정 부족 시 제외 가능 |
| macOS 검증 | 단위 테스트 + CI로만 검증 | 실제 macOS 장비 테스트는 하지 않음 |
| CI | GitHub Actions 적용 (Windows + macOS) | 공개 저장소이므로 무료 |
| 저장소 공개 여부 | 공개 유지 | 가상 데이터만 커밋 |

---

## 3. 아키텍처

**단방향 파이프라인 + 계층 분리** 구조입니다.

```
 [CLI] ─── 사용자 명령 (scan / stats / export / diff)
   │
   ▼
 ┌──────────┐   경로 스트림   ┌───────────┐  FileRecord  ┌────────────┐
 │ Scanner  │ ─────────────▶ │ Metadata  │ ───────────▶ │ Classifier │
 │ (폴더순회) │   (generator)  │ (stat 수집) │              │ (분류 규칙)   │
 └──────────┘                └───────────┘              └─────┬──────┘
      │ 오류(권한·경로)                                         │ 배치(1,000건)
      ▼                                                       ▼
 ┌──────────┐                                          ┌────────────┐
 │ ErrorLog │ ───────────────────────────────────────▶ │  Storage   │ SQLite 파일 1개
 └──────────┘                                          └─────┬──────┘
                                                             ▼
                                              ┌──────────────────────────┐
                                              │ Report / Exporter        │
                                              │ (통계 요약, CSV, xlsx)     │
                                              └──────────────────────────┘
```

### 원칙과 설계의 대응

| 원칙 | 설계상 대응 |
|---|---|
| 원본 불변 | 원본 파일을 **열지 않는다**. `os.stat()`은 파일시스템 정보만 읽으며 파일을 open하지 않는다. `safety` 모듈이 출력 경로가 스캔 대상 폴더 안에 생기는 것을 차단한다. |
| 외부 전송 금지 | 네트워크 라이브러리를 사용하지 않는다. 결과는 로컬 SQLite/CSV에만 저장한다. |
| 메타데이터만 | 1단계에서는 해시 계산이나 텍스트 추출을 하지 않는다. 내용 분석은 2단계에서 별도 모듈로 확장한다. |
| 대용량 처리 | **generator 스트리밍**으로 전체 목록을 메모리에 올리지 않고, **배치 트랜잭션**으로 DB에 저장한다. |
| 작은 모듈 | 각 단계는 입력→출력이 명확한 함수 위주로 작성하여 독립적으로 테스트한다. |

### 동작 원리: generator

`os.walk()` 결과를 리스트에 모두 담으면 5만 개 경로가 한 번에 메모리에 올라가고,
순회가 끝날 때까지 첫 결과를 볼 수 없습니다.
`yield`를 사용하는 generator는 **파일 하나를 찾을 때마다 바로 다음 단계로 넘기므로**
파일 수와 무관하게 메모리 사용량이 거의 일정합니다.

### 동작 원리: 배치 트랜잭션

SQLite는 `INSERT` 한 건마다 커밋하면 매번 디스크에 기록을 확정하느라 매우 느립니다.
1,000건씩 모아 하나의 트랜잭션으로 저장하면 디스크 확정 횟수가 1/1000로 줄어듭니다.

---

## 4. 디렉터리 구성

```
Document-Inventory/
├── pyproject.toml           # 프로젝트 정의, 의존성, pytest/ruff 설정
├── README.md
├── .gitignore               # output/, .venv/, *.sqlite, *.csv 등 제외
├── .gitattributes           # 줄바꿈(CRLF/LF) 규칙 통일
├── .github/
│   └── workflows/
│       └── test.yml         # CI: Windows + macOS 자동 테스트
├── config/
│   └── default.toml         # 확장자→분류 규칙, 제외 패턴
├── src/
│   └── doc_inventory/
│       ├── __init__.py
│       ├── __main__.py      # `python -m doc_inventory` 진입점
│       ├── cli.py           # 명령행 인터페이스
│       ├── config.py        # 설정 파일 로딩
│       ├── models.py        # FileRecord 등 데이터 구조
│       ├── safety.py        # 읽기 전용 보장, 출력 경로 검증
│       ├── pathutils.py     # 경로 정규화 (NFC, 긴 경로, 상대경로)
│       ├── scanner.py       # 폴더 순회
│       ├── metadata.py      # stat → FileRecord 변환
│       ├── classifier.py    # 확장자/규칙 기반 분류
│       ├── storage.py       # SQLite 스키마, 저장, 조회
│       ├── report.py        # 통계 집계
│       └── exporter.py      # CSV / xlsx 내보내기
├── tests/
│   ├── conftest.py          # 가상 폴더 트리 fixture
│   ├── test_<모듈명>.py      # 모듈당 1개
│   ├── test_korean_filenames.py
│   └── test_readonly.py     # 원본 불변 검증 (최우선)
├── tools/
│   └── make_fake_dataset.py # 가상 건설감정 자료 트리 생성기
├── docs/
│   └── decisions.md         # 기술 결정 기록
└── output/                  # 실행 결과 (git 제외)
```

### 왜 `src/` 레이아웃인가

패키지를 프로젝트 루트에 바로 두면 설치하지 않아도 현재 폴더 덕분에 import가 우연히 성공하여,
"내 PC에서는 되는데 다른 환경에서는 안 되는" 문제가 숨어버립니다.
`src/` 아래에 두면 테스트가 반드시 **설치된 패키지**를 대상으로 실행되어 이런 문제를 조기에 발견합니다.

---

## 5. 모듈별 역할

| 모듈 | 책임 | 입력 → 출력 |
|---|---|---|
| `models.py` | 데이터 구조 정의 | — → `FileRecord`, `ScanError`, `ScanSummary` |
| `config.py` | TOML 설정 로딩, 기본값 병합 | 파일 경로 → `Config` |
| `safety.py` | 출력 경로가 스캔 대상 내부면 거부, 대상 존재 확인 | (root, output) → 통과 / 예외 |
| `pathutils.py` | 유니코드 NFC 정규화, 상대경로, Windows 긴 경로 | `Path` → 정규화 문자열 |
| `scanner.py` | `os.scandir` 재귀 순회, 제외 패턴, 심볼릭 링크 미추적 | root → `Iterator[DirEntry \| ScanError]` |
| `metadata.py` | stat 추출, 플랫폼 차이(생성일 등) 흡수 | `DirEntry` → `FileRecord` |
| `classifier.py` | 확장자 기반 분류 | `FileRecord` → category 부여 |
| `storage.py` | SQLite 스키마, 배치 insert, 스캔 이력 | `Iterable[FileRecord]` → DB |
| `report.py` | SQL 집계로 통계 생성 | DB → 요약 표 |
| `exporter.py` | CSV(UTF-8 BOM), xlsx 출력 | DB 조회 결과 → 파일 |
| `cli.py` | 명령 분기, 진행률, 로깅 | argv → 종료 코드 |

### 수집 메타데이터 (1단계)

| 필드 | 설명 |
|---|---|
| `rel_path` | 스캔 루트 기준 상대경로 (NFC 정규화) |
| `name`, `extension` | 파일명, 확장자(소문자) |
| `size_bytes` | 파일 크기 |
| `created_at`, `modified_at` | 생성일, 수정일 (UTC 저장) |
| `depth`, `parent_dir` | 폴더 깊이, 상위 폴더 |
| `is_hidden` | 숨김 파일 여부 |
| `category` | 분류 (문서/도면/사진/표/압축/기타) |
| `name_was_nfd`, `name_suspect_mojibake` | 한글 파일명 진단 플래그 ([9장](#9-한글-파일명-처리) 참고) |

### 분류 규칙 예시 (`config/default.toml`)

| 분류 | 확장자 |
|---|---|
| 문서 | `.pdf`, `.hwp`, `.hwpx`, `.doc`, `.docx`, `.txt` |
| 도면 | `.dwg`, `.dxf`, `.dwf` |
| 사진 | `.jpg`, `.jpeg`, `.png`, `.heic`, `.tif` |
| 표 | `.xls`, `.xlsx`, `.csv` |
| 압축 | `.zip`, `.7z`, `.rar`, `.alz`, `.egg` |

### SQLite 스키마 초안

```
scans  (scan_id, root_path, started_at, finished_at, file_count, error_count, tool_version)
files  (id, scan_id, rel_path, name, extension, category, size_bytes,
        created_at, modified_at, depth, parent_dir, is_hidden,
        name_was_nfd, name_suspect_mojibake)
errors (id, scan_id, path, error_type, message)

인덱스: files(scan_id, extension), files(scan_id, parent_dir)
```

---

## 6. 기술 스택과 선택 이유

### 표준 라이브러리 (핵심 기능은 모두 표준 라이브러리로 구현)

| 기술 | 용도 | 선택 이유 |
|---|---|---|
| `os.scandir` | 폴더 순회 | `listdir` + `stat`보다 빠름. Windows에서는 디렉터리 읽기 시 stat 정보가 함께 와서 시스템 호출이 크게 줄어듦 |
| `pathlib` | 경로 조작 | OS별 경로 구분자(`\` vs `/`) 차이를 자동 처리 |
| `dataclasses` | 데이터 모델 | dict보다 오타에 안전하고 IDE 자동완성 지원. `frozen=True`로 불변 객체 |
| `sqlite3` | 저장소 | 서버 없는 단일 파일 DB, 수백만 행 처리, SQL 집계 가능, 외부 전송 없음 |
| `unicodedata` | 한글 정규화 | macOS 자모 분리(NFD) 문제 해결 |
| `tomllib` | 설정 파일 | 3.11+ 표준, JSON과 달리 주석 작성 가능 |
| `argparse` | CLI | 표준 라이브러리, 의존성 없음, 동작 원리 학습에 적합 |
| `logging` | 로그 | 레벨(DEBUG/INFO/ERROR) 구분, 파일 기록 |
| `csv`, `datetime`, `fnmatch` | 내보내기, 시간, 제외 패턴 | — |

### 외부 라이브러리 (최소화)

| 라이브러리 | 용도 | 구분 |
|---|---|---|
| `pytest`, `pytest-cov` | 테스트, 커버리지 | 개발용 |
| `ruff` | 린트 + 포맷 (flake8/black/isort 대체) | 개발용 |
| `tqdm` | 진행률 표시 | 실행용 |
| `openpyxl` | xlsx 출력 | 실행용 (선택 기능) |

### 의도적으로 사용하지 않는 것

- **pandas:** 1단계는 SQL 집계로 충분. 무거운 의존성을 피하고 분석 단계에서 도입 검토
- **멀티스레딩:** 먼저 단일 스레드로 측정하고, 병목이 확인될 때만 도입 (특히 NAS 환경)

### 출력 형식: 왜 CSV 기본 + xlsx 선택인가

CSV는 행 제한이 없고 빠르며 어떤 도구로도 읽을 수 있어 **전체 원본 목록**에 적합합니다.
그러나 Excel로 CSV를 열면 데이터가 임의로 바뀌는 문제가 있습니다.

| CSV를 Excel로 열 때 문제 | 예시 | xlsx라면 |
|---|---|---|
| 한글 깨짐 | BOM 없으면 cp949로 해석 | 문제 없음 |
| 텍스트가 숫자/날짜로 변형 | 폴더명 `01` → `1`, `3-1` → `3월 1일` | 텍스트 서식 유지 |
| 날짜가 텍스트로 인식 | 정렬/필터 오동작 | 날짜 서식 |
| 파일당 표 1개 | 요약/목록/오류가 3개 파일 | 시트 3개를 1개 파일에 |
| 서식 없음 | 열 너비·필터·머리글 고정 매번 수동 | 미리 설정해 출력 |

따라서 **CSV는 기본 출력(전체 목록)**, **xlsx는 실무 보고용 요약 보고서(선택 기능)** 로 역할을 나눕니다.
xlsx는 104만 행 제한이 있고 대용량에서 느리므로 요약 용도로 한정합니다.

---

## 7. 4주 구현 계획

각 주의 끝에는 **동작하는 결과물 + 통과하는 테스트**가 남도록 구성합니다.

### 1주차 — 기반과 폴더 순회

- 개발 환경: `venv`, `pyproject.toml`, `.gitignore`, `.gitattributes`, pytest·ruff 설정
- CI 설정: `.github/workflows/test.yml` (Windows + macOS)
- `tools/make_fake_dataset.py`: 가상 감정 자료 트리 생성
  (예: `사건_가상001/01_계약서/`, `02_도면/*.dwg`, `03_현장사진/*.jpg`, 깊은 폴더, 긴 한글 파일명, 빈 폴더, 한글 특수 사례)
- `models.py`, `pathutils.py`, `scanner.py` + 테스트
- **결과물:** 가상 폴더를 순회해 파일 경로를 출력
- **학습:** generator, 재귀 vs 반복, 예외 처리, CI

### 2주차 — 메타데이터와 저장

- `metadata.py`: stat → FileRecord, 생성일 플랫폼 차이 처리, UTC 저장
- `classifier.py` + `config/default.toml`
- `storage.py`: 스키마, 1,000건 배치 insert, 오류 테이블
- `safety.py`: 출력 경로 검증
- **결과물:** `scan` 명령으로 SQLite DB 생성
- **학습:** dataclass, SQL 기초, 트랜잭션, 타임존

### 3주차 — CLI와 보고서

- `cli.py`: `scan`, `stats`, `export` 하위 명령
- `report.py`: 확장자별 개수/용량, 폴더별 집계, 큰 파일 Top N, 오류 목록, 한글 파일명 진단
- `exporter.py`: CSV (Excel 한글 호환) → 후반에 xlsx 요약 보고서 (선택)
- 진행률 표시, 로그 파일
- **결과물:** 실사용 가능한 1.0 버전
- **학습:** CLI 설계, SQL GROUP BY, 인코딩

### 4주차 — 대규모 처리, 재스캔, 마무리

- 성능 테스트: 가상 파일 5만 개로 측정(`time`, `cProfile`) 및 병목 개선
- `diff` 명령: 두 스캔 비교 (추가/삭제/변경 파일, 기준: 경로 + 크기 + 수정일)
- CI에서 macOS 테스트 결과 확인 및 수정
- README, 사용 설명서, `docs/decisions.md` 정리
- **2단계 로드맵** 확정

---

## 8. 예상되는 기술적 문제

| # | 문제 | 원인 | 대응 |
|---|---|---|---|
| 1 | Windows 260자 경로 제한 | 감정 자료는 폴더가 깊고 이름이 김 | `\\?\` 접두사 처리, 실패 시 오류 테이블 기록, LongPathsEnabled 설정 안내 |
| 2 | 생성일의 OS별 의미 차이 | Linux `st_ctime`은 메타데이터 변경 시각. 복사 시 생성일이 복사 시점으로 바뀜 | `st_birthtime` 우선, 없으면 NULL. 보고서에 해석 주의 문구 표기 (감정 자료에서 특히 중요) |
| 3 | 권한 오류, 잠긴 파일 | 시스템 폴더, 타 사용자 파일 | 예외를 잡아 오류 테이블에 기록하고 스캔 계속 |
| 4 | 심볼릭 링크·정션 무한 루프 | 링크가 상위 폴더를 가리킴 | `follow_symlinks=False`, 링크라는 사실만 기록 |
| 5 | NAS·네트워크 드라이브 속도 | stat 호출마다 네트워크 왕복 | 진행률 표시, 측정 후 `ThreadPoolExecutor` 검토 |
| 6 | OneDrive 등 클라우드 동기화 폴더 | 파일 내용을 읽으면 다운로드 발생 | 1단계는 메타데이터만 읽으므로 안전. 2단계에서 주의 |
| 7 | Excel 행 제한 | 1,048,576행 | 전체 목록은 CSV, xlsx는 요약 용도 |
| 8 | 잡음 파일 | `Thumbs.db`, `.DS_Store`, `~$보고서.xlsx` | 설정 파일의 제외 패턴, 제외 개수도 통계에 표시 |
| 9 | 대소문자 | Windows/macOS는 기본적으로 대소문자 비구분 | 확장자 소문자 정규화, 비교 규칙 문서화 |

---

## 9. 한글 파일명 처리

Python 3는 한글 파일명을 기본적으로 잘 처리합니다(Windows에서도 유니코드 API 사용).
문제는 대부분 **경계 지점** — 입출력, OS 간 이동, 다른 프로그램과의 교환 — 에서 발생합니다.

| # | 문제 | 발생 상황 | 대응 |
|---|---|---|---|
| 1 | **자모 분리 (NFD)** | macOS에서 만든 파일을 USB/NAS로 옮기면 **Windows에서도** 발생. 화면상 같은 `계약서.pdf`가 다른 문자열로 취급됨 | DB에는 NFC로 정규화하여 저장, 원래 NFD였는지 `name_was_nfd` 플래그 기록 |
| 2 | **인코딩 미지정** | Windows에서 `open()`의 기본 인코딩은 **cp949** → cp949에 없는 문자에서 오류 | 모든 파일 입출력에 `encoding="utf-8"` 명시, ruff 규칙으로 누락 자동 검사 |
| 3 | **콘솔 출력 오류** | 출력을 파일로 리다이렉트하면 cp949로 인코딩되어 일부 문자에서 `UnicodeEncodeError` | 출력·로그를 UTF-8로 설정, 인코딩 불가 문자는 대체 처리 |
| 4 | **Excel CSV 깨짐** | BOM 없는 UTF-8 | `utf-8-sig`로 저장 |
| 5 | **이미 깨진 파일명 (mojibake)** | Windows에서 만든 ZIP을 다른 환경에서 풀면 `°è¾à¼­.pdf` 같은 이름이 실제 파일명으로 남음 | 원본은 수정하지 않고(원칙 3) `name_suspect_mojibake` 플래그로 보고서에 표시. 오탐 가능성이 있어 1단계는 "의심" 표시까지만 |
| 6 | **유효하지 않은 바이트 파일명** | NAS·외장 드라이브의 비정상 이름 → Python이 surrogate 문자로 변환 → SQLite 저장 시 오류 | 안전한 표기로 변환하여 저장하고 오류 테이블에 기록, 스캔은 계속 |
| 7 | **정렬 순서** | NFD 상태에서는 가나다 정렬이 틀어짐 | NFC 정규화로 해결 |
| 8 | **macOS 파일명 길이** | 255**바이트** 제한, 한글은 글자당 3바이트 → 약 85자 | 이 프로그램은 복사하지 않으므로 직접 영향 없음. 위험 파일만 보고서에 표시 |

### 동작 원리: NFC와 NFD

한글 "가"는 유니코드로 두 가지 방식으로 표현할 수 있습니다.

```
NFC (조합형): 가        → U+AC00          (1개 코드포인트)
NFD (분해형): ㄱ + ㅏ   → U+1100 U+1161   (2개 코드포인트)
```

화면에는 똑같이 보이지만 Python에서 `"가" == "가"`가 `False`가 될 수 있습니다.
Windows는 주로 NFC, macOS는 NFD를 사용하므로 두 환경을 오간 자료에는 두 형태가 섞여 있습니다.
`unicodedata.normalize("NFC", name)`으로 통일하여 비교·검색·정렬 문제를 해결합니다.

---

## 10. 테스트 전략

**핵심 원칙: 모든 테스트는 pytest의 `tmp_path`(임시 폴더)에 가상 파일을 생성하여 수행합니다.**
실제 자료에는 절대 접근하지 않습니다.

| 계층 | 대상 | 방법 |
|---|---|---|
| 단위 테스트 | 모듈별 함수 | 작은 가상 트리 fixture. 순수 함수는 `@pytest.mark.parametrize`로 입력/출력 표 검증 |
| 오류 경로 | 권한 오류, 깨진 링크 | `monkeypatch`로 `os.stat`이 `PermissionError`를 내도록 대체 (실제 권한 변경 불필요) |
| 저장소 | `storage.py` | `sqlite3.connect(":memory:")` 메모리 DB — 빠르고 흔적 없음 |
| 통합 테스트 | CLI 전체 흐름 | `main(["scan", ...])` 직접 호출 후 DB 내용 검증 |
| **원본 불변** | 최우선 원칙 | 스캔 **전후로** 모든 가상 파일의 크기·수정일·내용 해시를 스냅샷하여 **완전히 동일한지** 검증. 출력 경로를 스캔 대상 내부로 지정하면 거부되는지 검증 |
| 한글 파일명 | [9장](#9-한글-파일명-처리)의 사례 | NFD 파일명, 깨진 이름, `㈜`·`①`·`㎡`·전각 공백·이모지 포함 파일명을 생성하여 검증 |
| 플랫폼별 | 생성일, 긴 경로 | `@pytest.mark.skipif(sys.platform != "darwin")` 등 OS별 분기. CI에서 양쪽 모두 실행 |
| 성능 | 5만 개 처리 | `@pytest.mark.slow` 표시, 평소엔 생략하고 `pytest -m slow`로 실행 |

- **커버리지 목표:** 전체 80% 이상, `safety.py`·`scanner.py`·`metadata.py`는 90% 이상
- **개발 습관:** 함수 하나를 만들면 테스트 하나를 함께 작성

---

## 11. CI (자동 테스트)

**CI(Continuous Integration, 지속적 통합)** 는 GitHub에 코드를 push할 때마다
GitHub 서버가 자동으로 테스트를 실행해 주는 것입니다.

```
내 PC (Windows)                     GitHub 서버 (GitHub Actions)
  코드 수정 → git push  ───────▶   ┌ Windows 가상머신: 설치 → pytest ┐
                                   └ macOS 가상머신:   설치 → pytest ┘
                                               │
  커밋 옆에 ✅ / ❌ 표시  ◀────────────────────┘
```

- **이 프로젝트에서의 의미:** macOS 실기기 테스트를 하지 않기로 했으므로,
  macOS 동작을 검증하는 **유일한 수단**이 CI입니다.
- **설정 파일:** `.github/workflows/test.yml`
- **비용:** 공개 저장소이므로 무료
- **원칙 4와의 관계:** CI에 올라가는 것은 코드와 가상 데이터 생성기뿐이며, 실제 자료는 전송되지 않습니다.

---

## 12. 2단계 로드맵

1단계(메타데이터 인벤토리) 이후, Document AI 방향으로 다음 순서의 확장을 검토합니다.

1. **해시 기반 중복 탐지** — 파일 내용을 처음으로 읽는 단계 (읽기 전용 유지)
2. **텍스트 추출** — PDF, HWP/HWPX, Office 문서
3. **문서 분류** — 규칙 기반 → AI 기반 (계약서, 도면, 공문, 사진 등)
4. **GUI** — 실무 사용자를 위한 화면
