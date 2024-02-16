import requests
import json
from ...auth.api_secrets import get_api_token
from ...utils.mapper import map_to_requests_response
from collections import defaultdict
#Incluir caso for substituir o metodo da primeira linha do Fetch_ritm_variables
#from ...utils.parser import get_value



#URLs
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow_dev = "https://eleadev.service-now.com/"

#Tokens
gestao_x_login = get_api_token('gestao-x-prd-login')
gestao_x_token = get_api_token('gestao-x-prd-api-token')

gestao_x_login_arauco = get_api_token("gestao-x-prd-login-arauco")
gestao_x_login_dimed = get_api_token("gestao-x-prd-login-dimed")
gestao_x_login_fatl = get_api_token("gestao-x-prd-login-fatl")
gestao_x_login_unimed = get_api_token("gestao-x-prd-login-unimed")

servicenow_client_id = get_api_token('servicenow-dev-client-id-oauth')
servicenow_client_secret = get_api_token('servicenow-dev-client-secret-oauth')
service_now_refresh_token = get_api_token('servicenow-dev-refresh-token-oauth')


#Variavel de parametros para GET na API do ServiceNow
#Recebe uma Encoded Query no formato do ServiceNow de acordo com a necessidade dentro das funções onde é necessário
serviceNow_params = {
    "sysparm_query": "",
    "sysparm_fields": ""
}

#Gera uma nova token de acesso ao ServiceNow com o uso da 'refresh_token'
#Tokens expiram a cada 1800 segundos (30 minutos), caso a função seja chamada multiplas vezes dentro desse periodo ela apenas retorna a mesma token ainda válida.
#https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0778194
def get_auth_token():
    url = url_servicenow_dev+"/oauth_token.do"
    body = {
        "grant_type": "refresh_token",
        "client_id":servicenow_client_id,
        "client_secret":servicenow_client_secret,
        "refresh_token":service_now_refresh_token,
    }

    response = requests.post(url, data=body)
    data = response.json()

    return data["access_token"]



#Busca RITMs no ServiceNow onde "Assignment Group" é Gr.Suporte N3, "Is Integrated" é false E o estado não é final
def fetch_ritm_servicenow(url, params, token):    
                                               #3ee6ef4c1bb8d510bef1a79fe54bcbb3 <- Sys_ID PRODUÇÃO É O MESMO DE DEV
    params["sysparm_query"] = "assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN3,4,7,9,10,11"
    params["sysparm_fields"] = "number, sys_id, cat_item.name"

    headers = {
            "Content-Type": "application/json",
            "Accept":"application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        response = requests.get(url+"api/now/table/sc_req_item", headers=headers, params=params)
        
        ritm_list = response.json()

        if not 'result' in ritm_list or len(ritm_list['result']) == 0:
            raise Exception("No RITMs found")

        if response.status_code == 200:        
            return ritm_list['result']
        
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_ritm_servicenow: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on GET fetch_ritm_servicenow: {err}")



#Busca as variaveis da RITM aberta através de um catalog item/record producer.
def fetch_ritm_variables (url, ritm, params, token):
    params["sysparm_query"] = "request_item.sys_id="+ritm['sys_id']   #get_value(ritm, lambda x : x['results']['sys_is'], None)
    params["sysparm_fields"] = "sys_id, sc_item_option.item_option_new.question_text, sc_item_option.value, sc_item_option.order"
    
    headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        response = requests.get(url+"api/now/table/sc_item_option_mtom", headers=headers, params=params)
        if response.status_code == 200:
            variable_list = response.json()
            
            if not 'result' in variable_list or len(variable_list['result']) == 0:
                raise Exception(f"No variables found for {ritm['number']}")
            
            return variable_list['result']
        
        else:
            response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on GET fetch_ritm_variables: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on GET fetch_ritm_variables: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on GET fetch_ritm_variables: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on GET fetch_ritm_variables: {err}")



#Dinamicamente constroi a descrição que será enviada ao Gestão X com base no que foi preenchido no formulario
def descriptionBuilder(variables, descConfig):
    descricao = ""
    for config in descConfig:
        aValue = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == config["var"]]
                                                        #and config["extraValidator"](variable) if "extraValidator" in config else True]

        descricao += config["msg"] + aValue[0]["sc_item_option.value"] if aValue[0]["sc_item_option.value"] else ""
        
    return descricao


