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


def add_random_ending(text, suffix, frequency, draw=None):
    """Append once before final punctuation; 0 never draws, 100 always applies."""
    import random
    frequency = max(0, min(100, int(frequency)))
    if not suffix.strip() or frequency == 0:
        return text
    if frequency < 100 and (draw or random.random)() >= frequency / 100:
        return text
    match = re.match(r"^(.*?)([.!?…]+)$", text.rstrip(), flags=re.S)
    body, punctuation = match.groups() if match else (text.rstrip(), "")
    ending = suffix.rstrip()
    separator = "" if ending[0].isspace() or ending[0] in ",;:.!?…" else " "
    if ending[-1] in ".!?…":
        punctuation = ""
    return body + separator + ending + punctuation
