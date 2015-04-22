import sys

if sys.version_info < (3, 4):
    from . import pathlib, enum
    sys.modules["pathlib"] = pathlib
    sys.modules["enum"] = enum

    import abc

    class ABC(metaclass=abc.ABCMeta):
        pass

    abc.ABC = ABC
