import os
import sys
import json

# --- TRUCO DE AUTO-INSTALACIÓN NIVEL DIOS ---
# Reemplazamos cloudscraper por curl_cffi (Curl Impersonate)
# Esta librería imita la huella criptográfica exacta de Google Chrome real
try:
    from curl_cffi import requests as c_requests
except ImportError:
    import subprocess
    print("Instalando 'curl_cffi' para evadir la máxima seguridad de Cloudflare...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "curl_cffi"])
    from curl_cffi import requests as c_requests

# 1. Obtener credenciales de las variables de entorno de GitHub
EMAIL = os.environ.get("MYFXBOOK_EMAIL")
PASSWORD = os.environ.get("MYFXBOOK_PASSWORD")

if not EMAIL or not PASSWORD:
    print("Error: Faltan credenciales. Asegúrate de configurar MYFXBOOK_EMAIL y MYFXBOOK_PASSWORD en los Secrets de GitHub.")
    sys.exit(1)

# 2. Login en la API de Myfxbook
print("Iniciando sesión en Myfxbook con simulación criptográfica de Chrome...")
login_url = "https://www.myfxbook.com/api/login.json"
login_params = {
    'email': EMAIL,
    'password': PASSWORD
}

try:
    # impersonate="chrome110" copia el motor interno exacto de Google Chrome
    response = c_requests.get(login_url, params=login_params, impersonate="chrome110")
    response.raise_for_status() 
    login_response = response.json()
except Exception as e:
    print(f"Error de conexión con Myfxbook: {e}")
    if 'response' in locals():
        print(f"Detalle del bloqueo del servidor:\n{response.text[:500]}")
    sys.exit(1)

if login_response.get("error"):
    print(f"Error de Login: {login_response.get('message')}")
    sys.exit(1)

session_id = login_response.get("session")
print("Sesión iniciada correctamente.")

# 3. Obtener el ID de la cuenta de trading
print("Obteniendo cuentas de trading...")
accounts_url = "https://www.myfxbook.com/api/get-my-accounts.json"
accounts_response = c_requests.get(accounts_url, params={'session': session_id}, impersonate="chrome110").json()

if accounts_response.get("error") or not accounts_response.get("accounts"):
    print("Error: No se encontraron cuentas asociadas a este perfil.")
    sys.exit(1)

# Seleccionamos la primera cuenta de la lista
account_id = accounts_response["accounts"][0]["id"]
print(f"Cuenta seleccionada ID: {account_id}")

# 4. Obtener el historial de la cuenta
print("Descargando historial de operaciones...")
history_url = "https://www.myfxbook.com/api/get-history.json"
history_params = {
    'session': session_id,
    'id': account_id
}
history_response = c_requests.get(history_url, params=history_params, impersonate="chrome110").json()

if history_response.get("error"):
    print(f"Error al obtener historial: {history_response.get('message')}")
    sys.exit(1)

trades = history_response.get("history", [])
print(f"Se encontraron {len(trades)} operaciones en Myfxbook.")

# 5. Formatear los datos para el Dashboard HTML
formatted_data = []

for trade in trades:
    # Ignoramos movimientos que no tengan símbolo
    symbol = trade.get("symbol", "").strip()
    if not symbol:
        continue

    # Extraemos valores financieros
    profit = float(trade.get("profit", 0))
    commission = float(trade.get("commission", 0))
    swap = float(trade.get("interest", 0)) 
    
    # Calculamos el Profit Neto
    net_profit = profit + commission + swap

    formatted_data.append({
        "Symbol": symbol,
        "EntryTime": trade.get("openTime"), # Ej: "2023-10-15 14:30:00"
        "Time": trade.get("closeTime"),     # Fecha de Cierre
        "NetProfit": net_profit
    })

# 6. Guardar los datos en el archivo JSON
print("Guardando datos_trading.json...")
with open("datos_trading.json", "w", encoding="utf-8") as f:
    json.dump(formatted_data, f, indent=4)

print("¡Actualización completada con éxito!")
