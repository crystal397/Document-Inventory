from amount_parser import parse_korean_amount

def test_billions_and_ten_thousands():
    korean_amount = "금삼십억오천만원"
    total = parse_korean_amount(korean_amount)

    assert total == 3050000000


def test_unit_without_digit_means_one():
    korean_amount = "금십만원"
    total = parse_korean_amount(korean_amount)

    assert total == 100000
 

def test_arabic_digits_return_zero():
    korean_amount = "금3,050,000,000원"
    total = parse_korean_amount(korean_amount)

    assert total == 0


def test_small_units_inside_big_unit():
    korean_amount = "금일억오천이백만원"
    total = parse_korean_amount(korean_amount)

    assert total == 152000000


def test_spaces_are_ignored():
    korean_amount = ' 금 삼십억 오천만원 '
    total = parse_korean_amount(korean_amount)

    assert total == 3050000000

def test_big_unit_without_digit_means_one():
    korean_amount = "금만원"
    total = parse_korean_amount(korean_amount)

    assert total == 10000