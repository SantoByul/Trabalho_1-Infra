import socket
from protocolo import (
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    criar_pacote,
    desempacotar_pacote,
)

HOST = "127.0.0.1"
PORTA = 50000


def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    cliente.connect((HOST, PORTA))
    print(f"Conectado ao servidor {HOST}:{PORTA}\n")

    cliente.close()
    print("Conexão encerrada pelo cliente.")


if __name__ == "__main__":
    iniciar_cliente()