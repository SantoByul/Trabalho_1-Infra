import socket
from protocolo import(
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    criar_pacote,
    desempacotar_pacote,
    receber_pacote,
)

#configuraçoes de rede
HOST = "127.0.0.1"
PORTA = 50000

TAMANHO_JANELA_INICIAL = 5

def iniciar_servidor():
    #cria o socket TCP (ipv4, stream)
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #permite reutilizat o endereço/porta imediatamente após fechar
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    servidor.bind((HOST, PORTA))
    servidor.listen(1)

    print(f"[*] SERVIDORES ATIVO - Escutando em {HOST}:{PORTA}")

    conn, addr = servidor.accept()
    print(f"[+] Cliente conectado com sucesso! Origem: {addr}\n")

    #etapa 1: handshake inicial
    pkt_syn = receber_pacote(conn)

    if pkt_syn and (pkt_syn["flags"] & FLAG_SYN):
        print("--- [METADADOS] HANDSHAKE RECEBIDO DO CLIENTE ---")
        print(f"SeqNum Recebido: {pkt_syn['seq_num']}")
        print(f"Checksum Válido: {pkt_syn['is_valido']}")
        print(f"Payload do Handshake: {pkt_syn['payload']!r}")

        resposta_syn = criar_pacote(
            seq_num=0,
            ack_num=pkt_syn["seq_num"],
            flags=FLAG_SYN | FLAG_ACK,
            payload_texto=str(TAMANHO_JANELA_INICIAL),
        )
        conn.sendall(resposta_syn)
        print(
            f"[>] Resposta SYN+ACK enviada ao cliente com Janela = {TAMANHO_JANELA_INICIAL}\n"
        )

    mensagem_reconstruida = []
    proximo_seq_esperado = 0
    ultimo_ack_enviado = None

    while True:
        pacote = receber_pacote(conn)
        if pacote is None:
            break

        print("--- [METADADOS] PACOTE RECEBIDO NO SERVIDO ---")
        print(f"Número de Sequência (SeqNum) : {pacote['seq_num']}")
        print(f"Flags de Controle           : {pacote['flags']}")
        print(f"Checksum Recebido           : {hex(pacote['checksum'])}")
        print(f"Integridade do Checksum     : {pacote['is_valido']}")
        print(f"Payload Decifrado (4 chars) : {pacote['payload']!r}")

        if not pacote["is_valido"] or pacote["seq_num"] != proximo_seq_esperado:
            print(
                f"[!] Pacote descartado (esperado SeqNum={proximo_seq_esperado}, "
                f"recebido={pacote['seq_num']}, válido={pacote['is_valido']}).\n"
            )
            if ultimo_ack_enviado is not None:
                conn.sendall(ultimo_ack_enviado)
                print("[>] Reenviado último ACK válido ao cliente.\n")
            continue

        if pacote["flags"] & FLAG_FIN:
            print(
                "\n[!] Sinal de Encerramento (FIN) detectado. Finalizando recepção..."
            )
            ack_fin = criar_pacote(
                seq_num=0,
                ack_num=pacote["seq_num"],
                flags=FLAG_ACK | FLAG_FIN,
                payload_texto="OK",
            )
            conn.sendall(ack_fin)
            break

        mensagem_reconstruida.append(pacote["payload"])

        ack_pkt = criar_pacote(
            seq_num=0,
            ack_num=pacote["seq_num"],
            flags=FLAG_ACK,
            payload_texto="ACK",
        )
        conn.sendall(ack_pkt)
        ultimo_ack_enviado = ack_pkt
        proximo_seq_esperado += 1
        print(
            f"[>] Confirmação (ACK {pacote['seq_num']}) enviada ao cliente."
        )

    #etapa 3: reconstituicao e exibiçao da mensage, final
    texto_final = "".join(mensagem_reconstruida)
    
    print("      MENSAGEM COMPLETA RECONSTRUIDA          ")
    print(f"\"{texto_final}\"")

    # Encerra as conexões
    conn.close()
    servidor.close()
    print("[*] Conexão encerrada pelo servidor.")


if __name__ == "__main__":
    iniciar_servidor()
