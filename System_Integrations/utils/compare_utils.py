def is_response_ok(response):
    return 200 <= response.status_code and response.status_code <= 299