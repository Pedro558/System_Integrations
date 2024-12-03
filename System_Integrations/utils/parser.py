from types import FunctionType
import functools

def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))

def get_value(item, funcExtractor:FunctionType, defaultValue):
    try:
        return funcExtractor(item)
    except:
        return defaultValue

def get_value_obj(obj, attr):
    if isinstance(obj, dict):
        return obj.get(attr)
    else:
        return rgetattr(obj, attr, None)

def group_by(arr, props):
    # takes out of list if it is only one element
    props = props if isinstance(props, list) and len(props) > 1 else props[0]
    grouped_data = {}
    for item in arr:
        if isinstance(props, list):
            key = tuple(get_value_obj(item, prop) for prop in props)
        else:
            key = (get_value_obj(item, props))

        grouped_data.setdefault(key, []).append(item)

    return grouped_data