#Quando alguma variavel faz uso de tabela multilinha (sc_multi_row_question_answer) essa função é chamada para buscar todos os valores e criar o texto da descrição
def get_multi_row_question_answer(ritm_sys_id, cat_item_name):
    params = serviceNow_params
    params['sysparm_fields'] = "item_option_new.question_text, row_index, value"

    headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer "+get_auth_token(),
            }
    cat_item_name = "Networks"

    match cat_item_name:
        case 'Networks':
            params['sysparm_query'] = "variable_set=f9f1f6371b689510bef1a79fe54bcb43^parent_id="+ritm_sys_id+"^parent_table_name=sc_req_item"
            params['sysparm_fields'] = "item_option_new.question_text, row_index, value"
            
            getMultiRowData = requests.get(url_servicenow_dev+"api/now/table/sc_multi_row_question_answer", params = params, headers=headers)
            if getMultiRowData.status_code == 200:
                results = defaultdict(list)

                data = getMultiRowData.json()['result']

                for item in data:
                    row_id = item["row_index"]
                    question = item["item_option_new.question_text"]
                    answer = item["value"]
                    results[row_id].append({"question":question,"answer":answer})

                key_names = results.keys()
                key_names_list = list(key_names)
                
                description = ""
                counter = 0

                for key in key_names_list:
                    counter = counter+1
                    aQuestionSourceIp = [item for item in results[key] if item['question'] == "Source IP(s) (hosts/Subnets) Ex: 10.36.1.1/255.255.255.0"]
                    valueSourceIp = aQuestionSourceIp[0]['answer']

                    aQuestionDestinationIp = [item for item in results[key] if item['question'] == "Destination IP(s) (hosts/subnets) Ex: 10.39.1.151/255.255.255.0"]
                    valueDestinationIp = aQuestionDestinationIp[0]['answer']

                    aQuestionProtocol = [item for item in results[key] if item['question'] == "Protocol Ex: TCP, UDP"]
                    valueProtocol = aQuestionProtocol[0]['answer']

                    aQuestionPort = [item for item in results[key] if item['question'] == "Port / Service Ex: 80 (http)"]
                    valuePort = aQuestionPort[0]['answer']

                    aQuestionNatSourceIp = [item for item in results[key] if item['question'] == "NAT - Source IP(s) (hosts/Subnets) Ex: 10.36.1.1"]
                    valueNatsourceIp = aQuestionNatSourceIp[0]['answer']

                    aQuestionNatDestinationIp = [item for item in results[key] if item['question'] == "NAT - Destination IP(s) (hosts/Subnets) Ex: 10.39.1.151/255.255.255.0"]
                    valueNatDestinationIp = aQuestionNatDestinationIp[0]['answer']
                    
                    aQuestionNatProtocol = [item for item in results[key] if item['question'] == "NAT - Protocol Ex: TCP, UDP"]
                    valueNatProtocol = aQuestionNatProtocol[0]['answer']

                    aQuestionNatPort = [item for item in results[key] if item['question'] == "NAT - Port / Service Ex: 80 (http)"]
                    valueNatPort = aQuestionNatPort[0]['answer']

                    description += f"\n\n---Regra {counter}---\n"\
                                f"IP de Origem: {valueSourceIp if valueSourceIp else ''}\n"\
                                f"IP de Destino: {valueDestinationIp if valueDestinationIp else ''}\n"\
                                f"Protocolo: {valueProtocol if valueProtocol else ''}\n"\
                                f"Porta: {valuePort if valuePort else ''}\n"\
                                f"NAT - IP de Origem: {valueNatsourceIp if valueNatsourceIp else ''}\n"\
                                f"NAT - IP de Destino{valueNatDestinationIp if valueSourceIp else ''}\n"\
                                f"NAT - Protocolo: {valueNatProtocol if valueNatProtocol else ''}\n"\
                                f"NAT - Porta: {valueNatPort if valueNatPort else ''}"
                    
    return description



