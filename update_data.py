import requests
import json
import os

# Obtener credenciales de los Secretos de GitHub
EMAIL = os.getenv('MYFXBOOK_EMAIL')
PASSWORD = os.getenv('MYFXBOOK_PASSWORD')

# 1. Login para obtener el Session ID (Sustituye a la API Key)
login_url = f"https://api.myfxbook.com/api/login.json?email={EMAIL}&password={PASSWORD}"
session_data = requests.get(login_url).json()

if not session_data.get('error'):
    session_id = session_data['session']
    
    # 2. Obtener datos de la cuenta (Balance, Equity, etc.)
    acc_url = f"https://api.myfxbook.com/api/get-my-accounts.json?session={session_id}"
    data = requests.get(acc_url).json()

    # 3. Guardar en un archivo JSON para tu web
    with open('datos_trading.json', 'w') as f:
        json.dump(data, f, indent=4)
    print("Datos actualizados correctamente.")
else:
    print("Error en el login:", session_data.get('message'))
