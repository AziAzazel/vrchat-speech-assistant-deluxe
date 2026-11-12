"""The smaller package retains Polly models, endpoint metadata and TLS roots."""
from pathlib import Path
import runpy
import pytest


def test_polly_data_filter_keeps_models_and_common_data():
    pytest.importorskip('PyInstaller')
    namespace = runpy.run_path(str(Path(__file__).parents[1]/'scripts/pyinstaller_hooks/hook-botocore.py'))
    data = namespace['datas']
    paths = [destination.replace('\\', '/') for _, destination in data]
    names = {Path(source).name for source, _ in data}
    assert any(path.startswith('botocore/data/polly/') for path in paths)
    assert all(not path.startswith('botocore/data/s3/') for path in paths)
    assert {'cacert.pem', 'endpoints.json', 'partitions.json', '_retry.json'} <= names
    assert any('service-2.json' in name for name in names)