#Constroi a descrição com base nas variaveis e tipo de item de catalogo
def process_data(url, ritm_list):
    tickets_to_post = []
    if not ritm_list:
        return #TODO tratar
    
    for ritm in ritm_list:
        variables = fetch_ritm_variables(url, ritm, serviceNow_params, get_auth_token())

        #Contact info is universal
        aQuestionContact = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "Contact"]
                    
        contactParams = {
            "sysparm_query": "sys_id="+aQuestionContact[0]["sc_item_option.value"],
            "sysparm_fields": "company.name, company.sys_id, first_name, last_name, email, phone, mobile_phone"
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+get_auth_token(),
        }
        
        getContactInfo = requests.get(url_servicenow_dev+"api/now/table/sys_user", params = contactParams, headers=headers)
        if getContactInfo.status_code == 200:
            contactInfo = getContactInfo.json()["result"]
            valueContact = contactInfo[0]["first_name"]+" "+contactInfo[0]["last_name"]
            valueCompany = contactInfo[0]["company.name"]
            valueEmail = contactInfo[0]["email"]
            valuePhone = contactInfo[0]["phone"]
            valueMobilePhone = contactInfo[0]["mobile_phone"]

        else:
            response.raise_for_status()

        descricao = ""
        if ritm['cat_item.name']:
            match ritm['cat_item.name']:
                case 'Operational system':           
                    # COLINHA:
                    # aQuestionHostname = list(filter(
                    #                             lambda variable: variable['question'] == 'hostname'
                    #                             , variables
                    #                             ))

                    # OU

                    # aQuestionHostname = [variable for variable in variables if variable["question"] == 'hostname']
                    
                    # ENTÃO

                    # questionHortname = aQuestionHostname[0]["value"]

                    #valueSummary = [variable["sc_item_option.value"] for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'Summary'][0]
                    #Essa alternativa retorna um array contendo somente o value e então entrega para a variavel a primeira posição (0) do array que é a string contendo o valor
                    #                    return   for each ele in array     if ele['key'] == 'value' 
                    #aQuestionSummary = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'Summary']
                    
                    #  Operating System
                    aQuestionWhatOperatingSystem = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What Operating System?"]
                    valueWhatOperatingSystem = aQuestionWhatOperatingSystem[0]["sc_item_option.value"]
                    #  Unix Service
                    aQuestionWhatServiceWindows = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the service?" and variable["sc_item_option.order"] == "5"]
                    valueWhatServiceWindows = aQuestionWhatServiceWindows[0]["sc_item_option.value"]
                    #  Windows Services
                    aQuestionWhatServiceUnix = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the service?" and variable["sc_item_option.order"] == "6"]
                    valueWhatServiceUnix = aQuestionWhatServiceUnix[0]["sc_item_option.value"]
                    #  Reboot Time Start                
                    aQuestionRebootTimeStart = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == " What is the Server Reboot Time (Start)"] #sim, tem um espaço no nome da variavel
                    valueRebootTimeStart = aQuestionRebootTimeStart[0]["sc_item_option.value"] if len(aQuestionRebootTimeStart) > 0 else None
                    #  Reboot Time End
                    aQuestionRebootTimeEnd = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "What is the Server Reboot Time (end)"]
                    valueRebootTimeEnd = aQuestionRebootTimeEnd[0]["sc_item_option.value"] if len(aQuestionRebootTimeEnd) > 0 else None


                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What Operating System?", "msg": "\n\nSistema Operacional: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)
                    if valueWhatOperatingSystem == 'windows':
                        descricao += f"\nTipo de serviço: {valueWhatServiceWindows}"
                    elif valueWhatOperatingSystem == 'unix':
                        descricao += f"\nTipo de serviço: {valueWhatServiceUnix}"
                    if valueRebootTimeStart:
                        descricao += f"\nHora do inicio do reboot: {valueRebootTimeStart}"
                    if valueRebootTimeEnd:
                        descricao += f"\n Hora do fim do reboot: {valueRebootTimeEnd}"

                case 'Backup':
                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What type of service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)

                case 'Database':
                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What is the Database Manager?", "msg": "\n\nGerenciador do banco (DBM): "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "},
                        {"var": "What is the instance?", "msg": "\nNome da instancia: "},
                        {"var": "What is the service?", "msg": "\nTipo de Serviço: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)

                case 'Monitoring':
                    #  Blackout Window Start
                    aQuestionBlackoutWindowStart = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (start)']
                    valueBlackoutWindowStart = aQuestionBlackoutWindowStart[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowStart) > 0 else None
                    #  Blackout Window End
                    aQuestionBlackoutWindowEnd = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == 'What is the blackout window (End)']
                    valueBlackoutWindowEnd = aQuestionBlackoutWindowEnd[0]["sc_item_option.value"] if len(aQuestionBlackoutWindowEnd) > 0 else None

                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": "What is the service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)
                    if valueBlackoutWindowStart:
                        descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowStart}"
                    if valueBlackoutWindowEnd:
                        descricao += f"\nInicio da janela do blackout: {valueBlackoutWindowEnd}"

                case 'Storage':
                    descriptionConfig = [
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": " What is the service?", "msg": "\n\nTipo de serviço: "},
                        {"var": "What is the server/hostname?", "msg": "\nNome do Host: "}
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)

                case 'Networks':
                    descriptionConfig = [    
                        {"var": "Summary", "msg": "\n\nResumo:\n" },
                        {"var": "Description", "msg": "\n\nDescrição:\n" },
                        {"var": " What is the service?", "msg": "\n\nTipo de serviço: "},
                        {"var": " What network equipment?", "msg": "\nNome do equipamento: "} 
                    ]

                    descricao += "---TESTE INTEGRACAO---"
                    descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                    descricao += f"\nCliente: {valueContact}"
                    descricao += f"\nEmpresa: {valueCompany}"
                    descricao += f"\nEmail: {valueEmail}"
                    descricao += f"\nTelefone 1: {valuePhone}"
                    descricao += f"\nTelefone 2: {valueMobilePhone}"
                    descricao += descriptionBuilder(variables, descriptionConfig)
                    descricao += get_multi_row_question_answer(ritm['sys_id'], ritm['cat_item.name'])

        else:
            continue
        
        login_solicitante = ""
        #ARAUCO
        if getContactInfo.json()["result"][0]["company.sys_id"] == "cc7f7f951bfcd110bef1a79fe54bcbb2":
            login_solicitante = gestao_x_login_arauco
            print(login_solicitante)

        #DIMED
        if getContactInfo.json()["result"][0]["company.sys_id"] == "2c7fbf951bfcd110bef1a79fe54bcb07":
            login_solicitante = gestao_x_login_dimed
            print(login_solicitante)
        #FATL                                                       b47fbf951bfcd110bef1a79fe54bcb79
        if getContactInfo.json()["result"][0]["company.sys_id"] == "b47fbf951bfcd110bef1a79fe54bcb79":
            login_solicitante = gestao_x_login_fatl
            print(login_solicitante)   
        #UNIMED
        if getContactInfo.json()["result"][0]["company.sys_id"] == "6d7fff951bfcd110bef1a79fe54bcb12":
            login_solicitante = gestao_x_login_unimed
            print(login_solicitante)
        else:
            login_solicitante = gestao_x_login
            print(login_solicitante)
            descricao = "Solicitação feita por cliente não pré cadastrado na integração.\nFavor entrar em contato com o Service Desk para avaliar.\nCaso necessário comunique a equipe de integração.\n\n"+descricao

        ticket_to_post =  {
            "ritm_number": ritm['number'],
            "data": {
                "Descricao":descricao,
                "LoginSolicitante":login_solicitante, #gestao_x_login,
                "Token":gestao_x_token,
                "CatalogoServicosid":"2650"
            }
        }
        

        tickets_to_post.append(ticket_to_post)
                    

    return tickets_to_post



