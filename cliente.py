import socket
from protocolo import (
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    criar_pacote,
    desempacotar_pacote,
    receber_pacote,
)

HOST = "127.0.0.1"
PORTA = 50000

TAMANHO_BLOCO = 4
TAMANHO_MINIMO_MENSAGEM = 30
TIMEOUT_ACK = 1.0


def exibir_metadados(pacote, direcao: str):
    if not pacote:
        print(f"[!] Pacote inválido ou conexão encerrada ({direcao}).\n")
        return pacote

    print(f"--- [METADADOS] PACOTE {direcao} ---")
    print(f"SeqNum                      : {pacote['seq_num']}")
    print(f"AckNum                      : {pacote['ack_num']}")
    print(f"Flags                       : {pacote['flags']}")
    print(f"Checksum                    : {hex(pacote['checksum'])}")
    print(f"Integridade do Checksum     : {pacote['is_valido']}")
    print(f"Payload                     : {pacote['payload']!r}\n")
    return pacote


def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect((HOST, PORTA))
    print(f"[*] Conectado ao servidor {HOST}:{PORTA}\n")

    pacote_syn = criar_pacote(seq_num=0, ack_num=0, flags=FLAG_SYN, payload_texto="SYN")
    exibir_metadados(desempacotar_pacote(pacote_syn), "ENVIADO (SYN)")
    cliente.sendall(pacote_syn)

    pkt_syn_ack = receber_pacote(cliente)
    exibir_metadados(pkt_syn_ack, "RECEBIDO (SYN+ACK)")

    if not pkt_syn_ack or not ((pkt_syn_ack["flags"] & FLAG_SYN) and (pkt_syn_ack["flags"] & FLAG_ACK)):
        print("[!] Handshake falhou ou resposta inválida do servidor.")
        cliente.close()
        return

    tamanho_janela = int(pkt_syn_ack["payload"])
    print(f"[*] Tamanho da janela definido pelo servidor: {tamanho_janela}\n")

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
            exibir_metadados(desempacotar_pacote(pacote), f"ENVIADO (SeqNum={proximo_a_enviar})")
            cliente.sendall(pacote)
            proximo_a_enviar += 1

        try:
            pkt_ack = receber_pacote(cliente)
            exibir_metadados(pkt_ack, "RECEBIDO (ACK)")

            if pkt_ack and pkt_ack["is_valido"] and (pkt_ack["flags"] & FLAG_ACK):
                if pkt_ack["ack_num"] >= base:
                    base = pkt_ack["ack_num"] + 1
        except socket.timeout:
            print(f"[!] Timeout esperando ACK. Retransmitindo a partir do SeqNum={base}...\n")
            proximo_a_enviar = base

    seq_fin = len(blocos)
    fin_confirmado = False

    while not fin_confirmado:
        pacote_fin = criar_pacote(seq_num=seq_fin, ack_num=0, flags=FLAG_FIN, payload_texto="FIN")
        exibir_metadados(desempacotar_pacote(pacote_fin), f"ENVIADO (FIN, SeqNum={seq_fin})")
        cliente.sendall(pacote_fin)

        try:
            pkt_fin_ack = receber_pacote(cliente)
            exibir_metadados(pkt_fin_ack, "RECEBIDO (ACK+FIN)")

            if pkt_fin_ack and pkt_fin_ack["is_valido"] and (pkt_fin_ack["flags"] & FLAG_FIN) and (pkt_fin_ack["flags"] & FLAG_ACK):
                fin_confirmado = True
        except socket.timeout:
            print("[!] Timeout esperando ACK+FIN. Retransmitindo FIN...\n")

    cliente.settimeout(None)
    cliente.close()
    print("[*] Conexão encerrada pelo cliente.")


if __name__ == "__main__":
    iniciar_cliente()