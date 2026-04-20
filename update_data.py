import os
import sys
import json
import time
import subprocess
from datetime import datetime

# --- AUTO-INSTALACIÓN ---
try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Instalando librerías necesarias en tu PC...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "python-dotenv"])
    import requests
    from dotenv import load_dotenv

# 1. Cargar credenciales del archivo local .env
load_dotenv()
EMAIL = os.getenv("MYFXBOOK_EMAIL")
PASSWORD = os.getenv("MYFXBOOK_PASSWORD")

if not EMAIL or not PASSWORD:
    print("Error: Faltan credenciales. Asegúrate de crear el archivo .env con MYFXBOOK_EMAIL y MYFXBOOK_PASSWORD.")
    sys.exit(1)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36'
}

# 2. Login en Myfxbook
print("Iniciando sesión en Myfxbook...")
login_url = "https://www.myfxbook.com/api/login.json"
login_params = {'email': EMAIL, 'password': PASSWORD}

try:
    response = requests.get(login_url, params=login_params, headers=headers)
    response.raise_for_status() 
    login_response = response.json()
except Exception as e:
    print(f"Error de conexión con Myfxbook: {e}")
    sys.exit(1)

if login_response.get("error"):
    print(f"Error de Login: {login_response.get('message')}")
    sys.exit(1)

session_id = login_response.get("session")
if not session_id:
    print("Error crítico: Myfxbook no arrojó error, pero no entregó un Session ID.")
    sys.exit(1)

print(f"¡Login exitoso! Sesión obtenida: {session_id[:5]}... (oculto por seguridad)")

# --- TRUCO 1: LA PAUSA ---
# Damos 3 segundos para que los servidores de Myfxbook registren la sesión internamente
print("Esperando 3 segundos para que Myfxbook valide la llave...")
time.sleep(3)

# 3. Obtener el ID de la cuenta
print("Obteniendo cuenta de trading...")

# --- TRUCO 2: INYECCIÓN DIRECTA DE URL ---
# Pegamos la sesión directo en el link para evitar que Python cambie los símbolos
accounts_url = f"https://www.myfxbook.com/api/get-my-accounts.json?session={session_id}"
accounts_response = requests.get(accounts_url, headers=headers).json()

# --- DETECTOR DE ERRORES ---
if accounts_response.get("error"):
    print(f"\n❌ Myfxbook denegó el acceso a las cuentas. Mensaje oficial: {accounts_response.get('message')}")
    sys.exit(1)

if not accounts_response.get("accounts") or len(accounts_response.get("accounts")) == 0:
    print("\n⚠️ Myfxbook no arrojó error, pero dice que tienes CERO cuentas vinculadas.")
    print("Verifica que tu cuenta de MetaTrader esté correctamente enlazada en la web de Myfxbook.")
    sys.exit(1)
# ----------------------------------

account_id = accounts_response["accounts"][0]["id"]
print(f"Cuenta detectada con éxito. ID: {account_id}")

# 4. Obtener historial
print("Descargando historial de operaciones...")
# Truco 2 aplicado al historial también
history_url = f"https://www.myfxbook.com/api/get-history.json?session={session_id}&id={account_id}"
history_response = requests.get(history_url, headers=headers).json()

if history_response.get("error"):
    print(f"Error al obtener historial: {history_response.get('message')}")
    sys.exit(1)

trades = history_response.get("history", [])
print(f"Se encontraron {len(trades)} operaciones.")

# 5. Formatear y guardar JSON
formatted_data = []
for trade in trades:
    symbol = trade.get("symbol", "").strip()
    if not symbol: continue
    net_profit = float(trade.get("profit", 0))
    formatted_data.append({
        "Symbol": symbol,
        "EntryTime": trade.get("openTime"),
        "Time": trade.get("closeTime"),
        "NetProfit": net_profit
    })

with open("datos_trading.json", "w", encoding="utf-8") as f:
    json.dump(formatted_data, f, indent=4)

# 6. --- SUBIDA A GITHUB AUTOMÁTICA ---
print("Iniciando subida automática a GitHub...")
try:
    # --- NUEVO: Configurar identidad de Git automáticamente ---
    subprocess.run(["git", "config", "--local", "user.email", "bot@trading.pc"], check=False)
    subprocess.run(["git", "config", "--local", "user.name", "Bot de Trading"], check=False)
    
    subprocess.run(["git", "add", "datos_trading.json"], check=True)
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    
    if "datos_trading.json" in status.stdout:
        fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subprocess.run(["git", "commit", "-m", f"Actualización automática PC: {fecha_hora}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"¡ÉXITO! Archivo subido a GitHub correctamente a las {fecha_hora}")
    else:
        print("No hay trades nuevos. No se subió nada para ahorrar recursos.")
except Exception as e:
    print(f"Error al subir a GitHub: {e}")