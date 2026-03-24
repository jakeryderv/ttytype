import curses
import time
from ttytype.words import get_words
from ttytype.stats import calculate_wpm, calculate_accuracy


def run(word_count: int = 25):
    curses.wrapper(lambda stdscr: main(stdscr, word_count))


def count_errors(typed: str, target: str) -> int:
    """Count the number of incorrect characters."""
    errors = 0
    for i, char in enumerate(typed):
        if i < len(target) and char != target[i]:
            errors += 1
    return errors


def render_histogram(wpm_samples: list[float], width: int) -> list[str]:
    """Render a simple ASCII histogram of WPM over time."""
    if not wpm_samples or len(wpm_samples) < 2:
        return []

    # Determine dimensions
    hist_width = min(width - 10, 50)
    hist_height = 6

    # Sample down to fit width if needed
    if len(wpm_samples) > hist_width:
        step = len(wpm_samples) / hist_width
        sampled = [wpm_samples[int(i * step)] for i in range(hist_width)]
    else:
        sampled = wpm_samples

    if not sampled:
        return []

    min_wpm = max(0, min(sampled) - 10)
    max_wpm = max(sampled) + 10
    wpm_range = max_wpm - min_wpm if max_wpm > min_wpm else 1

    # Build histogram rows (top to bottom)
    blocks = " ▁▂▃▄▅▆▇█"
    lines = []

    for row in range(hist_height, 0, -1):
        row_threshold = min_wpm + (row / hist_height) * wpm_range
        prev_threshold = min_wpm + ((row - 1) / hist_height) * wpm_range

        line = ""
        for wpm in sampled:
            if wpm >= row_threshold:
                line += "█"
            elif wpm > prev_threshold:
                # Partial block for this row
                fraction = (wpm - prev_threshold) / (row_threshold - prev_threshold)
                block_idx = int(fraction * (len(blocks) - 1))
                line += blocks[block_idx]
            else:
                line += " "

        # Add label on top and bottom rows
        if row == hist_height:
            lines.append(f"{max_wpm:3.0f} ┤{line}│")
        elif row == 1:
            lines.append(f"{min_wpm:3.0f} ┤{line}│")
        else:
            lines.append(f"    │{line}│")

    # Bottom axis
    lines.append(f"    └{'─' * len(sampled)}┘")

    return lines


def wrap_words(words: list[str], max_width: int) -> list[list[str]]:
    """Wrap words into lines that fit within max_width."""
    lines: list[list[str]] = []
    current_line: list[str] = []
    current_length = 0

    for word in words:
        word_len = len(word)
        space_needed = 1 if current_line else 0

        if current_length + space_needed + word_len <= max_width:
            current_line.append(word)
            current_length += space_needed + word_len
        else:
            if current_line:
                lines.append(current_line)
            current_line = [word]
            current_length = word_len

    if current_line:
        lines.append(current_line)

    return lines


def get_current_word_index(typed: str, words: list[str]) -> int:
    """Get the index of the word currently being typed."""
    spaces_typed = typed.count(" ")
    return min(spaces_typed, len(words) - 1)


