import os
import sys
import json
import subprocess
from datetime import datetime

try:
    import MetaTrader5 as mt5
except ImportError:
    print("Instalando MetaTrader5...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
    import MetaTrader5 as mt5

def main():
    print("========================================")
    print("   SISTEMA DE ACTUALIZACIÓN MT5 V3.5   ")
    print("========================================\n")

    print(">> Conectando con la terminal MT5...")
    if not mt5.initialize():
        print("❌ ERROR: No se pudo conectar a MT5. Verifica que la cuenta esté activa.")
        sys.exit(1)

    print(">> Extrayendo historial de deals...")
    fecha_inicio = datetime(2020, 1, 1)
    fecha_fin = datetime.now()
    deals = mt5.history_deals_get(fecha_inicio, fecha_fin)

    if not deals:
        print("⚠️ No hay operaciones en el historial.")
        mt5.shutdown()
        sys.exit(1)

    print(">> Reconstruyendo operaciones y consolidando costos (Swap/Comisión)...")
    positions = {}
    
    for d in deals:
        # Filtrar solo deals de trading (Tipo 0=Buy, 1=Sell). Ignorar depósitos (Tipo 2).
        if d.symbol == "" or d.type > 1:
            continue
            
        pid = d.position_id
        
        # Inicializar bolsa de datos para esta posición si es nueva
        if pid not in positions:
            positions[pid] = {
                "symbol": d.symbol,
                "entry_time": None,
                "exit_time": None,
                "accumulated_profit": 0.0,
                "accumulated_commission": 0.0,
                "accumulated_swap": 0.0
            }
        
        # ACUMULACIÓN INTEGRAL: Se suma cada centavo sin importar en qué deal ocurrió
        positions[pid]["accumulated_profit"] += float(d.profit)
        positions[pid]["accumulated_commission"] += float(d.commission)
        positions[pid]["accumulated_swap"] += float(d.swap)
        
        # Gestión de tiempos de entrada y salida
        if d.entry == 0: # Deal de Entrada
            if positions[pid]["entry_time"] is None or d.time < positions[pid]["entry_time"]:
                positions[pid]["entry_time"] = d.time
        elif d.entry == 1 or d.entry == 2: # Deal de Salida o Reversa
            if positions[pid]["exit_time"] is None or d.time > positions[pid]["exit_time"]:
                positions[pid]["exit_time"] = d.time

    formatted_data = []
    for pid, pos in positions.items():
        if pos["exit_time"] is not None:
            ent_ts = pos["entry_time"] if pos["entry_time"] is not None else pos["exit_time"]
            
            # CÁLCULO NETO FINAL: Profit Bruto + Comisiones + Swaps
            neto_total = pos["accumulated_profit"] + pos["accumulated_commission"] + pos["accumulated_swap"]
            
            formatted_data.append({
                "Symbol": pos["symbol"],
                "EntryTime": datetime.fromtimestamp(ent_ts).strftime("%Y-%m-%d %H:%M:%S"),
                "Time": datetime.fromtimestamp(pos["exit_time"]).strftime("%Y-%m-%d %H:%M:%S"),
                "NetProfit": round(neto_total, 2)
            })

    # Ordenar para que el gráfico de la web sea coherente
    formatted_data.sort(key=lambda x: x["Time"])

    mt5.shutdown()
    print(f"✅ Procesados {len(formatted_data)} trades cerrados.")

    json_file = "datos_trading.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, indent=4)
    print(f"💾 Archivo '{json_file}' actualizado localmente.")

    print("\n>> Sincronizando con el repositorio de GitHub...")
    try:
        # Configuración básica para evitar errores de identidad
        subprocess.run(["git", "config", "user.email", "bot@trading.pc"], check=False)
        subprocess.run(["git", "config", "user.name", "Bot MT5"], check=False)
        
        # 1. Pull previo: Vital para que el 'push' no sea rechazado
        print("   - Descargando posibles cambios remotos (git pull)...")
        subprocess.run(["git", "pull", "origin", "main", "--no-rebase"], capture_output=True)
        
        # 2. Add y verificar cambios
        subprocess.run(["git", "add", json_file], check=True)
        
        # Verificar si hay algo que commitear
        check_status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        
        if check_status.stdout.strip():
            print("   - Detectados nuevos datos. Creando commit...")
            fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            subprocess.run(["git", "commit", "-m", f"Auto-Sync: {len(formatted_data)} trades | {fecha_hora}"], check=True)
            
            print("   - Subiendo datos a GitHub (git push)...")
            result = subprocess.run(["git", "push", "origin", "HEAD:main"], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"\n🚀 ¡ÉXITO! Dashboard actualizado y sincronizado en la nube.")
            else:
                print(f"\n❌ ERROR en Git Push: {result.stderr}")
        else:
            print("\n✨ El archivo JSON no ha cambiado. No es necesario subir nada.")

    except Exception as e:
        print(f"\n❌ FALLO CRÍTICO en el proceso de Git: {e}")

if __name__ == "__main__":
    main()