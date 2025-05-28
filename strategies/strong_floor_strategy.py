from services.stock_data import fetch_stock_data
  
print("Datos de acciones obtenidos:")
stock_data = fetch_stock_data()
print(stock_data)