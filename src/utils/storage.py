from pathlib import Path


def _get_path_object(file_path):
    if isinstance(file_path, str):
        file_path = Path(file_path)
    if not isinstance(file_path, Path):
        raise TypeError("File path is not of data_type Path: {}".format(file_path.__class__()))
    if not file_path.parent.exists():
        file_path.parent.mkdir(parents=True)
    return file_path


def get_writer(file_path, mode='wb', *args, **kwargs):
    if mode not in ['wb', 'w', 'a', 'ab']:
        raise ValueError("Writer mode {} not supported".format(mode))
    file_path = _get_path_object(file_path)
    return file_path.open(mode, *args, **kwargs)


def get_reader(file_path, mode='rb', *args, **kwargs):
    if mode not in ['rb', 'r']:
        raise ValueError("Reader mode {} not supported".format(mode))
    file_path = _get_path_object(file_path)
    return file_path.open(mode, *args, **kwargs)


def exists(file_path):
    file_path = _get_path_object(file_path)
    return file_path.exists()
