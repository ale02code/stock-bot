import yfinance as yf
import pandas as pd
import mplfinance as mpf

# ======================================
# Paso 1: Descargar datos SPY
# ======================================
spy = yf.download('SPY', period='7d', interval='2m')
spy.dropna(inplace=True)

# ======================================
# Paso 2: Función para detectar martillos confirmados (tu código original)
# ======================================
def detectar_martillos_confirmados(df):
    señales = []

    for i in range(1, len(df) - 1):  # -1 porque miramos la vela siguiente
        try:
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

            es_martillo = (
                mecha_inf >= 2 * cuerpo and
                mecha_sup <= cuerpo * 0.5 and
                close > open_
            )

            if es_martillo:
                vela_siguiente = df.iloc[i + 1]
                next_open = float(vela_siguiente['Open'])
                next_close = float(vela_siguiente['Close'])

                confirmada = next_close > next_open and next_close > close

                if confirmada:
                    señales.append({
                        'Fecha': df.index[i],
                        'Low': low,
                        'Close': close,
                        'Index': i
                    })

        except Exception as e:
            print(f"⚠️ Error en índice {i}: {e}")
            continue

    return pd.DataFrame(señales)

# ======================================
# Paso 3: Ejecutar detección
# ======================================
señales_detectadas = detectar_martillos_confirmados(spy)

# ======================================
# Paso 4: Mostrar señales
# ======================================
if not señales_detectadas.empty:
    print("✅ Señales detectadas (Martillo + Confirmación):")
    for _, señal in señales_detectadas.iterrows():
        print(f"  📆 {señal['Fecha']} | 🔽 Soporte: ${señal['Low']:.2f}")
else:
    print("❌ No se detectaron señales en el período analizado.")

# ======================================
# Paso 5: Graficar señales SIN modificar lógica de detección
# ======================================
def graficar_señales(df, señales_df):
    for _, señal in señales_df.iterrows():
        idx = int(señal['Index'])
        fecha = pd.to_datetime(señal['Fecha'])

        inicio = max(0, idx - 3)
        fin = min(len(df), idx + 4)

        data_ventana = df.iloc[inicio:fin].copy()

        # Aplanar MultiIndex si lo hubiera
        data_ventana.columns = ['_'.join(map(str, col)).strip() if isinstance(col, tuple) else col for col in data_ventana.columns]

        # Renombrar columnas para que mplfinance las reconozca
        rename_map = {
            'Open_SPY': 'Open',
            'High_SPY': 'High',
            'Low_SPY': 'Low',
            'Close_SPY': 'Close',
            'Volume_SPY': 'Volume'
        }
        data_ventana.rename(columns=rename_map, inplace=True)

        # Verificar columnas OHLC
        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        if not all(col in data_ventana.columns for col in ohlc_cols):
            print("No se encontraron todas las columnas OHLC, verifica los nombres de columnas.")
            continue

        # Convertir a numérico y limpiar NaNs
        data_ventana[ohlc_cols] = data_ventana[ohlc_cols].apply(pd.to_numeric, errors='coerce')
        data_ventana.dropna(subset=ohlc_cols, inplace=True)

        mpf.plot(
            data_ventana,
            type='candle',
            style='charles',
            title=f"Martillo confirmado el {fecha.date()}",
            ylabel='Precio SPY (USD)',
            addplot=[
                mpf.make_addplot([señal['Low']] * len(data_ventana), color='red', linestyle='--')
            ]
        )

if not señales_detectadas.empty:
    graficar_señales(spy, señales_detectadas)
