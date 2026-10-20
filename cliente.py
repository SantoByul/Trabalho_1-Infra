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
    print(f"[*] Conectado ao servidor {HOST}:{PORTA}\n")
    pacote_syn = criar_pacote(
        seq_num=0,
        ack_num=0,
        flags=FLAG_SYN,
        payload_texto="SYN",
    )
    cliente.sendall(pacote_syn)
    print("[>] Pacote SYN enviado ao servidor.")

    dados_resposta = cliente.recv(1024)
    pkt_syn_ack = desempacotar_pacote(dados_resposta)

    tamanho_janela = None
    if pkt_syn_ack and (pkt_syn_ack["flags"] & FLAG_SYN) and (pkt_syn_ack["flags"] & FLAG_ACK):
        tamanho_janela = int(pkt_syn_ack["payload"])

        print("--- [METADADOS] HANDSHAKE RESPONDIDO PELO SERVIDOR ---")
        print(f"AckNum Recebido: {pkt_syn_ack['ack_num']}")
        print(f"Checksum Válido: {pkt_syn_ack['is_valido']}")
        print(f"Tamanho da Janela: {tamanho_janela}\n")
    else:
        print("[!] Handshake falhou ou resposta inválida do servidor.")

    cliente.close()
    print("[*] Conexão encerrada pelo cliente.")


if __name__ == "__main__":
    iniciar_cliente()