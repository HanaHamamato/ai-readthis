"""One-use arithmetic CAPTCHA rendered as SVG using only the standard library.

Ported from the original scripts/captcha.py so the challenge is generated
in-process (no external python binary required on the host).
"""
from __future__ import annotations

import random
import secrets


def generate() -> dict[str, str]:
    random.seed(secrets.randbits(128))
    a = random.randint(4, 19)
    b = random.randint(2, 9)
    operator = random.choice(["+", "-"])
    if operator == "-" and a <= b:
        a, b = b + 3, a
    answer = a + b if operator == "+" else a - b
    expression = f"{a}{operator}{b}=?"

    segments = {
        "a": "M 5 2 L 19 2", "b": "M 21 4 L 21 17", "c": "M 21 21 L 21 34",
        "d": "M 5 36 L 19 36", "e": "M 3 21 L 3 34", "f": "M 3 4 L 3 17",
        "g": "M 5 19 L 19 19",
    }
    digits = {
        "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
        "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "abfgcd",
    }
    paths = []
    for index, char in enumerate(expression):
        x = 18 + index * 33 + random.randint(-2, 2)
        y = 18 + random.randint(-4, 4)
        angle = random.randint(-9, 9)
        color = random.choice(["#42335e", "#634a86", "#7956a2", "#50406f"])
        if char in digits:
            strokes = " ".join(f'<path d="{segments[s]}" />' for s in digits[char])
        elif char == "+":
            strokes = '<path d="M 12 10 L 12 30 M 2 20 L 22 20" />'
        elif char == "-":
            strokes = '<path d="M 2 20 L 22 20" />'
        elif char == "=":
            strokes = '<path d="M 2 15 L 22 15 M 2 25 L 22 25" />'
        else:
            strokes = '<path d="M 3 8 Q 6 1 15 3 Q 25 5 18 15 L 12 21 M 12 32 L 12 34" />'
        paths.append(
            f'<g transform="translate({x} {y}) rotate({angle} 12 19)" fill="none" '
            f'stroke="{color}" stroke-linecap="round" stroke-linejoin="round" '
            f'stroke-width="3.3">{strokes}</g>'
        )

    noise = []
    for _ in range(28):
        x, y = random.randrange(250), random.randrange(90)
        noise.append(f'<circle cx="{x}" cy="{y}" r="{random.choice([.6, .9, 1.2])}" fill="#b5a5d3" opacity=".65"/>')
    for _ in range(3):
        y = random.randrange(20, 70)
        noise.append(
            f'<path d="M 3 {y} Q 85 {y + random.randint(-14, 14)} 134 {y} '
            f'T 248 {y + random.randint(-10, 10)}" fill="none" stroke="#a993c7" '
            f'stroke-width=".8" opacity=".4"/>'
        )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="250" height="90" viewBox="0 0 250 90">'
        '<rect width="250" height="90" rx="15" fill="#f6f2fc"/>'
        + "".join(noise)
        + "".join(paths)
        + "</svg>"
    )
    return {"answer": str(answer), "svg": svg}
