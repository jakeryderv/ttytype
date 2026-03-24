import argparse
from ttytype.game import run


def main():
    parser = argparse.ArgumentParser(description="Terminal typing test")
    parser.add_argument("-w", "--words", type=int, default=25)
    args = parser.parse_args()
    run(word_count=args.words)
