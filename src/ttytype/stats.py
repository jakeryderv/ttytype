def calculate_wpm(chars: int, seconds: float) -> float:
    if seconds == 0:
        return 0
    words = chars / 5
    minutes = seconds / 60
    return words / minutes


def calculate_accuracy(typed: str, target: str) -> float:
    if not typed:
        return 0
    correct = sum(a == b for a, b in zip(typed, target))
    return correct / len(typed)
