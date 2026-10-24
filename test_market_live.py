"""Quick test of market bars endpoint."""
import sys
sys.path.insert(0, 'apps/api/src')
sys.path.insert(0, 'services')
sys.path.insert(0, 'packages/contracts/src')
from goldmasters_api.app import create_app
from fastapi.testclient import TestClient

client = TestClient(create_app())
resp = client.get('/v1/market/bars?instrument_id=xauusd&timeframe=H1')
print('Status:', resp.status_code)
print('Body:', resp.json())