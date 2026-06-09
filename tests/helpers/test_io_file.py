import os

from src.helpers.io_file import IOFile


def test_get_real_path_from_relative_path() -> None:
    your_instance = IOFile()

    relative_path = os.path.normpath("example_folder/example_file.txt")
    expected_result = os.path.realpath(os.path.join(os.path.abspath("."), relative_path))

    result = your_instance.get_real_path_from_relative_path(relative_path)
    assert result == expected_result

    absolute_path = os.path.normpath("/absolute/path/to/some/file.txt")
    _drive, path = os.path.splitdrive(your_instance.get_real_path_from_relative_path(absolute_path))
    assert path == absolute_path

    different_relative_path = os.path.normpath("another_folder/another_file.txt")
    different_expected_result = os.path.realpath(os.path.join(os.path.abspath("."), different_relative_path))
    assert your_instance.get_real_path_from_relative_path(different_relative_path) == different_expected_result
