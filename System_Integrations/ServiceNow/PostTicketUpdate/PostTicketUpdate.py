# TODO É necessário separar esse código em diversos módulos?
# TODO PRECISO VERIFICAR A CONDIÇÃO DE ABERTURA DE CHAMADO NO GESTÃO X

import requests
import json
from ...auth.api_secrets import get_api_token
from ...utils.mapper import map_to_requests_response

#URLs
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow = "https://eleadev.service-now.com/"

#Tokens
gestao_x_login = get_api_token('gestao-x-prd-login')
#print(gestao_x_login)
gestao_x_userId = get_api_token('gestao-x-prd-userid')
#print(gestao_x_userId)
gestao_x_token = get_api_token('gestao-x-prd-api-token')
#print(gestao_x_token)
servicenow_client_id = get_api_token('servicenow-dev-client-id-oauth')
#print(servicenow_client_id)
servicenow_client_secret = get_api_token('servicenow-dev-client-secret-oauth')
#print(servicenow_client_secret)
service_now_refresh_token = get_api_token('servicenow-dev-refresh-token-oauth')
#print(service_now_refresh_token)

#Parametros da API https://csc.everestdigital.com.br/API/api/chamado/RetornaChamadosSolicitante
params_fetch_chamados_gestao_x = {
    "Usuarioid": gestao_x_userId,
    "Token": gestao_x_token,
}

#Parametros da API https://csc.everestdigital.com.br/API/api/chamado/RetornaHistoricoChamado
params_fetch_historico_chamado_gestao_x = {
    "CodigoChamado":"",
    "Token":gestao_x_token,
    "InformacaoPublica":"true",
}

#Variavel de parametros para GET na API do ServiceNow
#Recebe uma Encoded Query no formato do ServiceNow de acordo com a necessidade dentro das funções onde é necessário
params_encoded_query = {
    "sysparam_query": "",
    "sysparm_fields": ""
}



def get_auth_token():
    url = url_servicenow+"/oauth_token.do"
    body = {
        "grant_type": "refresh_token",
        "client_id":servicenow_client_id,
        "client_secret":servicenow_client_secret,
        "refresh_token":service_now_refresh_token, #TODO perguntar pro filipe sobre a localização dessas variaveis dentro do código
    }

    response = requests.post(url, data=body)
    data = response.json()
    #print(data)

    return data["access_token"]



def fetch_work_notes(params, token):
    url = url_servicenow+"api/now/table/u_integradora_gestao_x_atualizacoes"

    params["sysparm_query"] = "u_posted=False"
    params["sysparm_fields"] = "u_ticket_gestao_x.u_ticket_gestao_x, u_descricao, u_data_da_atualizacao"

    headers = {
            "Content-Type": "application/json",
            "Accept":"application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        work_notes = response.json()
        #print("voltou response")
        if not 'result' in work_notes or len(work_notes['result']) == 0:
            raise Exception("No Work Notes found")

        if response.status_code == 200:        
            return work_notes['result']
        
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_work_notes: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_work_notes: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_work_notes: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on GET fetch_work_notes: {err}")



def atualiza_gestao_x(work_notes):
    try:
        if not work_notes:
            raise Exception("Work Notes array is empty")

        url = url_gestao_x+"api/chamado/AlterarCampoChamado"
        
        headers = {
            "Content-Type": "application/json",
            "Application": ""
        }
    
        response = requests.Response()
        response_aux = requests.Response()
        results = []

        for work_note in work_notes:
            CodigoChamado = work_note['u_ticket_gestao_x.u_ticket_gestao_x']

            params = {
                "CodigoChamado": CodigoChamado,
                "Token": gestao_x_token
            }

            response_aux = requests.get(url_gestao_x+"api/chamado/RetornaDetalhesChamados", headers=headers, params=params)
            if response_aux.status_code == 200 or response_aux.status_code == 201:
                aux_info = response_aux.json()

                loginResponsavel = aux_info['RESPONSAVEL_LOGIN_USER']
                status = aux_info['STATUS_ID']

            else:
                response_aux.raise_for_status()


            body = {
                "CodigoChamado": CodigoChamado,
                "Token": gestao_x_token,
                "Descricao": work_note['u_descricao'],
                "Status": status,
                "LoginResponsavel": loginResponsavel
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(body))
            if response.status_code == 200 or response.status_code == 201:
                results.append({
                    "item": work_note,
                    "response": response.__dict__,
                })  
            else:
                response.raise_for_status()

        return results

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST atualiza_gestao_x: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST atualiza_gestao_x: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST atualiza_gestao_x: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on POST atualiza_gestao_x: {err}")  
    except Exception as err: #generic
        raise Exception(err)
                
    
    
snow_token = get_auth_token()
work_notes = fetch_work_notes(params_encoded_query, snow_token)
results = atualiza_gestao_x(work_notes)

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Update from {result['item']['u_data_da_atualizacao']} of Ticket {result['item']['u_ticket_gestao_x']} was sent to ServiceNow")
            else:
                print(f"Error while trying to update Ticket {result['item']['u_ticket_gestao_x']} with {result['item']['u_data_da_atualizacao']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")