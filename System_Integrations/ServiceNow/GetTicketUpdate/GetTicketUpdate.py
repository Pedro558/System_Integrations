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
}



#Busca os chamados em acompanhamento no Gestão X
def fetch_chamados_gestao_x(url, params):
    try:
        response = requests.get(url+"api/chamado/RetornaChamadosSolicitante", params=params)
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



#Busca as atualizações de um dado chamado no Gestão X
def fetch_historico_chamado_gestao_x(url, params, ticket):
    try:
        params["CodigoChamado"] = ticket
        response = requests.get(url+"api/chamado/RetornaHistoricoChamado", params=params)
        if response.status_code == 200:
            historic_data = response.json()
            return historic_data
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_historico_chamado_gestao_x: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_historico_chamado_gestao_x: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_historico_chamado_gestao_x: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET fetch_historico_chamado_gestao_x: {err}")



#Para cada chamado ativo, busca seu histórico e adiciona ele no array 'data'
def process_historico(ticket_data):
        data = []
        if ticket_data:
            for ticket in ticket_data:
                codigo_ticket = ticket.get('CODIGO')
                history_data = fetch_historico_chamado_gestao_x(url_gestao_x, params_fetch_historico_chamado_gestao_x, codigo_ticket)
                
                if history_data:
                    for entry in history_data:
                        if "Atualização através do ServiceNow:" not in entry.get("DESCRICAO"):
                            codigo = entry.get("CODIGO")
                            descricao = entry.get("DESCRICAO")
                            status = entry.get("STATUS_ID")
                            data_historico = entry.get("DATA_HISTORICO")
                        
                            entry_dic = {
                                "u_ticket_gestao_x":codigo,
                                "u_descricao":descricao,
                                "u_status":status,
                                "u_data_da_atualizacao":data_historico,
                                "u_posted":True
                            }

                            data.append(entry_dic)
        #print(entry_dic)
        return data  



#Gera uma nova token de acesso ao ServiceNow com o uso da 'refresh_token'
#Tokens expiram a cada 1800 segundos (30 minutos), caso a função seja chamada multiplas vezes dentro desse periodo ela apenas retorna a mesma token ainda válida.
#https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0778194
def get_auth_token():
    url = url_servicenow+"/oauth_token.do"
    body = {
        "grant_type": "refresh_token",
        "client_id":servicenow_client_id,
        "client_secret":servicenow_client_secret,
        "refresh_token":service_now_refresh_token,
    }

    response = requests.post(url, data=body)
    data = response.json()
    #print(data)

    return data["access_token"]



#Verifica se o ticket (Gestão X) já está cadastrado no ServiceNow ou não
#Caso não esteja, quer dizer que o ticket foi proativamente aberto no Gestão X e deve ser cadastrado no ServiceNow para acompanhamento.
#Isso é feito no job GetProactiveTicket
def does_it_exist(code, params, token):
    try:
        found = False
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer "+token,
        }
        params["sysparm_query"] = "u_ticket_gestao_xLIKE"+code

        response = requests.get(url_servicenow+"api/now/table/u_integradora_gestao_x", headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if not 'result' in data or len(data['result']) == 0:
                found = False
            else:
                found = True
                
            return found
        
        else:
            response.raise_for_status()
        
    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET does_it_exist: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET does_it_exist: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET does_it_exist: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET does_it_exist: {err}")



#Verifica se o registro do histórico já foi inserido no ServiceNow
def has_it_been_updated(code, date, params, token):
    try:
        found = False
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer "+token,
        }
        params["sysparm_query"] = "u_ticket_gestao_x.u_ticket_gestao_xLIKE"+code+"^u_data_da_atualizacaoLIKE"+date #TODO adicionar status nessa verificação?

        response = requests.get(url_servicenow+"api/now/table/u_integradora_gestao_x_atualizacoes", headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if not 'result' in data or len(data['result']) == 0:
                found = False
            else:
                found = True
                
            return found
        
        else:
            response.raise_for_status()
        
    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET has_it_been_updated: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET has_it_been_updated: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET has_it_been_updated: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"A request exception occurred on GET has_it_been_updated: {err}")
    


#Insere as novas informações dos historicos dos chamados do Gestão X na tabela integradora de atualizações (u_integradora_gestao_x_atualizacoes)
#Ao criar os registros nessa tabela o Flow 'ELEA-LB: Gestão X - Escreve atualizações recebidas dos tickets' realiza a atualização da RITM.
def update_servicenow(updates, token):  
    try:
        if not updates:
            raise Exception("Updates array is empty")

        url = url_servicenow+"/api/now/table/u_integradora_gestao_x_atualizacoes"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }
        results = []
        
        response = requests.Response()
        for item in updates:
            try:
                if does_it_exist(item["u_ticket_gestao_x"], params_encoded_query, token):
                    if not has_it_been_updated(item['u_ticket_gestao_x'], item['u_data_da_atualizacao'], params_encoded_query, token):
                        response = requests.post(url, headers=headers, data=json.dumps(item))

                        results.append({
                            "item": item,
                            "response": response.__dict__,
                        })  

                    else:
                        print(f"Matching data is already stored on ServiceNow for {item['u_ticket_gestao_x']}")

                else:
                    print(f"Ticket {item['u_ticket_gestao_x']} does not have a corresponding RITM and will be treated as a proactive ticket")

            except requests.exceptions.HTTPError as err: # HTTP Error
                raise Exception(f"HTTP error occurred on POST update_servicenow: {err}")
            except requests.exceptions.ConnectionError as err: # Connection Error
                raise Exception(f"Connection error on POST update_servicenow: {err}")
            except requests.exceptions.Timeout as err: # Timeout
                raise Exception(f"Request timed out on POST update_servicenow: {err}")
            except requests.exceptions.RequestException as err: # Request Exception
                raise Exception(f"A request exception occurred on POST update_servicenow: {err}")  
        
        return results
                
    except Exception as err:
        raise Exception(err)
    
    

results = update_servicenow(process_historico(fetch_chamados_gestao_x(url_gestao_x, params_fetch_chamados_gestao_x)), get_auth_token())

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Update from {result['item']['u_data_da_atualizacao']} of Ticket {result['item']['u_ticket_gestao_x']} was sent to ServiceNow")
            else:
                print(f"Error while trying to update Ticket {result['item']['u_ticket_gestao_x']} with {result['item']['u_data_da_atualizacao']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")