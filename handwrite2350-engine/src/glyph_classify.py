import unicodedata


S_BASE = 0xAC00
S_END = 0xD7A3
L_COUNT = 19
V_COUNT = 21
T_COUNT = 28
N_COUNT = V_COUNT * T_COUNT

VERTICAL_VOWELS = {0, 1, 2, 3, 4, 5, 6, 7, 20}
HORIZONTAL_VOWELS = {8, 12, 13, 17, 18}
MIXED_VOWELS = {9, 10, 11, 14, 15, 16, 19}


def decompose_hangul_syllable(ch: str):
    if len(ch) != 1:
        raise ValueError(f"decompose_hangul_syllable expects one character, got {len(ch)}")

    codepoint = ord(ch)
    if not S_BASE <= codepoint <= S_END:
        return None

    s_index = codepoint - S_BASE
    l_index = s_index // N_COUNT
    v_index = (s_index % N_COUNT) // T_COUNT
    t_index = s_index % T_COUNT
    return l_index, v_index, t_index


def classify_hangul_layout(ch: str) -> str:
    decomposed = decompose_hangul_syllable(ch)
    if decomposed is None:
        return "hangul_jamo"

    _, v_index, t_index = decomposed
    final_suffix = "with_final" if t_index > 0 else "no_final"

    if v_index in VERTICAL_VOWELS:
        vowel_group = "vertical"
    elif v_index in HORIZONTAL_VOWELS:
        vowel_group = "horizontal"
    elif v_index in MIXED_VOWELS:
        vowel_group = "mixed"
    else:
        vowel_group = "mixed"

    return f"hangul_{vowel_group}_{final_suffix}"


def classify_glyph(ch: str) -> str:
    if len(ch) != 1:
        raise ValueError(f"classify_glyph expects one character, got {len(ch)}")

    codepoint = ord(ch)
    category = unicodedata.category(ch)

    if ch in ".":
        return "punct_bottom_dot"
    if ch in ",;:":
        return "punct_bottom_comma"
    if ch in "'\"`^":
        return "punct_top"
    if ch in "-":
        return "punct_horizontal_mid"
    if ch in "_":
        return "punct_horizontal_bottom"
    if ch in "=+*<>~":
        return "punct_operator"
    if ch in "()[]{}":
        return "punct_bracket"
    if ch in "/\\|":
        return "punct_slash"
    if ch in "@#$%&":
        return "punct_large_symbol"
    if 0x0021 <= codepoint <= 0x007E and not ch.isalnum():
        return "punct_middle"
    if "0" <= ch <= "9":
        if ch == "1":
            return "digit_one"
        return "digit"
    if "A" <= ch <= "Z":
        if ch in "MW":
            return "latin_upper_wide"
        if ch == "I":
            return "latin_upper_narrow"
        if ch == "Q":
            return "latin_upper_q"
        return "latin_upper"
    if "a" <= ch <= "z":
        if ch in "mw":
            return "latin_lower_wide"
        if ch in "bdfhk":
            return "latin_lower_ascender"
        if ch in "gqpy":
            return "latin_lower_descender"
        if ch in "il":
            return "latin_lower_narrow"
        if ch == "t":
            return "latin_lower_t"
        if ch == "j":
            return "latin_lower_j"
        return "latin_lower_xheight"
    if S_BASE <= codepoint <= S_END:
        return classify_hangul_layout(ch)
    if 0x1100 <= codepoint <= 0x11FF or 0x3130 <= codepoint <= 0x318F:
        return "hangul_jamo"
    if category.startswith("P"):
        return "punctuation"
    if category.startswith("S"):
        return "symbol"
    if category.startswith("N"):
        return "number"
    if category.startswith("L"):
        return "letter"
    return "other"
