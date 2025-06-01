import datetime
from pytz import timezone

# Zona horaria EST
est_tz = timezone("America/New_York")
ahora_est = datetime.datetime.now(est_tz)

# Solo ejecutar si es después de las 11:00 AM EST
if ahora_est.hour >= 11:
    print("✅ Ejecutando script: Es después de las 11:00 AM EST.")

    import yfinance as yf
    import pandas as pd
    import mplfinance as mpf

    def extraer_valor(serie_o_valor):
        if isinstance(serie_o_valor, pd.Series):
            return float(serie_o_valor.iloc[0])
        else:
            return float(serie_o_valor)

    # Descargar datos SPY
    spy = yf.download('SPY', period='3mo', interval='1h', auto_adjust=False)
    spy.dropna(inplace=True)

    # Calcular medias móviles MP20 y MP40
    spy['MP20'] = spy['Close'].rolling(window=100).mean()
    spy['MP40'] = spy['Close'].rolling(window=200).mean()

    print("Último dato disponible:", spy.index[-1])

    def detectar_martillos_confirmados(df):
        señales = []
        for i in range(1, len(df) - 1): 
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

    señales_detectadas = detectar_martillos_confirmados(spy)

    if not señales_detectadas.empty:
        última_señal = señales_detectadas.iloc[-1]
        print("✅ Última señal detectada (Martillo + Confirmación + MP20 > MP40):")
        print(f"  📆 {última_señal['Fecha'].strftime('%Y-%m-%d %H:%M')} | 🔽 Soporte: ${última_señal['Low']:.2f}")
    else:
        print("❌ No se detectaron señales completas en el período analizado.")

    def graficar_última_señal(df, señal):
        idx = int(señal['Index'])
        fecha = pd.to_datetime(señal['Fecha'])

        inicio = max(0, idx - 10)
        fin = min(len(df), idx + 11)

        data_ventana = df.iloc[inicio:fin].copy()

        if isinstance(data_ventana.columns, pd.MultiIndex):
            data_ventana.columns = data_ventana.columns.get_level_values(0)

        cols_ohlc = ['Open', 'High', 'Low', 'Close']
        if not all(col in data_ventana.columns for col in cols_ohlc):
            print(f"⚠️ No se encuentran todas las columnas OHLC en ventana para señal en {fecha}")
            return

        data_ventana[cols_ohlc] = data_ventana[cols_ohlc].apply(pd.to_numeric, errors='coerce')
        data_ventana.dropna(subset=cols_ohlc, inplace=True)

        if data_ventana.empty:
            print(f"⚠️ Ventana vacía tras limpiar NaNs para señal en {fecha}")
            return

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
        graficar_última_señal(spy, última_señal)

else:
    print("⛔ El script solo se ejecuta a partir de las 11:00 AM EST.")
