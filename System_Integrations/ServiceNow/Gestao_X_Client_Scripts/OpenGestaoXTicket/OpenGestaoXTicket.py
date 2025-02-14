import os 
from System_Integrations.ServiceNow.Strategies.ServiceNow.INCProcessingStrategy import INCProcessingStrategy
from System_Integrations.ServiceNow.Strategies.ServiceNow.RITMProcessingStrategy import RITMProcessingStrategy
from System_Integrations.ServiceNow.Strategies.ServiceNow.ServiceNowTicketProcessingContext import ServiceNowTicketProcessingContext
from commons.utils.env import only_run_in

#URL produção
url_gestao_x = "https://csc.everestdigital.com.br/API/"
url_servicenow_prd = "https://servicenow.eleadigital.com/"


def execute():
    type = os.getenv("RD_OPTION_TYPE")

    strat = None
    if type == "ritm":
        strat = RITMProcessingStrategy(
            url_snow=url_servicenow_prd,
            url_gestao_x=url_gestao_x,
        )    
    elif type == "inc":
        strat = INCProcessingStrategy(
            url_snow=url_servicenow_prd,
            url_gestao_x=url_gestao_x,
        )

    ticket_context = ServiceNowTicketProcessingContext(strat)
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

#PARA TESTES EM DEV
# inc_strat = INCProcessingStrategy(
#         url_snow=url_servicenow_prd,
#         url_gestao_x=url_gestao_x,
#     )

# ritm_strat = RITMProcessingStrategy(
#         url_snow=url_servicenow_prd,
#         url_gestao_x=url_gestao_x,
#     )


# ritm_context = ServiceNowTicketProcessingContext(ritm_strat)
# ritm_context.get_auth()
# ritm_context.fetch_list()
# ritm_context.processing()

# ritm_context.post()
# ritm_context.show_results()

# ritm_context.post_evidence()
# ritm_context.show_evidence_results()


# inc_context = ServiceNowTicketProcessingContext(inc_strat)
# inc_context.get_auth()
# inc_context.fetch_list()
# inc_context.processing()

# inc_context.post()
# inc_context.show_results()

# inc_context.post_evidence()
# inc_context.show_evidence_results()