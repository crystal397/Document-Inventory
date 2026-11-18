"""pytest 공용 fixture.

conftest.py에 정의한 fixture는 같은 폴더의 모든 테스트 파일에서 import 없이 쓸 수 있다.
테스트 함수의 인자 이름을 fixture 이름과 같게 적으면 pytest가 자동으로 넣어준다.
"""

import pytest
from make_fake_dataset import FakeDataset, generate_dataset


@pytest.fixture
def fake_dataset(tmp_path) -> FakeDataset:
    """작은 가상 자료 트리 (일반 파일 30개 + 특수 사례).

    tmp_path는 pytest 내장 fixture로, 테스트마다 새 임시 폴더를 주고
    오래된 임시 폴더는 pytest가 알아서 정리한다. 실제 자료에는 절대 접근하지 않는다.
    """
    return generate_dataset(tmp_path / "data", n_files=30, n_cases=2, seed=1)
