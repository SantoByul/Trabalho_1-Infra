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

TAMANHO_BLOCO = 4
TAMANHO_MINIMO_MENSAGEM = 30
TIMEOUT_ACK = 1.0  # segundos


def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((HOST, PORTA))
    print(f"[*] Conectado ao servidor {HOST}:{PORTA}\n")

    pacote_syn = criar_pacote(seq_num=0, ack_num=0, flags=FLAG_SYN, payload_texto="SYN")
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
        return

    mensagem = input("Digite a mensagem a ser enviada (mínimo 30 caracteres): ")
    while len(mensagem) < TAMANHO_MINIMO_MENSAGEM:
        print(f"[!] Mensagem muito curta ({len(mensagem)} caracteres). Tente novamente.")
        mensagem = input("Digite a mensagem a ser enviada (mínimo 30 caracteres): ")

    blocos = [
        mensagem[i:i + TAMANHO_BLOCO]
        for i in range(0, len(mensagem), TAMANHO_BLOCO)
    ]
    print(f"[*] Mensagem fatiada em {len(blocos)} blocos.\n")

    base = 0                
    proximo_a_enviar = 0     

    cliente.settimeout(TIMEOUT_ACK)

    while base < len(blocos):
        while proximo_a_enviar < len(blocos) and proximo_a_enviar < base + tamanho_janela:
            pacote = criar_pacote(
                seq_num=proximo_a_enviar,
                ack_num=0,
                flags=FLAG_ACK,
                payload_texto=blocos[proximo_a_enviar],
            )
            cliente.sendall(pacote)
            print(f"[>] Enviado bloco SeqNum={proximo_a_enviar}: '{blocos[proximo_a_enviar]}'")
            proximo_a_enviar += 1

        try:
            dados_ack = cliente.recv(1024)
            pkt_ack = desempacotar_pacote(dados_ack)

            if pkt_ack and pkt_ack["is_valido"] and (pkt_ack["flags"] & FLAG_ACK):
                print(f"--- [METADADOS] ACK RECEBIDO: AckNum={pkt_ack['ack_num']} ---")
                if pkt_ack["ack_num"] >= base:
                    base = pkt_ack["ack_num"] + 1 
        except socket.timeout:
            print(f"[!] Timeout esperando ACK. Retransmitindo a partir do SeqNum={base}...")
            proximo_a_enviar = base 

    cliente.settimeout(None)

    cliente.close()
    print("[*] Conexão encerrada pelo cliente.")


if __name__ == "__main__":
    iniciar_cliente()