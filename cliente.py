import socket
import time
from protocolo import (
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    FLAG_NAK,
    criar_pacote,
    desempacotar_pacote,
    receber_pacote,
    codificar_parametros,
    decodificar_parametros,
    MODO_INDIVIDUAL,
    MODO_LOTE,
    CONF_GBN,
    CONF_SR,
    TAMANHO_MINIMO_MENSAGEM_PADRAO,
)

HOST = "127.0.0.1"
PORTA = 50000

TAMANHO_BLOCO = 4
TIMEOUT_ACK = 1.0


def exibir_metadados(pacote, direcao: str):
    if not pacote:
        print(f"[!] Pacote invalido ou conexao encerrada ({direcao}).\n")
        return pacote

    print(f"--- [METADADOS] PACOTE {direcao} ---")
    print(f"SeqNum                      : {pacote['seq_num']}")
    print(f"AckNum                      : {pacote['ack_num']}")
    print(f"Flags                       : {pacote['flags']}")
    print(f"Checksum                    : {hex(pacote['checksum'])}")
    print(f"Integridade do Checksum     : {pacote['is_valido']}")
    print(f"Payload                     : {pacote['payload']!r}\n")
    return pacote


def definir_parametros_operacao():
    print("Modo de envio: [1] Lote (janela)  [2] Individual (pacote a pacote)")
    escolha_modo = input("Escolha o modo de envio (padrao 1): ").strip()
    modo = MODO_INDIVIDUAL if escolha_modo == "2" else MODO_LOTE

    print("Tipo de confirmacao: [1] Go-Back-N  [2] Repeticao Seletiva")
    escolha_conf = input("Escolha o tipo de confirmacao (padrao 1): ").strip()
    confirmacao = CONF_SR if escolha_conf == "2" else CONF_GBN

    entrada_tamanho = input(
        f"Tamanho maximo da mensagem (minimo {TAMANHO_MINIMO_MENSAGEM_PADRAO}, Enter para padrao): "
    ).strip()
    if entrada_tamanho == "":
        tamanho_maximo = TAMANHO_MINIMO_MENSAGEM_PADRAO
    else:
        try:
            tamanho_maximo = int(entrada_tamanho)
        except ValueError:
            tamanho_maximo = TAMANHO_MINIMO_MENSAGEM_PADRAO
        if tamanho_maximo < TAMANHO_MINIMO_MENSAGEM_PADRAO:
            print(f"[!] Valor abaixo do minimo, usando {TAMANHO_MINIMO_MENSAGEM_PADRAO}.")
            tamanho_maximo = TAMANHO_MINIMO_MENSAGEM_PADRAO

    return modo, confirmacao, tamanho_maximo


def enviar_mensagem_individual(cliente, blocos):
    for indice, bloco in enumerate(blocos):
        confirmado = False
        while not confirmado:
            pacote = criar_pacote(seq_num=indice, ack_num=0, flags=FLAG_ACK, payload_texto=bloco)
            exibir_metadados(desempacotar_pacote(pacote), f"ENVIADO (SeqNum={indice})")
            cliente.sendall(pacote)

            try:
                pkt_resposta = receber_pacote(cliente)
                exibir_metadados(pkt_resposta, "RECEBIDO (ACK/NAK)")

                if pkt_resposta and not pkt_resposta["is_valido"]:
                    print("[!] Confirmacao corrompida recebida, aguardando nova tentativa...\n")
                elif pkt_resposta and (pkt_resposta["flags"] & FLAG_NAK):
                    print(f"[!] NAK recebido para SeqNum={indice}. Retransmitindo...\n")
                elif pkt_resposta and (pkt_resposta["flags"] & FLAG_ACK) and pkt_resposta["ack_num"] == indice:
                    confirmado = True
            except socket.timeout:
                print(f"[!] Timeout esperando confirmacao do SeqNum={indice}. Retransmitindo...\n")


