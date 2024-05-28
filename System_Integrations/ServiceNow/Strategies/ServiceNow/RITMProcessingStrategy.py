from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import post_to_servicenow_table
from System_Integrations.utils.gestao_x_api import post_gestao_x
from System_Integrations.utils.mapper import map_to_requests_response
from collections import defaultdict
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy
import traceback

class RITMProcessingStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for sending tickets from servicenow to gestaoX
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    _table = 'sc_req_item'

    tickets = []
    tickets_to_post = []
    results = []
    evidence_results = []

    def __init__(self, url_snow, url_gestao_x) -> None:
        self._url_snow = url_snow
        self._url_gestao_x = url_gestao_x
        # self._client_id = client_id
        # self._client_secret = client_secret
        # self._refresh_token = refresh_token

    def get_auth(self):
        super().get_auth()
        self._token = get_servicenow_auth_token(self._url_snow, self._servicenow_client_id, self._servicenow_client_secret, self._service_now_refresh_token)

    def fetch_list(self):
        params = {
                'sysparm_query': 'assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN3,4,7,9,10,11',
                'sysparm_fields':'number, sys_id, cat_item.name'
        }
        #breakpoint()
        self.tickets = get_servicenow_table_data(self._url_snow, self._table, params = params, token = self._token)
        #breakpoint()
        #return self.tickets

    def _descriptionBuilder(self, variables, descConfig):
        descricao = ""
        for config in descConfig:
            aValue = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == config["var"]]
                                                            #and config["extraValidator"](variable) if "extraValidator" in config else True]

            descricao += config["msg"] + aValue[0]["sc_item_option.value"] if aValue[0]["sc_item_option.value"] else ""
            
        return descricao
    
    def _get_multi_row_question_answer(self, ritm_sys_id, cat_item_name):
        params = {
            'sysparm_fields': "item_option_new.question_text, row_index, value"
        }

        cat_item_name = "Networks"

        match cat_item_name:
            case 'Networks':
                params['sysparm_query'] = "variable_set=f9f1f6371b689510bef1a79fe54bcb43^parent_id="+ritm_sys_id+"^parent_table_name=sc_req_item"
                params['sysparm_fields'] = "item_option_new.question_text, row_index, value"
                
                table = "sc_multi_row_question_answer"
                getMultiRowData = get_servicenow_table_data(self._url_snow, table, params = params, token = self._token)
            
                results = defaultdict(list)

                #data = getMultiRowData.json()['result']

                for item in getMultiRowData:
                    row_id = item["row_index"]
                    question = item["item_option_new.question_text"]
                    answer = item["value"]
                    results[row_id].append({"question":question,"answer":answer})

                # key_names = results.keys()
                # key_names_list = [key_names]#list(key_names)

                #breakpoint()
                key_names_list = list(results)

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

    def processing(self):
        try:
            for ritm in self.tickets:
                table_variables = "sc_item_option_mtom"
                params = {
                    "sysparm_query": "request_item.sys_id="+ritm['sys_id'],
                    "sysparm_fields": "sys_id, sc_item_option.item_option_new.question_text, sc_item_option.value, sc_item_option.order"
                }

                variables = get_servicenow_table_data(self._url_snow, table_variables, params = params, token = self._token)

                descricao = ""
                #Contact info is universal
                aQuestionContact = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == "Contact"]
                table_contacts = "sys_user"
                contactParams = {
                    "sysparm_query": "sys_id="+aQuestionContact[0]["sc_item_option.value"],
                    "sysparm_fields": "company.name, company.sys_id, first_name, last_name, email, phone, mobile_phone"
                }

                contactInfo = get_servicenow_table_data(self._url_snow, table_contacts, params = contactParams)

                valueContact = contactInfo[0]["first_name"]+" "+contactInfo[0]["last_name"]
                valueCompany = contactInfo[0]["company.name"]
                valueEmail = contactInfo[0]["email"]
                valuePhone = contactInfo[0]["phone"]
                valueMobilePhone = contactInfo[0]["mobile_phone"]
                valueCompanySysId = contactInfo[0]["company.sys_id"]

            descricao = '---TESTE INTEGRAÇÃO---\n'
            #breakpoint()
            login_solicitante, _ = super().get_login_solicitante(valueCompanySysId, descricao) #valueCompanySysId, descricao)
            
            if ritm['cat_item.name']:
                match ritm['cat_item.name']:
                    case 'Operational system':                               
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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

                    case 'Database':
                        descriptionConfig = [
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": "What is the Database Manager?", "msg": "\n\nGerenciador do banco (DBM): "},
                            {"var": "What is the server/hostname?", "msg": "\nNome do Host: "},
                            {"var": "What is the instance?", "msg": "\nNome da instancia: "},
                            {"var": "What is the service?", "msg": "\nTipo de Serviço: "}
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
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

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)

                    case 'Networks':
                        aQuestionWhatService = [variable for variable in variables if variable["sc_item_option.item_option_new.question_text"] == ' What is the service?']
                        valueWhatService = aQuestionWhatService[0]["sc_item_option.value"] if len(aQuestionWhatService) > 0 else None

                        descriptionConfig = [    
                            {"var": "Summary", "msg": "\n\nResumo:\n" },
                            {"var": "Description", "msg": "\n\nDescrição:\n" },
                            {"var": " What is the service?", "msg": "\n\nTipo de serviço: "},
                            {"var": " What network equipment?", "msg": "\nNome do equipamento: "} 
                        ]

                        descricao += f"\nRITM no ServiceNow Elea: {ritm['number']}"
                        descricao += f"\nCliente: {valueContact}"
                        descricao += f"\nEmpresa: {valueCompany}"
                        descricao += f"\nEmail: {valueEmail}"
                        descricao += f"\nTelefone 1: {valuePhone}"
                        descricao += f"\nTelefone 2: {valueMobilePhone}"
                        descricao += self._descriptionBuilder(variables, descriptionConfig)
                        
                        if valueWhatService == ' firewall_nat_rule_include':
                            descricao += self._get_multi_row_question_answer(ritm['sys_id'], ritm['cat_item.name'])
                        elif valueWhatService == ' firewall_nat_rule_delete':
                            descricao += self._get_multi_row_question_answer(ritm['sys_id'], ritm['cat_item.name'])                     
            
            # else:
            #     continue
        
            ticket_to_post =  {
                "ritm_number": ritm['number'],
                "data": {
                    "Descricao":descricao,
                    "LoginSolicitante": login_solicitante,
                    "Token": self.gestao_x_token,
                    "CatalogoServicosid":"2649" # especifico gestaoX
                }
            }
            
            self.tickets_to_post.append(ticket_to_post)
            
        except Exception as e:
            print(f"-!-!-!-!-!-!-!-ERROR START-!-!-!-!-!-!-!-\nError on {ritm['number']}:\n",traceback.format_exc(), "\n-!-!-!-!-!-!-!-ERROR END-!-!-!-!-!-!-!-")
            
            #return self.tickets

    def post(self):
        
        url = self._url_gestao_x + 'api/chamado/AbrirChamado'
        headers = {
            "Content-Type": "application/json",
        }

        for ticket in self.tickets_to_post:
            data = ticket['data']
            result = post_gestao_x(url, headers, data)

            self.results.append({**result, "item": ticket})

    def show_results(self): 
        for ticket in self.results:
            print("--------------------------------")
            if ticket["error"]:
                #TODO
                continue
            response = map_to_requests_response(ticket['response'])
            if response.status_code == 200 or response.status_code == 201:
                print(f"RITM {ticket['item']['ritm_number']} was posted as {response.json()} in Gestão X")
            else:
                print(f"Error while trying to post RITM {ticket['item']['ritm_number']} with {ticket['item']['data']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")

    def post_evidence(self):
        table = "u_integradora_gestao_x"

        params = {"sysparm_input_display_value":"true"}
        for result in self.results:
            data = {
                "u_ticket_gestao_x":map_to_requests_response(result['response']).json(),
                "u_requested_item":result['item']['ritm_number']
            }
            
            evidence_result = post_to_servicenow_table(self._url_snow, table, data, self._token, params = params)

            self.evidence_results.append({**evidence_result, "data": data}) #, "item": result["item"]

    def show_evidence_results(self): 
        for result in self.evidence_results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            #breakpoint()
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {result['data']['u_requested_item']} integrated with Gestão X ticket {result['data']['u_ticket_gestao_x']} ")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {result['data']['u_requested_item']} with Gestão X ticket {result['data']['u_ticket_gestao_x']}")
                print(f"Code: {response.status_code}")
                print(f"Message: {response.reason}")
