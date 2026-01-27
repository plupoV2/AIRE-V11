from underwriting import score_to_grade_detail, verdict_from_score


def test_grade_detail_boundaries():
    assert score_to_grade_detail(97) == "A+"
    assert score_to_grade_detail(93) == "A"
    assert score_to_grade_detail(90) == "A-"
    assert score_to_grade_detail(87) == "B+"
    assert score_to_grade_detail(83) == "B"
    assert score_to_grade_detail(80) == "B-"
    assert score_to_grade_detail(77) == "C+"
    assert score_to_grade_detail(73) == "C"
    assert score_to_grade_detail(70) == "C-"
    assert score_to_grade_detail(67) == "D+"
    assert score_to_grade_detail(63) == "D"
    assert score_to_grade_detail(60) == "D-"
    assert score_to_grade_detail(55) == "F+"
    assert score_to_grade_detail(50) == "F"
    assert score_to_grade_detail(0) == "F-"


def test_verdict_from_score():
    assert verdict_from_score(95) == "BUY"
    assert verdict_from_score(85) == "BUY (Selective)"
    assert verdict_from_score(75) == "WATCH / NEGOTIATE"
    assert verdict_from_score(65) == "PASS (Most cases)"
    assert verdict_from_score(10) == "AVOID"