#Abre o ticket no gestão X
def openGestaoXTicket(url, tickets_to_post):
    url += 'api/chamado/AbrirChamado'
    headers = {
            "Content-Type": "application/json",
    }
    try:
        results =[]
        for ticket in tickets_to_post:
            response = requests.post(url, headers=headers, data=json.dumps(ticket['data']))
            if response.status_code == 200 or response.status_code == 201:
                results.append({
                    "item": ticket,
                    "response": response.__dict__,
                })  
                
            else:
                response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST openGestaoXTicket: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST openGestaoXTicket: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST openGestaoXTicket: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on POST openGestaoXTicket: {err}")


    return results



#Cria registro na tabela integradora
def postServiceNowIntegradora(url, token, tickets_posted):
    url += 'api/now/table/u_integradora_gestao_x?sysparm_input_display_value=true'
    headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer "+token,
        }
    
    try:
        results =[]
        for ticket in tickets_posted:
            data = {
                "u_ticket_gestao_x":map_to_requests_response(ticket['response']).json(),
                "u_requested_item":ticket['item']['ritm_number']
            }
            response = requests.post(url, headers=headers, data=json.dumps(data))
    
            if response.status_code == 200 or response.status_code == 201:
                results.append({
                    "item": ticket['item'],
                    "response": response.__dict__,
                })  
            else:
                response.raise_for_status()

    except requests.exceptions.HTTPError as err: # HTTP Error
        raise Exception(f"HTTP error occurred on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.ConnectionError as err: # Connection Error
        raise Exception(f"Connection error on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.Timeout as err: # Timeout
        raise Exception(f"Request timed out on POST postServiceNowIntegradora: {err}")
    except requests.exceptions.RequestException as err: # Request Exception
        raise Exception(f"An error occurred on POST postServiceNowIntegradora: {err}")

    return results



ritms = fetch_ritm_servicenow(url_servicenow_dev, serviceNow_params, get_auth_token())
tickets_to_post = process_data(url_servicenow_dev, ritms)
tickets_posted = openGestaoXTicket(url_gestao_x, tickets_to_post)
results = postServiceNowIntegradora(url_servicenow_dev, get_auth_token(), tickets_posted)

for ticket in tickets_posted:
            print("--------------------------------")
            response = map_to_requests_response(ticket["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"RITM {ticket['item']['ritm_number']} was posted as {map_to_requests_response(ticket['response']).json()} in Gestão X")
            else:
                print(f"Error while trying to post RITM {ticket['item']['ritm_number']} with {ticket['item']['data']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")

for result in results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {result['item']['ritm_number']} integrated with Gestão X ticket {map_to_requests_response(ticket['response']).json()} ")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {result['item']['u_requested_item']} with Gestão X ticket {map_to_requests_response(ticket['response']).json()}")
                print(f"{response.status_code}")
                print(f"{response.reason}")