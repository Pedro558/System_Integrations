from types import FunctionType

def get_value(item, funcExtractor:FunctionType, defaultValue):
    try:
        return funcExtractor(item)
    except:
        return defaultValue