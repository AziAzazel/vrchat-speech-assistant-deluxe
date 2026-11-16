"""Independent recognition/output pairs; keys use the existing action registry."""
LANGUAGE_PRESETS = {
    'language_preset_1': ('Polish', 'Polish'),
    'language_preset_2': ('Polish', 'English'),
    'language_preset_3': ('English', 'English'),
    'language_preset_4': ('Polish', 'Japanese'),
}
DEFAULT_PAIRS = {f'{action}_{field}': value for action, pair in LANGUAGE_PRESETS.items()
                 for field, value in zip(('source', 'target'), pair)}


def language_pair(config, action):
    default = LANGUAGE_PRESETS[action]
    return tuple(config['LANGUAGE_PRESETS'].get(f'{action}_{field}', value)
                 for field, value in zip(('source', 'target'), default))
