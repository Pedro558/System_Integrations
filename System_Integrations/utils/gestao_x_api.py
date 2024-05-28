import requests
from abc import ABC, abstractmethod
import json
from ..auth.api_secrets import get_api_token
from .mapper import map_to_requests_response
from collections import defaultdict

#       ORIGINALMENTE DO OpenGestaoXTicket.py

#       Posta ticket no Gestão X e retorna resposta
def post_gestao_x(url, headers, data):
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 200 or response.status_code == 201:
            return {
                "response": response.__dict__,
                "error": False
            }
            
        else:
            return {
                "response": response.__dict__,
                "error": True
            }
    except Exception as error:
        return {
            "response": response.__dict__,
            "error": True,
            "errorMessage": error # TODO AQUI verificar como extrair mensagem
        }
    
def get_gestao_x(url, params):
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            ticket_data = response.json()
            return ticket_data
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_chamados_gestao_x: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_chamados_gestao_x: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_chamados_gestao_x: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET fetch_chamados_gestao_x: {err}")