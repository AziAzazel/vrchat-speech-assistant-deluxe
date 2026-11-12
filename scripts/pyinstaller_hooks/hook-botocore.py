"""Bundle Polly models and shared SDK data; other AWS service models are unused.

Keep root metadata (endpoints, partitions, retry/default configuration) and files
outside data/, including TLS certificates. Source installs retain the full SDK.
"""
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ['html.parser']


def required_for_polly(destination):
    parts = destination.replace('\\', '/').split('/')
    return not (parts[:2] == ['botocore', 'data'] and len(parts) > 2 and parts[2] != 'polly')


datas = [(source, destination) for source, destination in collect_data_files('botocore')
         if required_for_polly(destination)]
