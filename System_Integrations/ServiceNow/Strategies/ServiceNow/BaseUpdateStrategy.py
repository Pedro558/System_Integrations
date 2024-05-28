from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import post_to_servicenow_table
from System_Integrations.utils.gestao_x_api import post_gestao_x
from System_Integrations.utils.gestao_x_api import get_gestao_x
from System_Integrations.auth.api_secrets import get_api_token
from System_Integrations.utils.mapper import map_to_requests_response
from .BaseTicketProcessingStrategy import BaseTicketProcessingStrategy
from .ISnowTicketProcessingStrategy import ISnowTicketProcessingStrategy


class BaseUpdateStrategy(BaseTicketProcessingStrategy, ISnowTicketProcessingStrategy):
    """
        Strategy for updating snow tickets with information from Gestão X.
        Posting records with this script triggers Servicenow Flow ELEA-LB: Gestão X - Escreve atualizações recebidas dos tickets
    """
    _url_snow = None
    _url_gestao_x = None
    _client_id = None
    _client_secret = None
    _refresh_token = None
    _token = None
    
    gx_tickets = []
    gx_updates_to_post = []
    results = []

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
        url = self._url_gestao_x + 'api/chamado/Retorna_chamados_acompanhamento_solicitantes'
        params = {
            "Login": self.gestao_x_login,
            "Token": self.gestao_x_token,
            }

        self.gx_tickets = get_gestao_x(url, params = params)

        #return self.tickets

#Verifica se o ticket (Gestão X) já está cadastrado no ServiceNow ou não
#Caso não esteja, quer dizer que o ticket foi proativamente aberto no Gestão X e deve ser cadastrado no ServiceNow para acompanhamento.
#Isso é feito no job GetProactiveTicket
    def _does_it_exist(self, code):
        found = False

        params = {"sysparm_query": "u_ticket_gestao_xLIKE"+code}
        table = "u_integradora_gestao_x"

        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)
    
        if lookUp:
            found = True
        else:
            found = False
            
        return found
    
#Verifica se o registro do histórico já foi inserido no ServiceNow
    def _has_it_been_updated(self, code, date):
        found = False

        params = {"sysparm_query":"u_ticket_gestao_x.u_ticket_gestao_xLIKE"+code+"^u_data_da_atualizacaoLIKE"+date}
        table = "u_integradora_gestao_x_atualizacoes"
        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)

        if lookUp:
            found = True
        else:
            found = False
        return found

    def processing(self):
        url = self._url_gestao_x + 'api/chamado/RetornaHistoricoChamado'
        params = {
            "CodigoChamado":"",
            "Token":self.gestao_x_token,
            "InformacaoPublica":"true",
        }
        
        for ticket in self.gx_tickets:
            params["CodigoChamado"] = ticket.get('CODIGO')
            history_data = get_gestao_x(url, params = params)

            if not history_data:
                continue
        
            for entry in history_data:
                if "Atualização através do ServiceNow:" in entry.get('DESCRICAO'):
                    continue

                codigo = entry.get('CODIGO')
                descricao = entry.get('DESCRICAO')
                status = entry.get('STATUS_ID')
                data_historico = entry.get('DATA_HISTORICO')

                entry_dic = {
                    "exist": self._does_it_exist(codigo),
                    "updated": self._has_it_been_updated(codigo,data_historico),
                    "body":{
                        "u_ticket_gestao_x":codigo,
                        "u_descricao":descricao,
                        "u_status":status,
                        "u_data_da_atualizacao":data_historico,
                        "u_posted":True
                    }
                }

                self.gx_updates_to_post.append(entry_dic)                     

    def post(self):
        if not self.gx_updates_to_post:
            print("No updates were found")
            return
        
        table = "u_integradora_gestao_x_atualizacoes"

        for item in self.gx_updates_to_post:
            if not item["exist"]:
                self.results.append({
                    "error":True,
                    "errorMsg":f"Ticket {item["body"]['u_ticket_gestao_x']} does not have a corresponding RITM and will be treated as a proactive ticket"})
                continue
            if item["updated"]:
                self.results.append({
                    "error":True,
                    "errorMsg":f"Matching data is already stored on ServiceNow for {item["body"]['u_ticket_gestao_x']} update at {item["body"]["u_data_da_atualizacao"]}"})
                continue
            
            result = post_to_servicenow_table(self._url_snow, table, item["body"], self._token)
            
            self.results.append({**result, "item": item["body"]})

    def show_results(self): 
        for ticket in self.results:
            print("--------------------------------")
            if ticket["error"]:
                print(ticket["errorMsg"])
                continue
            response = map_to_requests_response(ticket["response"])
            if response.status_code == 200 or response.status_code == 201:
                print(f"Update from {ticket['item']['u_data_da_atualizacao']} of Ticket {ticket['item']['u_ticket_gestao_x']} was sent to ServiceNow")
            else:
                print(f"Error while trying to update Ticket {ticket['item']['u_ticket_gestao_x']} with {ticket['item']['u_data_da_atualizacao']} history data")
                print(f"{response.status_code}")
                print(f"{response.reason}")



#NÃO É UTILIZADO
    def post_evidence(self):
        pass

    def show_evidence_results(self): 
        pass