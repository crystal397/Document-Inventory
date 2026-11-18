"""스모크 테스트: 패키지가 올바르게 설치되고 import 되는지만 확인한다.

'스모크 테스트'는 전자제품에 처음 전원을 넣고 연기가 나는지 보는 데서 유래한 말로,
"최소한 켜지기는 하는가?"를 확인하는 가장 기본적인 테스트다.
"""

import doc_inventory


def test_package_imports():
    assert doc_inventory.__version__ == "0.1.0"
