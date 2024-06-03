from cgitb import lookup
from System_Integrations.utils.servicenow_api import get_servicenow_auth_token
from System_Integrations.utils.servicenow_api import get_servicenow_table_data
from System_Integrations.utils.servicenow_api import post_to_servicenow_table
from System_Integrations.utils.gestao_x_api import get_gestao_x
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

    def get_auth(self):
        super().get_auth()
        self._token = get_servicenow_auth_token(self._url_snow, self._servicenow_client_id, self._servicenow_client_secret, self._service_now_refresh_token)

    def fetch_list(self):
        url = self._url_gestao_x + 'api/chamado/Retorna_chamados_acompanhamento_solicitantes'
        params = {
            "Login": self._gestao_x_login,
            "Token": self._gestao_x_token,
            }

        self.gx_tickets = get_gestao_x(url, params = params)

#Verifica se o ticket (Gestão X) já está cadastrado no ServiceNow ou não
#Caso não esteja, quer dizer que o ticket foi proativamente aberto no Gestão X e deve ser cadastrado no ServiceNow para acompanhamento.
#Isso é feito no job GetProactiveTicket
    def _does_it_exist(self, code):
        found = False

        params = {"sysparm_query": "u_ticket_gestao_xLIKE"+code}
        table = "u_integradora_gestao_x"

        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)

        #snow_ticket = ""

        if lookUp:
            #snow_ticket = lookUp['u_requested_item']
            found = True
        else:
            found = False
            
        return found#, snow_ticket
    
#Verifica se o registro do histórico já foi inserido no ServiceNow
    def _has_it_been_updated(self, code, date):
        found = False

        table = "u_integradora_gestao_x_atualizacoes"
        params = {"sysparm_query":"u_ticket_gestao_x.u_ticket_gestao_xLIKE"+code+"^u_data_da_atualizacaoLIKE"+date}#+"^u_mudou_o_tipo!=false"}
        lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)

        if lookUp:
            found = True
        else:
            found = False
        
        return found, lookUp
    
    # def _get_updates_from_ticket(self, code):
    #     table = "u_integradora_gestao_x_atualizacoes"
    #     params = {"sysparm_query":"u_ticket_gestao_x.u_ticket_gestao_xLIKE"+code+"^u_mudou_o_tipo!=false"}

    #     lookUp = get_servicenow_table_data(self._url_snow, table, params=params, token = self._token)
        
    #     return lookUp
        

    def processing(self):
        url = self._url_gestao_x + 'api/chamado/RetornaHistoricoChamado'
        params = {
            "CodigoChamado":"",
            "Token":self._gestao_x_token,
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
                #tipo = entry.get('EMX_TIPO_ITEM')
                descricao = entry.get('DESCRICAO')
                status = entry.get('STATUS_ID')
                data_historico = entry.get('DATA_HISTORICO')
                breakpoint()
                update_found, update_data = self._has_it_been_updated(codigo,data_historico)
                if update_found:
                    continue

                #found, snow_ticket_number = self._does_it_exist(codigo)

                if not self._does_it_exist(codigo):
                    continue

                #TODO ajusta esse essa validação

                # is_same_type = None
                
                # is_same_type = (
                #     tipo == "S" and snow_ticket_number.startwith("RITM")
                #     or
                #     tipo == "I" and snow_ticket_number.startwith("INC")
                # )
                
                # if not is_same_type:
                #     #pegar todos os registros da u_integradora_gestao_x_atualizacoes para o ticket que 'not is_same_type'
                #     snow_ticket = None

                #     old_updates_to_change = self._get_updates_from_ticket(codigo) 

                    #constroi o dict para fazer patch de todos os registros com "u_mudou_o_tipo": True, o dict que cancela o ticket (inc/req+ritm) e o dict que cancela o registro na tabela integradora
                    # for update in old_updates_to_change:
                    #     #update["u_mudou_o_tipo"] = True
                    #     entry_dic = {
                    #         "exist": found,
                    #         "is_same_type": is_same_type,
                    #         "body":{
                    #             "u_ticket_gestao_x":codigo,
                    #             "u_descricao":descricao,
                    #             "u_status":status,
                    #             "u_data_da_atualizacao":data_historico,
                    #             "u_posted": True,
                    #             "u_mudou_o_tipo": True
                    #         }
                    #     }
                    #     self.gx_updates_to_post.append(update)

                # else:
                breakpoint()

                entry_dic = {
                    #"exist": found,
                    #"is_same_type": is_same_type,
                    "body":{
                        "u_ticket_gestao_x":codigo,
                        "u_descricao":descricao,
                        "u_status":status,
                        "u_data_da_atualizacao":data_historico,
                        "u_posted": True,
                    }
                }
                
                self.gx_updates_to_post.append(entry_dic)                     

    def post(self):
        if not self.gx_updates_to_post:
            breakpoint()
            print("No updates were found")
            return
        
        table = "u_integradora_gestao_x_atualizacoes"

        #TODO Ajusta esse esse loop
        # for item in [x for x in self.gx_updates_to_post if not x["is_same_type"]]:
        #     pass
        
        for item in self.gx_updates_to_post:            
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