"""
auth.py — CDSE OAuth2 with single shared token
One token for all threads — refreshed only when expired
"""
import os, time, threading, requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

_session   = None
_token_exp = 0
_lock      = threading.Lock()

def get_session():
    global _session, _token_exp

    with _lock:
        now = time.time()
        # Only refresh if no session or token expires in <60s
        if _session is None or now > _token_exp - 60:
            client_id     = os.environ['CDSE_CLIENT_ID']
            client_secret = os.environ['CDSE_CLIENT_SECRET']
            client        = BackendApplicationClient(client_id=client_id)
            session       = OAuth2Session(client=client)
            token         = session.fetch_token(
                token_url=TOKEN_URL,
                client_secret=client_secret,
                include_client_id=True
            )
            _session   = session
            _token_exp = now + token.get('expires_in', 1800)
            print(f"Token refreshed ✅ expires in {token.get('expires_in',1800)//60} min")

        return _session
