import re

_DIGITS = {'일':1, '이':2, '삼':3, '사':4, '오':5, '육':6, '칠':7, '팔':8, '구':9}
_BIG_UNITS = {'만':10000, '억':100000000, '조':1000000000000}
_SMALL_UNITS = {'십':10, '백':100, '천':1000}


def parse_korean_amount(text: str):
    text = re.sub(r'\s+', '', text)
    if text[:1] == "금":
        text = text[1:]
    if text[-1:] == "원":
        text = text[:-1]

    split_korean_amount = re.split(r"([조억만])", text)
    total = 0
    int_amount = 0

    for korean_amount in split_korean_amount:
        if korean_amount not in _BIG_UNITS:
            int_amount = _parse_small_part(korean_amount)
        else:
            if korean_amount == '조':
                if int_amount != 0:
                    total += int_amount * 1000000000000
                    int_amount = 0
                else:
                    total += 1000000000000
            elif korean_amount == '억':
                if int_amount != 0:
                    total += int_amount * 100000000
                    int_amount = 0
                else:
                    total += 100000000    
            elif korean_amount == '만':
                if int_amount != 0:
                    total += int_amount * 10000
                    int_amount = 0
                else:
                    total += 10000
                    
    total += int_amount
    return total


def _parse_small_part(split_korean_amount: str):
    _split_korean_amount = re.split(r"([천백십])", split_korean_amount)
    total = 0
    int_amount = 0

    for korean_amount in _split_korean_amount:
        if korean_amount in _DIGITS:
            int_amount = _DIGITS[korean_amount]
        else:
            if korean_amount == '천':
                if int_amount != 0:
                    total += int_amount * 1000
                    int_amount = 0
                else:
                    total += 1000
            elif korean_amount == '백':
                if int_amount != 0:
                    total += int_amount * 100
                    int_amount = 0
                else:
                    total += 100
            elif korean_amount == '십':
                if int_amount != 0:
                    total += int_amount * 10
                    int_amount = 0
                else:
                    total += 10
    total += int_amount
    return total