import requests

def map_to_requests_response(response_dict) -> requests.Response:
    # Create a requests.Response instance
    http_response = requests.Response()

    # Set attributes using the dictionary data
    for key, value in http_response.__dict__.items():
        setattr(http_response, key, response_dict.get(key, value))

    return http_response