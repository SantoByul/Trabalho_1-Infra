import socket
from protocolo import(
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    criar_pacote,
    desempacotar_pacote,
    receber_pacote,
    codificar_parametros,
    decodificar_parametros,
    MODO_LOTE,
    CONF_GBN,
    TAMANHO_JANELA_PADRAO,
    TAMANHO_MINIMO_MENSAGEM_PADRAO,
)

#configuraçoes de rede
HOST = "127.0.0.1"
PORTA = 50000

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
        parametros_cliente = decodificar_parametros(pkt_syn["payload"])
        modo_solicitado = parametros_cliente.get("MODO", MODO_LOTE)
        confirmacao_solicitada = parametros_cliente.get("CONF", CONF_GBN)
        tamanho_max_solicitado = parametros_cliente.get(
            "MAXMSG", str(TAMANHO_MINIMO_MENSAGEM_PADRAO)
        )

        print("--- [METADADOS] HANDSHAKE RECEBIDO DO CLIENTE ---")
        print(f"SeqNum Recebido         : {pkt_syn['seq_num']}")
        print(f"Checksum Valido         : {pkt_syn['is_valido']}")
        print(f"Modo de operacao        : {modo_solicitado}")
        print(f"Tipo de confirmacao     : {confirmacao_solicitada}")
        print(f"Tamanho maximo mensagem : {tamanho_max_solicitado}")

        resposta_parametros = codificar_parametros({
            "JANELA": tamanho_janela,
            "MODO": modo_solicitado,
            "CONF": confirmacao_solicitada,
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

    #etapa 2
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

        #Checkpoint 3 - verificação rdt de integridade e ordem
        #CENÁRIO 1: PACOTE CORROMPIDO (Checksum falhou)
        if not pacote["is_valido"]:
            print(
                f"\n [ERRO RDT] Checksum INVÁLIDO no pacote SeqNum={pacote['seq_num']}! Pacote descartado."
            )
            if ultimo_ack_enviado is not None:
                print(
                    " [RDT RECOVERY] Reenviando último ACK válido ao cliente..."
                )
                conn.sendall(ultimo_ack_enviado)
            print("-" * 50 + "\n")
            continue

        #CENÁRIO 2: PACOTE FORA DE ORDEM
        if pacote["seq_num"] != proximo_seq_esperado:
            print(
                f"\n [ERRO RDT] Pacote FORA DE ORDEM! Esperado SeqNum={proximo_seq_esperado}, recebido={pacote['seq_num']}."
            )
            print(
                " [RDT RECOVERY] Pacote descartado. Reenviando último ACK válido ao cliente..."
            )
            if ultimo_ack_enviado is not None:
                conn.sendall(ultimo_ack_enviado)
            print("-" * 50 + "\n")
            continue
        
        #CENÁRIO 3: SINAL DE ENCERRAMENTO (FIN)
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

        # CENÁRIO 4: PACOTE VÁLIDO E EM ORDEM (Caminho Feliz / Recuperado)
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
            f"[>] Confirmação (ACK {pacote['seq_num']}) enviada ao cliente.\n"
        )
        print("-" * 50)

    # Etapa 3: Reconstituição e Exibição da Mensagem Final
    texto_final = "".join(mensagem_reconstruida)

    print("\n" + "=" * 50)
    print("      MENSAGEM COMPLETA RECONSTRUIDA NO SERVIDOR")
    print("=" * 50)
    print(f'"{texto_final}"')
    print("=" * 50 + "\n")

    # Encerra as conexões
    conn.close()
    servidor.close()
    print("[*] Conexão encerrada pelo servidor.")


if __name__ == "__main__":
    iniciar_servidor()