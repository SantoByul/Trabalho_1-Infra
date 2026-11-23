import socket
from protocolo import(
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    FLAG_NAK,
    criar_pacote,
    desempacotar_pacote,
    receber_pacote,
    codificar_parametros,
    decodificar_parametros,
    MODO_LOTE,
    CONF_GBN,
    CONF_SR,
    TAMANHO_JANELA_PADRAO,
    TAMANHO_MINIMO_MENSAGEM_PADRAO,
)

HOST = "127.0.0.1"
PORTA = 50000
TIMEOUT_ESPERA_FIN = 2.0


def definir_tamanho_janela() -> int:
    entrada = input("Defina o tamanho da janela de recepcao (1 a 5, Enter para padrao 5): ").strip()
    if entrada == "":
        return TAMANHO_JANELA_PADRAO
    try:
        valor = int(entrada)
    except ValueError:
        print("[!] Valor invalido, usando padrao (5).")
        return TAMANHO_JANELA_PADRAO
    if valor < 1 or valor > 5:
        print("[!] Valor fora do intervalo permitido, usando padrao (5).")
        return TAMANHO_JANELA_PADRAO
    return valor


def iniciar_servidor():
    tamanho_janela = definir_tamanho_janela()

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORTA))
    servidor.listen(1)

    print(f"[*] SERVIDORES ATIVO - Escutando em {HOST}:{PORTA}")

    conn, addr = servidor.accept()
    print(f"[+] Cliente conectado com sucesso! Origem: {addr}\n")

    modo_negociado = MODO_LOTE
    confirmacao_negociada = CONF_GBN

    pkt_syn = receber_pacote(conn)

    if pkt_syn and (pkt_syn["flags"] & FLAG_SYN):
        parametros_cliente = decodificar_parametros(pkt_syn["payload"])
        modo_negociado = parametros_cliente.get("MODO", MODO_LOTE)
        confirmacao_negociada = parametros_cliente.get("CONF", CONF_GBN)
        tamanho_max_solicitado = parametros_cliente.get("MAXMSG", str(TAMANHO_MINIMO_MENSAGEM_PADRAO))

        print("--- [METADADOS] HANDSHAKE RECEBIDO DO CLIENTE ---")
        print(f"SeqNum Recebido         : {pkt_syn['seq_num']}")
        print(f"Checksum Valido         : {pkt_syn['is_valido']}")
        print(f"Modo de operacao        : {modo_negociado}")
        print(f"Tipo de confirmacao     : {confirmacao_negociada}")
        print(f"Tamanho maximo mensagem : {tamanho_max_solicitado}")

        resposta_parametros = codificar_parametros({
            "JANELA": tamanho_janela,
            "MODO": modo_negociado,
            "CONF": confirmacao_negociada,
            "MAXMSG": tamanho_max_solicitado,
        })

        resposta_syn = criar_pacote(
            seq_num=0,
            ack_num=pkt_syn["seq_num"],
            flags=FLAG_SYN | FLAG_ACK,
            payload_texto=resposta_parametros,
        )
        conn.sendall(resposta_syn)
        print(f"[>] Resposta SYN+ACK enviada ao cliente: {resposta_parametros}\n")

    mensagem_reconstruida = []
    proximo_seq_esperado = 0
    buffer_fora_de_ordem = {}

    while True:
        pacote = receber_pacote(conn)
        if pacote is None:
            break

        print("--- [METADADOS] PACOTE RECEBIDO NO SERVIDOR ---")
        print(f"Numero de Sequencia (SeqNum) : {pacote['seq_num']}")
        print(f"Flags de Controle            : {pacote['flags']}")
        print(f"Checksum Recebido            : {hex(pacote['checksum'])}")
        print(f"Integridade do Checksum      : {pacote['is_valido']}")
        print(f"Payload Decifrado (4 chars)  : {pacote['payload']!r}")

        if not pacote["is_valido"]:
            print(f"\n[ERRO RDT] Checksum INVALIDO no pacote SeqNum={pacote['seq_num']}! Pacote descartado.")
            nak_pkt = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_NAK, payload_texto="NAK")
            conn.sendall(nak_pkt)
            print(f"[RDT RECOVERY] NAK enviado para SeqNum={pacote['seq_num']}.")
            print("-" * 50 + "\n")
            continue

        if pacote["flags"] & FLAG_FIN:
            print("\n[!] Sinal de Encerramento (FIN) detectado. Finalizando recepcao...")
            ack_fin = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_ACK | FLAG_FIN, payload_texto="OK")
            conn.sendall(ack_fin)

            conn.settimeout(TIMEOUT_ESPERA_FIN)
            aguardando_fin_repetido = True
            while aguardando_fin_repetido:
                try:
                    pacote_repetido = receber_pacote(conn)
                    if pacote_repetido and (pacote_repetido["flags"] & FLAG_FIN):
                        print("[RDT RECOVERY] FIN repetido recebido (ACK+FIN anterior pode ter se perdido/corrompido). Reenviando confirmacao...")
                        conn.sendall(ack_fin)
                    else:
                        aguardando_fin_repetido = False
                except socket.timeout:
                    aguardando_fin_repetido = False
            conn.settimeout(None)
            break

        if confirmacao_negociada == CONF_SR:
            if pacote["seq_num"] < proximo_seq_esperado:
                ack_pkt = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_ACK, payload_texto="ACK")
                conn.sendall(ack_pkt)
                print(f"[>] Pacote duplicado SeqNum={pacote['seq_num']}, ACK reenviado.\n")
                print("-" * 50)
                continue

            if pacote["seq_num"] != proximo_seq_esperado:
                buffer_fora_de_ordem[pacote["seq_num"]] = pacote["payload"]
                ack_pkt = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_ACK, payload_texto="ACK")
                conn.sendall(ack_pkt)
                print(f"[RDT] Pacote fora de ordem bufferizado (SeqNum={pacote['seq_num']}). ACK individual enviado.\n")
                print("-" * 50)
                continue

            mensagem_reconstruida.append(pacote["payload"])
            ack_pkt = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_ACK, payload_texto="ACK")
            conn.sendall(ack_pkt)
            proximo_seq_esperado += 1

            while proximo_seq_esperado in buffer_fora_de_ordem:
                mensagem_reconstruida.append(buffer_fora_de_ordem.pop(proximo_seq_esperado))
                proximo_seq_esperado += 1

            print(f"[>] Confirmacao individual (ACK {pacote['seq_num']}) enviada ao cliente.\n")
            print("-" * 50)
            continue

        if pacote["seq_num"] != proximo_seq_esperado:
            print(f"\n[ERRO RDT] Pacote FORA DE ORDEM! Esperado SeqNum={proximo_seq_esperado}, recebido={pacote['seq_num']}.")
            nak_pkt = criar_pacote(seq_num=0, ack_num=proximo_seq_esperado, flags=FLAG_NAK, payload_texto="NAK")
            conn.sendall(nak_pkt)
            print(f"[RDT RECOVERY] Pacote descartado. NAK enviado (esperado SeqNum={proximo_seq_esperado}).")
            print("-" * 50 + "\n")
            continue

        mensagem_reconstruida.append(pacote["payload"])
        ack_pkt = criar_pacote(seq_num=0, ack_num=pacote["seq_num"], flags=FLAG_ACK, payload_texto="ACK")
        conn.sendall(ack_pkt)
        proximo_seq_esperado += 1

        print(f"[>] Confirmacao (ACK {pacote['seq_num']}) enviada ao cliente.\n")
        print("-" * 50)

    texto_final = "".join(mensagem_reconstruida)

    print("\n" + "=" * 50)
    print("      MENSAGEM COMPLETA RECONSTRUIDA NO SERVIDOR")
    print("=" * 50)
    print(f'"{texto_final}"')
    print("=" * 50 + "\n")

    conn.close()
    servidor.close()
    print("[*] Conexao encerrada pelo servidor.")


if __name__ == "__main__":
    iniciar_servidor()