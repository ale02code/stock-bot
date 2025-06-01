import datetime
from pytz import timezone
import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import os

from dotenv import load_dotenv
from services.email_sender import send_email

load_dotenv()

# Zona horaria EST
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

def graficar_última_señal(df, señal, frame_grafico):
    import matplotlib
    matplotlib.use("TkAgg")

    # Limpiar frame antes de graficar
    for widget in frame_grafico.winfo_children():
        widget.destroy()

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

    fig, _ = mpf.plot(
        data_plot,
        type='candle',
        style='charles',
        returnfig=True,
        title=f"Martillo confirmado el {fecha.date()}",
        ylabel='Precio SPY (USD)',
        addplot=[mpf.make_addplot([señal['Low']] * len(data_plot), color='red', linestyle='--')]
    )

    canvas = FigureCanvasTkAgg(fig, master=frame_grafico)
    canvas.draw()
    canvas.get_tk_widget().pack(fill='both', expand=True)

def analizar():
    ahora_est = datetime.datetime.now(est_tz)
    if ahora_est.hour < 11:
        messagebox.showwarning("Horario incorrecto", "El script solo se ejecuta a partir de las 11:00 AM EST.")
        return

    correo = entry_correo.get().strip() or os.getenv('USER_EMAIL', '').strip()

    if not correo:
        messagebox.showwarning("Correo vacío", "Por favor, ingresa un correo válido.")
        return
    
    send_email(
    subject="🚨 ¡SEÑAL - PISO FUERTE! 🚨",
        body=(
            "Se notifica al correo xxxx que la estrategia piso fuerte se encuentra presente con los siguientes datos:\n"
            f"📅 Fecha: {señal_hoy['Fecha']}\n"
            f"💰 Piso: ${señal_hoy['Piso']:.2f}\n"
            f"📈 Gap: +{señal_hoy['Gap %']:.2f}%\n"
            f"🎯 Cierre: ${señal_hoy['Cierre']:.2f}\n"
            "✅ Acción: Comprar CALL ATM"
        )
    )
    lbl_estado.config(text="Descargando y analizando datos... espere...")

    # Descargar datos SPY
    spy = yf.download('SPY', period='3mo', interval='1h', auto_adjust=False)
    spy.dropna(inplace=True)

    spy['MP20'] = spy['Close'].rolling(window=100).mean()
    spy['MP40'] = spy['Close'].rolling(window=200).mean()

    señales_detectadas = detectar_martillos_confirmados(spy)

    if señales_detectadas.empty:
        lbl_estado.config(text="❌ No se detectaron señales completas en el período analizado.")
        # Limpiar gráfico si existía
        for w in frame_grafico.winfo_children():
            w.destroy()
        lbl_fecha_val.config(text="N/A")
    else:
        última_señal = señales_detectadas.iloc[-1]
        fecha_str = última_señal['Fecha'].strftime('%Y-%m-%d %H:%M')
        lbl_estado.config(text=f"✅ Última señal detectada correctamente.")
        lbl_fecha_val.config(text=fecha_str)
        graficar_última_señal(spy, última_señal, frame_grafico)

    # Aquí puedes agregar código para enviar correo si quieres, usando el valor de `correo`

# Construcción de la interfaz gráfica
root = tk.Tk()
root.title("Detector de Martillos SPY")

# Input correo
tk.Label(root, text="Ingrese su correo:").pack(padx=10, pady=(10,0))
entry_correo = tk.Entry(root, width=40)
entry_correo.pack(padx=10, pady=(0,10))

# Mostrar fecha última señal
frame_fecha = tk.Frame(root)
frame_fecha.pack(padx=10, pady=5, fill='x')
tk.Label(frame_fecha, text="Fecha última señal:").pack(side='left')
lbl_fecha_val = tk.Label(frame_fecha, text="N/A", fg='blue')
lbl_fecha_val.pack(side='left', padx=(5,0))

# Estado
lbl_estado = tk.Label(root, text="", fg="green")
lbl_estado.pack(pady=5)

# Botón analizar
btn_analizar = tk.Button(root, text="Analizar", command=analizar)
btn_analizar.pack(pady=10)

# Frame para gráfica
frame_grafico = tk.Frame(root, width=800, height=400)
frame_grafico.pack(padx=10, pady=10, fill='both', expand=True)

root.mainloop()
