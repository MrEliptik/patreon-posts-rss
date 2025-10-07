from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

# Save the credentials for later
with open('token.pkl', 'wb') as f:
    pickle.dump(creds, f)

# Saves in base64, then use cat token.b64 to get the value and store in github secrets
open('token.b64','w').write(base64.b64encode(open('token.pkl','rb').read()).decode())
