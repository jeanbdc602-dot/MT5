import os
import sys
import json
import subprocess
from datetime import datetime

# --- AUTO-INSTALACIÓN ---
try:
    import MetaTrader5 as mt5
except ImportError:
    print("Instalando MetaTrader5...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
    import MetaTrader5 as mt5

def main():
    print("========================================")
    print("   SISTEMA DE ACTUALIZACIÓN MT5 V3.0   ")
    print("========================================\n")

    print(">> Conectando con la terminal MT5...")
    if not mt5.initialize():
        print("❌ ERROR: No se pudo conectar a MT5. Verifica que esté abierto.")
        sys.exit(1)

    print(">> Extrayendo historial crudo...")
    fecha_inicio = datetime(2020, 1, 1)
    fecha_fin = datetime.now()
    deals = mt5.history_deals_get(fecha_inicio, fecha_fin)

    if not deals:
        print("⚠️ No hay operaciones en el historial.")
        mt5.shutdown()
        sys.exit(1)

    # --- EL MOTOR INTELIGENTE: AGRUPACIÓN POR POSITION ID ---
    print(">> Reconstruyendo operaciones mediante Position ID...")
    positions = {}
    
    for d in deals:
        # Ignorar depósitos, retiros o filas vacías
        if d.type == 2 or d.symbol == "":
            continue
            
        pid = d.position_id
        if pid not in positions:
            positions[pid] = {
                "symbol": d.symbol,
                "entry_time": None,
                "exit_time": None,
                "net_profit": 0.0
            }
        
        # Sumar todos los fragmentos de la misma operación
        positions[pid]["net_profit"] += float(d.profit) + float(d.commission) + float(d.swap)
        
        # Identificar las fechas correctas de apertura y cierre
        if d.entry == 0:  # Entrada (IN)
            if positions[pid]["entry_time"] is None or d.time < positions[pid]["entry_time"]:
                positions[pid]["entry_time"] = d.time
        elif d.entry == 1 or d.entry == 2:  # Salida (OUT o IN/OUT)
            if positions[pid]["exit_time"] is None or d.time > positions[pid]["exit_time"]:
                positions[pid]["exit_time"] = d.time

    # --- FORMATEO PARA LA WEB ---
    formatted_data = []
    for pid, pos in positions.items():
        # Asegurarnos de que el trade ya está cerrado
        if pos["exit_time"] is not None:
            # Si por algún motivo MT5 no arrojó la entrada, usamos la de salida como respaldo
            ent = pos["entry_time"] if pos["entry_time"] is not None else pos["exit_time"]
            
            formatted_data.append({
                "Symbol": pos["symbol"],
                "EntryTime": datetime.fromtimestamp(ent).strftime("%Y-%m-%d %H:%M:%S"),
                "Time": datetime.fromtimestamp(pos["exit_time"]).strftime("%Y-%m-%d %H:%M:%S"),
                "NetProfit": round(pos["net_profit"], 2)
            })

    # Ordenar cronológicamente
    formatted_data.sort(key=lambda x: x["Time"])

    mt5.shutdown()
    print(f"✅ Se reconstruyeron {len(formatted_data)} operaciones perfectas.")

    # --- GUARDAR Y SUBIR ---
    json_file = "datos_trading.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(formatted_data, f, indent=4)
    print(f"💾 Archivo '{json_file}' generado con éxito.")

    print("\n>> Sincronizando con GitHub...")
    try:
        subprocess.run(["git", "config", "--local", "user.email", "bot@trading.pc"], check=False)
        subprocess.run(["git", "config", "--local", "user.name", "Bot MT5"], check=False)
        
        print("   - Descargando cambios de la web...")
        subprocess.run(["git", "pull", "origin", "main", "--no-edit"], check=False)
        
        subprocess.run(["git", "add", json_file], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        
        if json_file in status.stdout or "M  datos_trading.json" in status.stdout:
            fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            subprocess.run(["git", "commit", "-m", f"Trades reconstruidos y subidos: {fecha_hora}"], check=True)
            print("   - Empujando a los servidores de GitHub...")
            
            result = subprocess.run(["git", "push", "origin", "HEAD:main"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"\n🚀 ¡ÉXITO! JSON subido correctamente.")
            else:
                print(f"\n❌ Error al subir: {result.stderr}")
        else:
            print("\n✨ El historial ya estaba idéntico en la nube.")

    except Exception as e:
        print(f"\n❌ Fallo en la subida automática: {e}")

if __name__ == "__main__":
    main()