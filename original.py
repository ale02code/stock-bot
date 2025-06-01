import datetime
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import tkinter as tk
from tkinter import messagebox
from pytz import timezone
from dotenv import load_dotenv
from services.email_sender import send_email

load_dotenv()

est_tz = timezone("America/New_York")

def extraer_valor(serie_o_valor):
    if isinstance(serie_o_valor, pd.Series):
        return float(serie_o_valor.iloc[0])
    else:
        return float(serie_o_valor)

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
                    mp100 = extraer_valor(vela['MP100'])
                    mp200 = extraer_valor(vela['MP200'])

                    if pd.notna(mp100) and pd.notna(mp200) and mp100 > mp200:
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

def graficar_última_señal(df, señal):
    idx = int(señal['Index'])
    fecha = pd.to_datetime(señal['Fecha'])

    inicio = max(0, idx - 10)
    fin = min(len(df), idx + 11)

    data_ventana = df.iloc[inicio:fin].copy()
    cols_ohlc = ['Open', 'High', 'Low', 'Close']
    data_ventana[cols_ohlc] = data_ventana[cols_ohlc].apply(pd.to_numeric, errors='coerce')
    data_ventana.dropna(subset=cols_ohlc, inplace=True)
    data_ventana.index = pd.to_datetime(data_ventana.index)

    mpf.plot(
        data_ventana[cols_ohlc],
        type='candle',
        style='charles',
        title=f"Martillo confirmado el {fecha.date()}",
        ylabel='Precio SPY (USD)',
        addplot=[mpf.make_addplot([señal['Low']] * len(data_ventana), color='red', linestyle='--')]
    )

def ejecutar_script():
    ahora_est = datetime.datetime.now(est_tz)
    hoy_est = ahora_est.date()

    if ahora_est.hour < 11:
        messagebox.showwarning("⛔ No disponible", "El análisis solo se ejecuta después de las 11:00 AM EST.")
        return

    spy = yf.download('SPY', period='3mo', interval='1h', auto_adjust=False)
    spy.dropna(inplace=True)
    spy['MP100'] = spy['Close'].rolling(window=100).mean()
    spy['MP200'] = spy['Close'].rolling(window=200).mean()

    señales = detectar_martillos_confirmados(spy)

    if not señales.empty:
        última_señal = señales.iloc[-1]
        fecha_señal = última_señal['Fecha'].date()

        if fecha_señal == hoy_est:
            print("✅ Piso fuerte detectado HOY.")
            graficar_última_señal(spy, última_señal)

            send_email(
                subject="🚨 ¡SEÑAL - PISO FUERTE DETECTADO! 🚨",
                body = f"""
¡Hola! 👋
Se ha detectado una señal de trading que cumple con la estrategia de Piso Fuerte en SPY:

📅 Fecha y Hora (EST): {última_señal['Fecha'].strftime('%Y-%m-%d %H:%M')}
📊 Símbolo: SPY (ETF S&P 500)

📉 Medias Móviles:
    - MP100: {spy['MP100'].iloc[última_señal['Index']]:.2f}
    - MP200: {spy['MP200'].iloc[última_señal['Index']]:.2f}

✅ Condiciones cumplidas:
    - Patrón martillo detectado 🕯️
    - Confirmación alcista con la vela siguiente ✅
    - MP100 > MP200 (tendencia alcista) 📈

🎯 Acción recomendada: Considerar compra de opción CALL ATM

📌 Nota:
    - Señal verificada después de las 11:00 AM EST
    - Aplica gestión de riesgo
                """
            )
            messagebox.showinfo("✅ Señal detectada", "Se ha detectado una señal HOY y se ha enviado el correo.")
        else:
            print("📭 Hoy no se ha presentado ningún piso fuerte.")
            messagebox.showinfo("Resultado", "Hoy no se ha presentado ningún piso fuerte.")
    else:
        print("❌ No se detectaron señales completas.")
        messagebox.showinfo("Resultado", "No se detectaron señales completas en el período analizado.")

# Interfaz
ventana = tk.Tk()
ventana.title("Detector de Piso Fuerte")
ventana.geometry("400x200")

titulo = tk.Label(ventana, text="🔍 Detector de Piso Fuerte (SPY)", font=("Arial", 14))
titulo.pack(pady=20)

boton = tk.Button(ventana, text="Ejecutar análisis ahora", command=ejecutar_script, font=("Arial", 12), bg="#4C63AF", fg="white")
boton.pack(pady=10)

ventana.mainloop()
