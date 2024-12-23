from re import I
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

def parse_commit_rate_to(commit_rate, unit="MB"):
    commit_rate = commit_rate if commit_rate else 0

    size_units = {'B':1, 'KB': 1e3, 'MB': 1e6, 'GB': 1e9, 'TB': 1e12, 'PB': 1e15}

    return commit_rate / size_units.get(unit.upper().replace('s',''), 1)

def get_visual_commit_rate(commit_rate, bps:bool = False):
    commit_rate = commit_rate if commit_rate else 0

    value = 0
    unit = ""
    unit_bps = ""
    if commit_rate >= 1e9:
        value = parse_commit_rate_to(commit_rate, "GB")
        unit = "GB"
        unit_bps = "Gbps"
    else:
        value = parse_commit_rate_to(commit_rate, "MB")
        unit = "MB"
        unit_bps = "Mbps"

    if bps: 
        value = value * 8

    return str(value).replace(".0", "") + (unit if not bps else unit_bps)
