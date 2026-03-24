from ttytype.stats import calculate_wpm, calculate_accuracy


def test_wpm():
    assert calculate_wpm(250, 60) == 50


def test_accuracy():
    assert calculate_accuracy("hello", "hello") == 1.0
    assert calculate_accuracy("hxllo", "hello") == 0.8
