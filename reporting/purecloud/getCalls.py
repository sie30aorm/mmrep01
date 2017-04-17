import base64, requests, sys, logging, json
from requests.auth import HTTPBasicAuth

# Depending on geographical origins
# USA
PURECLOUD_PLATFORM="mypurecloud.com"
# EU
PURECLOUD_PLATFORM="mypurecloud.ie"

SERVICE_URI='https://api.{}/api/v2/analytics/reporting/metadata'.format( PURECLOUD_PLATFORM )

#logging.basicConfig(level=logging.DEBUG)

print('-----------------------------------------------')
print('- PureCloud Python Client Example -')
print('-----------------------------------------------')

clientId = '5b67c4a7-4547-4f9b-9fb0-9f01c35e5ef1'
clientSecret = 'O6zP_WQmEo66ngJNcfR5JTY2MgfQf6msPl9Het-Mzyw'

requestBody = {
	'grant_type': 'client_credentials'
}

# Get token
response = requests.post(
   'https://login.{}/oauth/token'.format(PURECLOUD_PLATFORM),
   data=requestBody,
   auth=HTTPBasicAuth(clientId, clientSecret)
   )

# Check response
if response.status_code == 200:
	print('Got token')
else:
	print('Failure: ' + str(response.status_code) + ' - ' + response.reason)
	sys.exit(response.status_code)

# Get JSON response body
responseJson = response.json()

# Prepare for GET /api/v2/authorization/roles request
requestHeaders = {
	'Authorization': responseJson['token_type'] + ' ' + responseJson['access_token']
}
#print( requestHeaders )

# Get roles
response = requests.get(SERVICE_URI, headers=requestHeaders)

# Check response
if response.status_code == 200:
	print('Got roles')
else:
	print('Failure: ' + str(response.status_code) + ' - ' + response.reason)
	sys.exit(response.status_code)

# Print Un-Formatted Response
responseJSON = response.json()
print( "\n============ JSON ==========================\n" +
  json.dumps( responseJSON, indent=2, sort_keys=True) )

# Print Formatted Response
print( "\n============ USERS =========================")
for entity in responseJSON['entities']:
	print('  ' + entity['name'])

print('\nDone')
