from flask import jsonify, request


def error(message, status):
    """Return a consistent JSON error response."""
    return jsonify({"error": message}), status


def json_body():
    """Return the request JSON as a dict (empty dict if missing or invalid)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}
