from importlib import import_module

from banal import ensure_dict
from servicelayer.extensions import get_entry_point

from ..incremental import skip_incremental


def _get_method(method_name):
    # method A: via a named Python entry point
    func = get_entry_point("memorious.operations", method_name)
    if func is not None:
        return func
    # method B: direct import from a module
    if ":" not in method_name:
        raise ValueError("Unknown method: %s", method_name)
    package, method = method_name.rsplit(":", 1)
    module = import_module(package)
    return getattr(module, method)


def store(context, data):
    """
    an extended store to be able to set skip_incremental
    """
    handler = _get_method(context.params.get("operation", "directory"))
    handler(context, data)
    incremental = ensure_dict(data.get("skip_incremental"))
    if incremental.get("target") == context.stage.name:
        if incremental.get("key") is not None:
            context.set_tag(incremental["key"], True)
    # during testing mode, this will end the scraper, if store stage is set as target
    skip_incremental(context, data)
