import pytest


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Simulate DATA_DIR with a temporary directory."""
    return str(tmp_path)
