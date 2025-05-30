import yfinance as yf
import pandas as pd
import mplfinance as mpf

# ======================================
# Paso 1: Descargar datos SPY
# ======================================
spy = yf.download('SPY', period='30d', interval='15m', auto_adjust=False)
spy.dropna(inplace=True)

# ======================================
# Paso 2: Calcular medias móviles MP20 y MP40
# ======================================
spy['MP20'] = spy['Close'].rolling(window=20).mean()
spy['MP40'] = spy['Close'].rolling(window=40).mean()

# ======================================
# Paso 3: Función para detectar martillos confirmados
# ======================================
def detectar_martillos_confirmados(df):
    señales = []

    for i in range(1, len(df) - 1):  # -1 porque miramos la vela siguiente
        try:
            vela = df.iloc[i]

            # Extraer valores escalar correctamente
            open_ = float(vela['Open'])
            close = float(vela['Close'])
            high = float(vela['High'])
            low = float(vela['Low'])

            cuerpo = abs(close - open_)
            mecha_sup = high - max(open_, close)
            mecha_inf = min(open_, close) - low

            if cuerpo == 0 or mecha_inf < 0 or mecha_sup < 0:
                continue

            # Condición martillo clásico: mecha inferior larga, cuerpo pequeño, poca mecha superior, cierre arriba de apertura
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
                    # DEBUG: Medias móviles para esta señal
                    mp20 = df.iloc[i]['MP20']
                    mp40 = df.iloc[i]['MP40']

                    # Extraer valores escalares si son Series
                    if isinstance(mp20, pd.Series):
                        mp20 = mp20.iloc[0]
                    if isinstance(mp40, pd.Series):
                        mp40 = mp40.iloc[0]

                    # Verificar que no sean NaN y aplicar condición MP20 > MP40
                    if pd.notna(mp20) and pd.notna(mp40) and mp20 > mp40:
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
# Paso 4: Ejecutar detección
# ======================================
señales_detectadas = detectar_martillos_confirmados(spy)

# ======================================
# Paso 5: Mostrar señales
# ======================================
if not señales_detectadas.empty:
    print("✅ Señales detectadas (Martillo + Confirmación + MP20 > MP40):")
    for _, señal in señales_detectadas.iterrows():
        print(f"  📆 {señal['Fecha']} | 🔽 Soporte: ${señal['Low']:.2f}")
else:
    print("❌ No se detectaron señales completas en el período analizado.")

# ======================================
# Paso 6: Graficar señales
# ======================================
def graficar_señales(df, señales_df):
    for _, señal in señales_df.iterrows():
        idx = int(señal['Index'])
        fecha = pd.to_datetime(señal['Fecha'])

        inicio = max(0, idx - 10)
        fin = min(len(df), idx + 11)

        data_ventana = df.iloc[inicio:fin].copy()

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
