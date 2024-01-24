try:
    from ._version import __version__
except ModuleNotFoundError:
    __version__ = "0.0.dev"
    version_tuple = (0, 0, "dev")
