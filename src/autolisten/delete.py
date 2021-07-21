import shutil as su
from datetime import datetime, timedelta
import pathlib
from os import walk, path
from typing import List

# This script will be responsible for the deletion portion of autolisten.


def date_parser(days: int) -> datetime:
    """Parses the date to create a datetime

    Args:
            days (int): the number of days that have passed

    Returns:
            datetime: A datetime representing the latest date.
    """
    now = datetime.now()
    new_date = now - timedelta(days=days)
    return new_date


def delete_folders(location: pathlib.Path, days: int):
    """Deletes all the folders older than a certain date in a directory.

    Args:
            location (pathlib.Path): [description]
            days (int): [description]
    """

    dirs = get_dirs(location)
    date_parsed = date_parser(days)
    for directory in dirs:
        try:
            date = datetime.strptime(directory, "%Y-%m-%d")
        except ValueError:
            continue
        else:
            if date_parsed > date:
                print("Deleting directory {}".format(directory))
                su.rmtree(path.join(location, directory))


def get_dirs(location: pathlib.Path) -> List[str]:
    """Returns all the files in a directory.


    Args:
            location (pathlib.Path): location of the directory

    Returns:
            List[str]: All the directorys in the given location
    """
    f = []
    for (_, dirnames, _) in walk(location):
        f.extend(dirnames)
        break
    return f


if __name__ == "__main__":
    delete_folders("/User/Desktop", 7)
