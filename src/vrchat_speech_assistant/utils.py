from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import deepl


def test_deepl(api_key: str) -> Optional[deepl.Translator]:
    """The function tests if a DeepL API key is valid by checking the usage limit.

    Parameters
    ----------
    api_key : str
        The DeepL API key.

    Returns
    -------
    deepl.Translator or None
        Return the DeepL translator object if the test is passed, None otherwise.
    """
    if not api_key:
        return None
    import deepl
    try:
        translator = deepl.Translator(api_key)
        translator.get_usage()
        return translator
    except deepl.exceptions.DeepLException:
        return None
