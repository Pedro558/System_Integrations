import requests
import json

#     ORIGINALMENTE DO OpenGestaoXTicket.py

#     BUSCA TOKEN DE AUTORIZAÇÃO NO AMBIENTE DO SERVICENOW
def get_servicenow_auth_token(envUrl, clientId, clientSecret, refreshToken):
    url = envUrl
    url += "/" if not url.endswith("/") else ""
    url += 'oauth_token.do'

    body = {
        'grant_type': 'refresh_token',
        'client_id':clientId,
        'client_secret':clientSecret,
        'refresh_token':refreshToken,
    }

    response = requests.post(url, data=body)
    data = response.json()

    
    return data['access_token']


#     CONSULTA UMA TABELA NO SERVICENOW
def get_servicenow_table_data(envUrl, table_name, params, token):
    url = envUrl + 'api/now/table/' + table_name

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+token,
        }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        # breakpoint()
        table_data = response.json()        

        if response.status_code == 200:
            # if not 'result' in table_data or len(table_data['result']) == 0:
            #     print(f'No data found in {table_name} for the following params: {params}')
            return table_data['result'] if "result" in table_data else None
        
        else:
            #breakpoint()
            response.raise_for_status()
        
    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f'HTTP error occurred on GET get_servicenow_table_data: {err}')
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f'Connection error on GET get_servicenow_table_data: {err}')
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f'Request timed out on GET get_servicenow_table_data: {err}')
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f'An error occurred on GET get_servicenow_table_data: {err}')
    
def post_to_servicenow_table(envUrl, table_name, data, token, params={}):
    url = envUrl + 'api/now/table/' + table_name

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+token,
        }

    response = requests.post(url, headers=headers, params = params, data=json.dumps(data))
    try:
        if response.status_code == 200 or response.status_code == 201:
            return {
                #"item": ticket['item'],
                "response": response.__dict__,
                "response_http": response,
                "error": False
            }
        else:
            response.raise_for_status()

    except Exception as error:
        return {
            #"item": ticket,
            "response": response.__dict__,
            "response_http": response,
            "error": True,
            "errorMsg": error # TODO AQUI verificar como extrair mensagem
        }

def patch_servicenow_record(envUrl, table_name, record_sys_id, data, token, params={}):
    url = envUrl + 'api/now/table/' + table_name +"/"+record_sys_id

    headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer '+token,
        }

    response = requests.patch(url, headers=headers, params=params, data=json.dumps(data))
    try:
        if response.status_code == 200 or response.status_code == 201:
            return {
                #"item": ticket['item'],
                "response": response.__dict__,
                "response_http": response,
                "error": False
            }
        else:
            response.raise_for_status()

    except Exception as error:
        return {
            #"item": ticket,
            "response": response.__dict__,
            "response_http": response,
            "error": True,
            "errorMsg": error # TODO AQUI verificar como extrair mensagem
        }

#     CONSTROI A DESCRIÇÃO BASEADO EM UM PARAMETRO
def descriptionBuilder(variables, descConfig):
    descricao = ""
    for config in descConfig:
        aValue = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == config["var"]]
                                                        #and config["extraValidator"](variable) if "extraValidator" in config else True]
        descricao += config["msg"] + aValue[0]["sc_item_option.value"] if aValue[0]["sc_item_option.value"] else ""
        
    return descricao

def new_cross_validation(envUrl, headers, params, data):
    url = envUrl + '/api/eldi/new_cross/validate'
    response = requests.get(url, headers=headers, params=params, data=json.dumps(data))
    try:
        if response.status_code == 200 or response.status_code == 201:
            return {
                #"item": ticket['item'],
                "response": response,
                "error": False
            }
        else:
            response.raise_for_status()

    except Exception as error:
        return {
            #"item": ticket,
            "response": response,
            "error": True,
            "errorMsg": error # TODO AQUI verificar como extrair mensagem
        }


def client_monitoring_multi_post(envUrl, data, token, params={}):
    url = envUrl + '/api/eldi/client_links_monitoring/multi_insert'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token,
    }
    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    try:
        response.raise_for_status()
        return {
            "response": response,
            "error": False
        }

    except Exception as error:
        return {
            "response": response,
            "error": True,
            "errorMsg": error # TODO AQUI verificar como extrair mensagem
        }

def client_monitoring_multi_post_img(envUrl, data, token, params={}):
    url = envUrl + 'api/eldi/client_links_monitoring/multi_insert_image_table'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+token,
    }
    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))
    try:
        response.raise_for_status()
        return {
            "response": response,
            "error": False
        }

    except Exception as error:
        return {
            "response": response,
            "error": True,
            "errorMsg": error # TODO AQUI verificar como extrair mensagem
        }





