from System_Integrations.ServiceNow.Strategies.ServiceNow.GXTicketUpdateStrategy import GXTicketUpdateStrategy
from System_Integrations.ServiceNow.Strategies.ServiceNow.ServiceNowTicketProcessingContext import ServiceNowTicketProcessingContext
from commons.utils.env import only_run_in

#URL produção
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow_prd = "https://servicenow.eleadigital.com/"

def execute():
    ritm_strat = GXTicketUpdateStrategy(
        url_snow=url_servicenow_prd,
        url_gestao_x=url_gestao_x,
    )

    ticket_context = ServiceNowTicketProcessingContext(ritm_strat)
    ticket_context.get_auth()
    ticket_context.fetch_list()
    ticket_context.processing()

    ticket_context.post()
    ticket_context.show_results()

    ticket_context.post_evidence()
    ticket_context.show_evidence_results()

if __name__ == "__main__":
    only_run_in(["Prod"])
    execute()