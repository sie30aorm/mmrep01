import requests
# from requests_ntlm import HttpNtlmAuth
from requests.auth import HTTPBasicAuth

user="alvaro.paricio@MasMovilE1.onmicrosoft.com"
pswd="99.Sofia"
#Page:
#https://masmovile1.sharepoint.com/sites/Test2/control_financiero/Lists/ORG_DEPARTAMENTOS/AllItems.aspx
spo_site="https://masmovile1.sharepoint.com/sites/Test2/control_financiero"
spo_site="https://masmovile1.sharepoint.com/sites/Test2/control_financiero/_api/web/lists/ORG_DEPARTAMENTOS"
spo_site="https://masmovile1.sharepoint.com/sites/Test2/control_financiero/_api/web/lists/getbytitle('ORG_DEPARTAMENTOS')/items"

r = requests.get(spo_site, auth=HTTPBasicAuth(user, pswd))
print(r.status_code)
print(r.content)
