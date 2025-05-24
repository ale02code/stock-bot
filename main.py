from services.email_sender import send_email

def main():
    print("Ingrese 1 para enviar una alerta por correo:")
    opcion = input(">> ")

    if opcion == "1":
        send_email(
            subject="📢 Alerta Manual",
            body="Se ha enviado esta alerta porque el usuario ingresó 1."
        )
        print("✅ Correo enviado.")
    else:
        print("❌ Opción inválida. No se envió nada.")

if __name__ == "__main__":
    main()