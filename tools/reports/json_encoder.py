import json

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'type') and hasattr(obj, 'value'):
            return {
                'type': obj.type,
                'value': obj.value,
                'raw_value': getattr(obj, 'raw_value', None)
            }
        try:
            return dict(obj)
        except (TypeError, ValueError):
            try:
                return str(obj)
            except Exception:
                return repr(obj)
