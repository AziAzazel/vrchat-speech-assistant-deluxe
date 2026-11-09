"""Text corrections shared by recognition and manual input."""
import re


def correct_nicknames(text, corrections):
    """Replace literal whole names once, longest first, without cascading."""
    names = {key.casefold(): value for key, value in corrections.items() if key.strip()}
    if not names:
        return text
    pattern = r"(?<!\w)(?:" + "|".join(
        re.escape(key) for key in sorted(names, key=len, reverse=True)
    ) + r")(?!\w)"
    return re.sub(pattern, lambda match: names[match.group().casefold()], text, flags=re.I)


def decorate_chatbox(text, rules, source_text=""):
    """Append each matching addition once; speech is deliberately unaffected."""
    additions = []
    for keyword, addition in rules.items():
        if not keyword.strip() or not addition.strip():
            continue
        pattern = r"(?<!\w)" + re.escape(keyword.strip()) + r"(?!\w)"
        if any(re.search(pattern, sentence, flags=re.I) for sentence in (text, source_text)):
            if addition not in additions:
                additions.append(addition)
    return " ".join([text, *additions])
