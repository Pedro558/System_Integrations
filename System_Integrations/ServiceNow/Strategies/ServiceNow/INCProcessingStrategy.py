from System_Integrations.utils.servicenow_api import get_servicenow_table_data
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
    _fetch_params = {
        'sysparm_query': 'assignment_group=3ee6ef4c1bb8d510bef1a79fe54bcbb3^u_is_integrated=false^stateNOT IN6,7,8,9'
    }

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

    def processing(self):
        try:
            if not self.tickets:
                print("No new INC to process")
                return

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
                #breakpoint()
                valueContact = contactInfo[0]["first_name"]+" "+contactInfo[0]["last_name"]
                valueCompany = contactInfo[0]["company.name"]
                valueEmail = contactInfo[0]["email"]
                valuePhone = contactInfo[0]["phone"]
                valueMobilePhone = contactInfo[0]["mobile_phone"]
                valueCompanySysId = contactInfo[0]["company.sys_id"]

                #descricao = '---TESTE INTEGRAÇÃO---\n' #NECESSARIO EM DEV
                
                login_solicitante, _ = super().get_login_solicitante(valueCompanySysId, descricao) #valueCompanySysId, descricao)
                
                descricao += f"\nINC no ServiceNow Elea: {inc['number']}"
                descricao += f"\nCliente: {valueContact}"
                descricao += f"\nEmpresa: {valueCompany}"
                descricao += f"\nEmail: {valueEmail}"
                descricao += f"\nTelefone 1: {valuePhone}"
                descricao += f"\nTelefone 2: {valueMobilePhone}"
                descricao += f"\n\nResumo:\n {inc['short_description']}"
                descricao += f"\n\nDescrição:\n{inc['description']}"

                ticket_to_post =  {
                    "ticket_number": inc['number'],
                    "data": {
                        "Descricao":descricao,
                        "LoginSolicitante": login_solicitante,
                        "Token": self._gestao_x_token,
                        "CatalogoServicosid":"2650" # especifico gestaoX
                    }
                }
                    
                self.tickets_to_post.append(ticket_to_post)
            
        except Exception as e:
            print(f"-!-!-!-!-!-!-!-ERROR START-!-!-!-!-!-!-!-\nError on {inc['number']}:\n",traceback.format_exc(), "\n-!-!-!-!-!-!-!-ERROR END-!-!-!-!-!-!-!-")