def enviar_mensagem_em_lote(cliente, blocos, tamanho_janela, confirmacao_confirmada):
    base = 0
    proximo_a_enviar = 0
    confirmados = [False] * len(blocos)

    while base < len(blocos):
        while proximo_a_enviar < len(blocos) and proximo_a_enviar < base + tamanho_janela:
            if confirmacao_confirmada == CONF_SR and confirmados[proximo_a_enviar]:
                proximo_a_enviar += 1
                continue

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
            pkt_resposta = receber_pacote(cliente)
            exibir_metadados(pkt_resposta, "RECEBIDO (ACK/NAK)")

            if pkt_resposta and not pkt_resposta["is_valido"]:
                print("[!] Confirmacao corrompida recebida, aguardando nova tentativa...\n")

            elif pkt_resposta and (pkt_resposta["flags"] & FLAG_NAK):
                seq_problema = pkt_resposta["ack_num"]
                print(f"[!] NAK recebido para SeqNum={seq_problema}. Retransmitindo imediatamente...\n")
                if confirmacao_confirmada == CONF_SR:
                    pacote = criar_pacote(
                        seq_num=seq_problema,
                        ack_num=0,
                        flags=FLAG_ACK,
                        payload_texto=blocos[seq_problema],
                    )
                    exibir_metadados(desempacotar_pacote(pacote), f"REENVIADO (SeqNum={seq_problema})")
                    cliente.sendall(pacote)
                else:
                    base = seq_problema
                    proximo_a_enviar = base

            elif pkt_resposta and (pkt_resposta["flags"] & FLAG_ACK):
                if confirmacao_confirmada == CONF_SR:
                    confirmados[pkt_resposta["ack_num"]] = True
                    while base < len(blocos) and confirmados[base]:
                        base += 1
                else:
                    if pkt_resposta["ack_num"] >= base:
                        base = pkt_resposta["ack_num"] + 1

        except socket.timeout:
            if confirmacao_confirmada == CONF_SR:
                print(f"[!] Timeout. Reenviando pacotes pendentes a partir do SeqNum={base}...\n")
                for i in range(base, proximo_a_enviar):
                    if not confirmados[i]:
                        pacote = criar_pacote(seq_num=i, ack_num=0, flags=FLAG_ACK, payload_texto=blocos[i])
                        exibir_metadados(desempacotar_pacote(pacote), f"REENVIADO (SeqNum={i})")
                        cliente.sendall(pacote)
            else:
                print(f"[!] Timeout esperando ACK. Retransmitindo a partir do SeqNum={base}...\n")
                proximo_a_enviar = base


def iniciar_cliente():
    cliente = None
    conectado = False
    tentativas = 5

    while not conectado and tentativas > 0:
        try:
            cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            cliente.connect((HOST, PORTA))
            conectado = True
            print(f"[*] Conectado ao servidor {HOST}:{PORTA} com sucesso!\n")
        except ConnectionRefusedError:
            tentativas -= 1
            if cliente:
                cliente.close()
            print(
                f"[!] Servidor em {HOST}:{PORTA} nao encontrado. Tentando novamente em 2s... (Tentativas restantes: {tentativas})"
            )
            time.sleep(2)

    if not conectado:
        print(
            "\n[X] Erro: Nao foi possivel conectar ao servidor. Certifique-se de executar 'python3 server.py' primeiro."
        )
        return

    modo, confirmacao, tamanho_maximo_mensagem = definir_parametros_operacao()

    parametros_syn = codificar_parametros({
        "MODO": modo,
        "CONF": confirmacao,
        "MAXMSG": tamanho_maximo_mensagem,
    })
    pacote_syn = criar_pacote(seq_num=0, ack_num=0, flags=FLAG_SYN, payload_texto=parametros_syn)
    exibir_metadados(desempacotar_pacote(pacote_syn), "ENVIADO (SYN)")
    cliente.sendall(pacote_syn)

    pkt_syn_ack = receber_pacote(cliente)
    exibir_metadados(pkt_syn_ack, "RECEBIDO (SYN+ACK)")

    if not pkt_syn_ack or not ((pkt_syn_ack["flags"] & FLAG_SYN) and (pkt_syn_ack["flags"] & FLAG_ACK)):
        print("[!] Handshake falhou ou resposta invalida do servidor.")
        cliente.close()
        return

    parametros_servidor = decodificar_parametros(pkt_syn_ack["payload"])
    tamanho_janela = int(parametros_servidor.get("JANELA", 5))
    modo_confirmado = parametros_servidor.get("MODO", modo)
    confirmacao_confirmada = parametros_servidor.get("CONF", confirmacao)
    tamanho_maximo_confirmado = int(parametros_servidor.get("MAXMSG", tamanho_maximo_mensagem))

    print("[*] Parametros confirmados pelo servidor:")
    print(f"    Janela de recepcao      : {tamanho_janela}")
    print(f"    Modo de operacao        : {modo_confirmado}")
    print(f"    Tipo de confirmacao     : {confirmacao_confirmada}")
    print(f"    Tamanho maximo mensagem : {tamanho_maximo_confirmado}\n")

    mensagem = input(f"Digite a mensagem a ser enviada (minimo {tamanho_maximo_confirmado} caracteres): ")
    while len(mensagem) < tamanho_maximo_confirmado:
        print(f"[!] Mensagem muito curta ({len(mensagem)} caracteres). Tente novamente.")
        mensagem = input(f"Digite a mensagem a ser enviada (minimo {tamanho_maximo_confirmado} caracteres): ")

    blocos = [mensagem[i:i + TAMANHO_BLOCO] for i in range(0, len(mensagem), TAMANHO_BLOCO)]
    print(f"[*] Mensagem fatiada em {len(blocos)} blocos.\n")

    cliente.settimeout(TIMEOUT_ACK)
    if modo_confirmado == MODO_INDIVIDUAL:
        enviar_mensagem_individual(cliente, blocos)
    else:
        enviar_mensagem_em_lote(cliente, blocos, tamanho_janela, confirmacao_confirmada)

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
    print("[*] Conexao encerrada pelo cliente.")


if __name__ == "__main__":
    iniciar_cliente()