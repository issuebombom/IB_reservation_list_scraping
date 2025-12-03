def listing_month_date(start_date: int, end_date: int):
    """NOTE: 두 월 사이의 달들을 리스팅
    202511, 202602 -> [202511, 202512, 202601, 202602]
    """
    result = []
    y, m = divmod(start_date, 100)

    # m이 11이면 그대로, divmod는 m=11을 줌
    while True:
        result.append(y * 100 + m)
        if y * 100 + m == end_date:
            break

        # 다음 달로 이동
        m += 1
        if m == 13:
            m = 1
            y += 1

    return result
