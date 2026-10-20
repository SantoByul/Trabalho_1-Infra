import struct
import socket

#definiçao flag controle
FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_FIN = 0x04
FLAG_DATA = 0x08

#chave secreta usada por cliente e servidor
CHAVE_CRIPTOGRAFIA = "REDES"

#Ponto extra: algoritimo de integridade(checksum internet)
def calcular_checksum(dados: bytes) -> int:
    # O checksum processa os dados em bloco de 16 bits
    if len(dados) % 2 != 0:
        dados += b"\x00"
    soma = 0

    #avanca de 2 em 2 bytes
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i + 1]
        soma += palavra
        soma = (soma & 0xFFFF) + (soma >> 16)
    return ~soma & 0xFFFF


#Ponto extra: criptografia simetrica hands-on
def cifrar_vigenere(texto: str, chave: str = CHAVE_CRIPTOGRAFIA) -> str:
    resultado = []

    # percorre cada caractere da string junto com o indice i
    for i, char in enumerate(texto):
        deslocamento = ord(chave[i % len(chave)])  # descobre o valor de ASCII
        char_cifrado = chr((ord(char) + deslocamento) % 256)
        resultado.append(char_cifrado)

    # junta todos os caracteres transformados em uma unica string cifrada
    return "".join(resultado)


def decifrar_vigenere(texto_cifrado: str, chave: str = CHAVE_CRIPTOGRAFIA) -> str:
    # decifra o texto revertendo a operaçao matematica do deslocamento feito na cifragem
    resultado = []

    for i, char in enumerate(texto_cifrado):
        deslocamento = ord(chave[i % len(chave)])
        # subtrai o deslocamento para voltar ao caractere ASCII original.
        char_decifrado = chr((ord(char) - deslocamento) % 256)
        resultado.append(char_decifrado)

    return "".join(resultado)

#montagem e estruturaçao do pacote de aplicaçao
# H = SeqNum, H = AckNum, B = Flags, H = Checksum, B = TamanhoPayload
FORMATO_CABECALHO = "!HHBHB"
TAMANHO_CABECALHO = struct.calcsize(FORMATO_CABECALHO)

#Cifra o payload, calcula o Checksum sobre a mensagem e gera o vetor de bytes final.
def criar_pacote(seq_num: int, ack_num: int, flags: int, payload_texto: str) -> bytes:
    payload_cifrado = cifrar_vigenere(payload_texto)
    payload_bytes = payload_cifrado.encode("latin1")
    tamanho_payload = len(payload_bytes) #guarda o tamanho real do payload no cabeçalho

    cabecalho_temp = struct.pack(
        FORMATO_CABECALHO, seq_num, ack_num, flags, 0, tamanho_payload
    )

    #Calcula o Checksum real sobre a junçao do cabeçalho temporário com os bytes do payload.
    checksum = calcular_checksum(cabecalho_temp + payload_bytes)

    cabecalho_final = struct.pack(
        FORMATO_CABECALHO, seq_num, ack_num, flags, checksum, tamanho_payload
    )
    return cabecalho_final + payload_bytes

#Recebe os bytes já lidos do Socket, extrai o cabeçalho, valida a integridade via Checksum e decifra o payload.
def desempacotar_pacote(dados_brutos: bytes):
#Verifcaçoes
    if len(dados_brutos) < TAMANHO_CABECALHO:
        return None

    cabecalho_bytes = dados_brutos[:TAMANHO_CABECALHO] #fatiamento
    payload_bytes = dados_brutos[TAMANHO_CABECALHO:]

    seq_num, ack_num, flags, checksum_recebido, tamanho_payload = struct.unpack(
        FORMATO_CABECALHO, cabecalho_bytes
    )

# Validação da Integridade: cria um cabeçalho com o campo Checksum valendo 0 para recalcular o Checksum localmente.
    cabecalho_validacao = struct.pack(
        FORMATO_CABECALHO, seq_num, ack_num, flags, 0, tamanho_payload
    )
    checksum_calculado = calcular_checksum(cabecalho_validacao + payload_bytes)

    is_valido = checksum_recebido == checksum_calculado

    # Decodifica os bytes do payload de volta para string e aplica a decifração do algoritmo de Vigenère.
    payload_cifrado = payload_bytes.decode("latin1")
    payload_original = decifrar_vigenere(payload_cifrado)

    return {
        "seq_num": seq_num,
        "ack_num": ack_num,
        "flags": flags,
        "checksum": checksum_recebido,
        "is_valido": is_valido,
        "payload": payload_original,
    }

#garante a leitura de exatamente "tamanho" bytes do socket, mesmo que o TCP entregue em partes
def _recv_exato(conn: socket.socket, tamanho: int):
    dados = b""
    while len(dados) < tamanho:
        parte = conn.recv(tamanho - len(dados))
        if not parte:
            return None
        dados += parte
    return dados

#monta o pacote completo: le primeiro o cabeçalho de tamanho fixo e depois o payload, usando o TamanhoPayload informado nele, evitando que dois pacotes se colem num unico recv
def receber_pacote(conn: socket.socket):
    cabecalho_bytes = _recv_exato(conn, TAMANHO_CABECALHO)
    if cabecalho_bytes is None:
        return None

    _, _, _, _, tamanho_payload = struct.unpack(FORMATO_CABECALHO, cabecalho_bytes)

    payload_bytes = b""
    if tamanho_payload > 0:
        payload_bytes = _recv_exato(conn, tamanho_payload)
        if payload_bytes is None:
            return None

    return desempacotar_pacote(cabecalho_bytes + payload_bytes)