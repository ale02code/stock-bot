import yfinance as yf
import pandas as pd
import mplfinance as mpf

# Función auxiliar para extraer valor escalar de pd.Series o float
def extraer_valor(serie_o_valor):
    if isinstance(serie_o_valor, pd.Series):
        return float(serie_o_valor.iloc[0])
    else:
        return float(serie_o_valor)

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

            open_ = extraer_valor(vela['Open'])
            close = extraer_valor(vela['Close'])
            high = extraer_valor(vela['High'])
            low = extraer_valor(vela['Low'])

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
                next_open = extraer_valor(vela_siguiente['Open'])
                next_close = extraer_valor(vela_siguiente['Close'])

                confirmada = next_close > next_open and next_close > close

                if confirmada:
                    mp20 = extraer_valor(vela['MP20'])
                    mp40 = extraer_valor(vela['MP40'])

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

        # Detectar si columnas son MultiIndex y aplanar a nombres simples
        if isinstance(data_ventana.columns, pd.MultiIndex):
            # Tomamos solo el primer nivel (por ejemplo 'Open', 'High', ...)
            data_ventana.columns = data_ventana.columns.get_level_values(0)
        
        cols_ohlc = ['Open', 'High', 'Low', 'Close']

        # Verificar que todas las columnas OHLC estén presentes
        if not all(col in data_ventana.columns for col in cols_ohlc):
            print(f"⚠️ No se encuentran todas las columnas OHLC en ventana para señal en {fecha}")
            continue

        # Convertir a numérico, forzando errores a NaN
        data_ventana[cols_ohlc] = data_ventana[cols_ohlc].apply(pd.to_numeric, errors='coerce')

        # Eliminar filas con NaN en columnas OHLC
        data_ventana.dropna(subset=cols_ohlc, inplace=True)

        if data_ventana.empty:
            print(f"⚠️ Ventana vacía tras limpiar NaNs para señal en {fecha}")
            continue

        # Asegurar índice datetime
        data_ventana.index = pd.to_datetime(data_ventana.index)

        data_plot = data_ventana[cols_ohlc].copy()

        mpf.plot(
            data_plot,
            type='candle',
            style='charles',
            title=f"Martillo confirmado el {fecha.date()}",
            ylabel='Precio SPY (USD)',
            addplot=[mpf.make_addplot([señal['Low']] * len(data_plot), color='red', linestyle='--')]
        )

if not señales_detectadas.empty:
    graficar_señales(spy, señales_detectadas)