def main(stdscr, word_count: int):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, 8, -1)  # gray (correct)
    curses.init_pair(2, 1, -1)  # red (incorrect)
    curses.init_pair(3, 7, -1)  # white (current word)
    curses.init_pair(4, 1, -1)  # red (incorrect in current word)
    curses.init_pair(5, 2, -1)  # green (for results)
    curses.curs_set(0)

    while True:  # Restart loop
        words = get_words(word_count)
        target = " ".join(words)
        typed = ""
        start_time = None
        wpm_samples: list[float] = []
        last_sample_time = 0.0

        while len(typed) < len(target):
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            # Calculate live stats
            if start_time is not None:
                elapsed = time.time() - start_time
                wpm = calculate_wpm(len(typed), elapsed)
                accuracy = calculate_accuracy(typed, target[: len(typed)])

                # Sample WPM every 0.5 seconds for histogram
                if elapsed - last_sample_time >= 0.5 and len(typed) > 0:
                    wpm_samples.append(wpm)
                    last_sample_time = elapsed
            else:
                elapsed = 0.0
                wpm = 0.0
                accuracy = 1.0

            # Draw stats at top
            stats_text = f"WPM: {wpm:5.1f}  |  Accuracy: {accuracy:6.1%}"
            stats_x = max(0, (width - len(stats_text)) // 2)
            stdscr.addstr(0, stats_x, stats_text, curses.A_BOLD)

            # Wrap words to fit screen
            max_text_width = min(width - 4, 70)
            wrapped_lines = wrap_words(words, max_text_width)

            # Calculate vertical centering
            total_lines = len(wrapped_lines)
            start_y = max(2, (height - total_lines) // 2)

            # Track current word
            current_word_idx = get_current_word_index(typed, words)

            # Build character position map
            char_pos = 0
            word_idx = 0

            for line_num, line_words in enumerate(wrapped_lines):
                line_text = " ".join(line_words)
                start_x = max(0, (width - len(line_text)) // 2)
                col = start_x
                y = start_y + line_num

                if y >= height - 1:
                    break

                for word_i, word in enumerate(line_words):
                    is_current_word = word_idx == current_word_idx

                    # Draw word
                    for char in word:
                        if char_pos < len(typed):
                            # Already typed
                            if typed[char_pos] == target[char_pos]:
                                attr = curses.color_pair(1)  # gray correct
                            else:
                                if is_current_word:
                                    attr = curses.color_pair(4)  # red
                                else:
                                    attr = curses.color_pair(2)  # red
                        elif char_pos == len(typed):
                            # Current cursor position
                            attr = curses.color_pair(3) | curses.A_BOLD | curses.A_UNDERLINE
                        elif is_current_word:
                            # Rest of current word
                            attr = curses.color_pair(3) | curses.A_BOLD
                        else:
                            # Untyped text
                            attr = curses.A_NORMAL

                        try:
                            stdscr.addch(y, col, char, attr)
                        except curses.error:
                            pass
                        col += 1
                        char_pos += 1

                    word_idx += 1

                    # Draw space after word (except for the very last word)
                    is_last_word = (
                        line_num == len(wrapped_lines) - 1
                        and word_i == len(line_words) - 1
                    )
                    if not is_last_word:
                        if char_pos < len(typed):
                            if typed[char_pos] == " ":
                                attr = curses.color_pair(1)  # gray correct
                            else:
                                attr = curses.color_pair(2)  # red incorrect
                        elif char_pos == len(typed):
                            attr = curses.A_UNDERLINE  # cursor
                        else:
                            attr = curses.A_NORMAL  # untyped

                        try:
                            stdscr.addch(y, col, " ", attr)
                        except curses.error:
                            pass
                        col += 1
                        char_pos += 1

            # Draw help text at bottom
            help_text = "TAB restart  |  ESC quit"
            help_x = max(0, (width - len(help_text)) // 2)
            try:
                stdscr.addstr(height - 1, help_x, help_text, curses.color_pair(1))
            except curses.error:
                pass

            stdscr.refresh()
            key = stdscr.getch()

            if start_time is None and key not in (127, curses.KEY_BACKSPACE, 9):
                start_time = time.time()

            if key in (127, curses.KEY_BACKSPACE):
                typed = typed[:-1]
            elif key == 27:  # escape to quit
                return
            elif key == 9:  # tab to restart
                break
            elif 32 <= key <= 126:
                typed += chr(key)

        # Check if we broke out early (restart)
        if len(typed) < len(target):
            continue

        # Test complete - calculate final stats
        elapsed = time.time() - start_time
        wpm_samples.append(calculate_wpm(len(typed), elapsed))  # Final sample

        errors = count_errors(typed, target)
        raw_wpm = calculate_wpm(len(typed), elapsed)
        # Net WPM accounts for errors (subtract error penalty)
        net_wpm = max(0, raw_wpm - (errors * 60 / elapsed / 5))
        accuracy = calculate_accuracy(typed, target)

        # Show results screen
        if not show_results(stdscr, elapsed, len(typed), errors, raw_wpm, net_wpm, accuracy, wpm_samples):
            return  # User pressed ESC


def show_results(
    stdscr,
    elapsed: float,
    char_count: int,
    errors: int,
    raw_wpm: float,
    net_wpm: float,
    accuracy: float,
    wpm_samples: list[float],
) -> bool:
    """Display results screen. Returns True to restart, False to quit."""
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Build results content
        results: list[tuple[str, int]] = []  # (text, attr)

        # Title
        results.append(("─── Results ───", curses.A_BOLD))
        results.append(("", curses.A_NORMAL))

        # Main stats
        results.append((f"  Net WPM:    {net_wpm:5.1f}", curses.color_pair(5) | curses.A_BOLD))
        results.append((f"  Raw WPM:    {raw_wpm:5.1f}", curses.A_NORMAL))
        results.append((f"  Accuracy:   {accuracy:5.1%}", curses.A_NORMAL))
        results.append(("", curses.A_NORMAL))

        # Details
        minutes = int(elapsed // 60)
        seconds = elapsed % 60
        if minutes > 0:
            time_str = f"{minutes}m {seconds:.1f}s"
        else:
            time_str = f"{seconds:.1f}s"

        results.append((f"  Time:       {time_str}", curses.A_NORMAL))
        results.append((f"  Characters: {char_count}", curses.A_NORMAL))
        results.append((f"  Errors:     {errors}", curses.color_pair(2) if errors > 0 else curses.A_NORMAL))
        results.append(("", curses.A_NORMAL))

        # WPM histogram
        histogram = render_histogram(wpm_samples, width)
        if histogram:
            results.append(("  WPM over time:", curses.A_DIM))
            for line in histogram:
                results.append((f"  {line}", curses.A_NORMAL))
            results.append(("", curses.A_NORMAL))

        # Instructions
        results.append(("", curses.A_NORMAL))
        results.append(("TAB restart  |  ESC quit", curses.color_pair(1)))

        # Calculate vertical centering
        start_y = max(0, (height - len(results)) // 2)

        # Draw results
        for i, (text, attr) in enumerate(results):
            y = start_y + i
            if y >= height:
                break
            x = max(0, (width - len(text)) // 2)
            try:
                stdscr.addstr(y, x, text, attr)
            except curses.error:
                pass

        stdscr.refresh()
        key = stdscr.getch()

        if key == 9:  # Tab to restart
            return True
        elif key == 27:  # ESC to quit
            return False
