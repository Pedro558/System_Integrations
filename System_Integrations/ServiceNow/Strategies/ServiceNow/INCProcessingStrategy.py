from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import post_to_servicenow_table
from System_Integrations.utils.gestao_x_api import post_gestao_x
from System_Integrations.utils.mapper import map_to_requests_response
from collections import defaultdict
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy
import traceback

class INCProcessingStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for sending tickets from servicenow to gestaoX
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    _table = 'incident'

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
                'sysparm_query': 'assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN6,7,8,9',
                #'sysparm_fields':'number, sys_id, cat_item.name'
        }
        self.tickets = get_servicenow_table_data(self._url_snow, self._table, params = params, token = self._token)
        #return self.tickets

    #TODO Avaliar se as variaveis ainda caem em "question_mtom"
    def _descriptionBuilder(self, variables, descConfig):
        descricao = ""
        for config in descConfig:
            aValue = [variable for variable in variables if variable["question.question_text"] == config["var"]]
                                                            #and config["extraValidator"](variable) if "extraValidator" in config else True]

            descricao += config["msg"] + aValue[0]["value"] if aValue[0]["value"] else ""
            
        return descricao
    
    #TODO Avaliar se as variaveis ainda caem em "question_mtom"
    #TODO Avaliar se essa estrutura é a mesma utilizada para as demais variaveis multilinha
    def _get_multi_row_question_answer(self, case_sys_id, cat_item_name):
        params = {
            'sysparm_query':'',
            'sysparm_fields': 'item_option_new.question_text, row_index, value'
        }

        match cat_item_name:
            case 'Cabling':
                params['sysparm_query'] = "variable_set=8719ef5f1bb0d910bef1a79fe54bcb38^parent_id="+case_sys_id+"^parent_table_name=sn_customerservice_case"
                params['sysparm_fields'] = "item_option_new.question_text, row_index, value"
                params['sysparm_display_value'] = "true"
                
                table = "sc_multi_row_question_answer"
                getMultiRowData = get_servicenow_table_data(self._url_snow, table, params = params, token = self._token)
            
                results = defaultdict(list)

                for item in getMultiRowData:
                    row_id = item["row_index"]
                    question = item["item_option_new.question_text"]
                    answer = item["value"]
                    results[row_id].append({"question":question,"answer":answer})

                key_names_list = list(results)

                description = ""

                counter = 0
                for key in key_names_list:
                    counter = counter+1
                    aQuestionDataHall = [item for item in results[key] if item['question'] == "What is the Data Hall?"]
                    valueDataHall = aQuestionDataHall[0]['answer']
                    aQuestionRack = [item for item in results[key] if item['question'] == "What is the Rack?"]
                    valueRack = aQuestionRack[0]['answer']
                    aQuestionAccount = [item for item in results[key] if item['question'] == "Account"]
                    valueAccount = aQuestionAccount[0]['answer']
                    aQuestionSite = [item for item in results[key] if item['question'] == "Site"]
                    valueSite = aQuestionSite[0]['answer']

                    description += f"\n\n---Informe {counter}---\n"\
                                f"Datahall: {valueDataHall if valueDataHall else ''}\n"\
                                f"Rack: {valueRack if valueRack else ''}\n"\
                                f"Conta: {valueAccount if valueAccount else ''}\n"\
                                f"Site: {valueSite if valueSite else ''}"

        #breakpoint()
        return description

    def processing(self):
        try:
            for inc in self.tickets:
                descricao = ""
                
                #GET CONTACT
                table_contacts = "sys_user"
                
                contactParams = {
                    "sysparm_query": "sys_id="+inc["caller_id"]["value"],
                    "sysparm_fields": "company.name, company.sys_id, first_name, last_name, email, phone, mobile_phone"
                }

                contactInfo = get_servicenow_table_data(self._url_snow, table_contacts, params = contactParams, token = self._token)
                #END GET CONTACT

                valueContact = contactInfo[0]["first_name"]+" "+contactInfo[0]["last_name"]
                valueCompany = contactInfo[0]["company.name"]
                valueEmail = contactInfo[0]["email"]
                valuePhone = contactInfo[0]["phone"]
                valueMobilePhone = contactInfo[0]["mobile_phone"]
                valueCompanySysId = contactInfo[0]["company.sys_id"]

                descricao = '---TESTE INTEGRAÇÃO---\n'
                login_solicitante, _ = super().get_login_solicitante(valueCompanySysId, descricao) #valueCompanySysId, descricao)
                descricao += f"\nINC no ServiceNow Elea: Número INC"#{inc['number']}"
                descricao += f"\nCliente: Nome Cliente"#{valueContact}"
                descricao += f"\nEmpresa: Nome Empresa"#{valueCompany}"
                descricao += f"\nEmail: Email@email"#{valueEmail}"
                descricao += f"\nTelefone 1: Telefone"#{valuePhone}"
                descricao += f"\nTelefone 2: Celular"#{valueMobilePhone}"
                descricao += f"\n\nResumo:\n Resumo Teste"#{inc['short_description']}"
                descricao += f"\n\nDescrição:\nDescrição Teste"#{inc['description']}"

                print(descricao)
                ticket_to_post =  {
                    "inc_number": inc['number'],
                    "data": {
                        "Descricao":descricao,
                        "LoginSolicitante": login_solicitante,
                        "Token": self.gestao_x_token,
                        "CatalogoServicosid":"2650" # especifico gestaoX
                    }
                }
                    
                self.tickets_to_post.append(ticket_to_post)
            
        except Exception as e:
            print(f"-!-!-!-!-!-!-!-ERROR START-!-!-!-!-!-!-!-\nError on {inc['number']}:\n",traceback.format_exc(), "\n-!-!-!-!-!-!-!-ERROR END-!-!-!-!-!-!-!-")

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
                print(f"RITM {ticket['item']['inc_number']} was posted as {response.json()} in Gestão X")
            else:
                print(f"Error while trying to post RITM {ticket['item']['inc_number']} with {ticket['item']['data']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")

    def post_evidence(self):
        table = "u_integradora_gestao_x"

        params = {"sysparm_input_display_value":"true"}
        for result in self.results:
            data = {
                "u_ticket_gestao_x":map_to_requests_response(result['response']).json(),
                "u_requested_item":result['item']['inc_number']
            }
            
            evidence_result = post_to_servicenow_table(self._url_snow, table, data, self._token, params = params)

            self.evidence_results.append({**evidence_result, "data": data}) #, "item": result["item"]

    def show_evidence_results(self): 
        for result in self.evidence_results:
            print("--------------------------------")
            response = map_to_requests_response(result["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Record created in u_integradora_gestao_x for {result['data']['u_requested_item']} integrated with Gestão X ticket {result['data']['u_ticket_gestao_x']} ")
            else:
                print(f"Error while trying to update u_integradora_gestao_x for {result['data']['u_requested_item']} with Gestão X ticket {result['data']['u_ticket_gestao_x']}")
                print(f"Code: {response.status_code}")
                print(f"Message: {response.reason}")
