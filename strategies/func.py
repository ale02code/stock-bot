import yfinance as yf
import pandas as pd

# ======================================
# Paso 1: Descargar datos de BTC-USD
# ======================================
btc = yf.download('BTC-USD', period='60d', interval='1d')

# ======================================
# Paso 2: Limpiar datos faltantes
# ======================================
btc.dropna(inplace=True)

# ======================================
# Paso 3 + 4: Detectar martillos con confirmación de rebote
# ======================================
def detectar_martillos_confirmados(df):
    señales = []

    for i in range(1, len(df) - 1):  # -1 porque miramos la vela siguiente
        try:
            # Vela candidata a martillo
            vela = df.iloc[i]
            open_ = float(vela['Open'])
            close = float(vela['Close'])
            high = float(vela['High'])
            low = float(vela['Low'])

            cuerpo = abs(close - open_)
            mecha_sup = high - max(open_, close)
            mecha_inf = min(open_, close) - low

            if cuerpo == 0 or mecha_inf < 0 or mecha_sup < 0:
                continue

            # Martillo válido
            es_martillo = (
                mecha_inf >= 2 * cuerpo and
                mecha_sup <= cuerpo * 0.5 and
                close > open_
            )

            if es_martillo:
                # Paso 4: Confirmación con vela siguiente
                vela_siguiente = df.iloc[i + 1]
                next_open = float(vela_siguiente['Open'])
                next_close = float(vela_siguiente['Close'])

                confirmada = next_close > next_open and next_close > close

                if confirmada:
                    señales.append({
                        'Fecha': df.index[i].date(),
                        'Low': low,
                        'Martillo confirmado': True
                    })

        except Exception as e:
            print(f"⚠️ Error en índice {i}: {e}")
            continue

    return señales

# ======================================
# Paso 5: Ejecutar y mostrar señales detectadas
# ======================================
señales_detectadas = detectar_martillos_confirmados(btc)

if señales_detectadas:
    print("✅ Señales detectadas (Martillo + Confirmación):")
    for señal in señales_detectadas:
        print(f"  📆 {señal['Fecha']} | 🔽 Soporte: ${señal['Low']:.2f}")
else:
    print("❌ No se detectaron señales en el período analizado.")
