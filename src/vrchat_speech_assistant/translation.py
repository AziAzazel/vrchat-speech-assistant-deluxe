"""Shared DeepL request options, including explicitly selected beta languages."""
from vrchat_speech_assistant.languages import DEEPL, DEEPL_BETA_LANGUAGES


def translate_message(translator, text, source, target, options):
    request = dict(
        source_lang=DEEPL[source].split('-')[0], target_lang=DEEPL[target],
        split_sentences=int(options['split_sentences']),
        formality={'Default': 'default', 'Formal': 'prefer_more', 'Informal': 'prefer_less'}[options['formality']],
    )
    if source in DEEPL_BETA_LANGUAGES or target in DEEPL_BETA_LANGUAGES:
        request.update(extra_body_parameters={'enable_beta_languages': True}, model_type='quality_optimized')
    return translator.translate_text(text, **request).text
