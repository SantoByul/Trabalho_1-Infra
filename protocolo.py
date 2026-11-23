import struct
import socket

FLAG_SYN = 0x01
FLAG_ACK = 0x02
FLAG_FIN = 0x04
FLAG_DATA = 0x08
FLAG_NAK = 0x10

MODO_INDIVIDUAL = "INDIVIDUAL"
MODO_LOTE = "LOTE"

CONF_GBN = "GBN"
CONF_SR = "SR"

TAMANHO_MINIMO_MENSAGEM_PADRAO = 30
TAMANHO_JANELA_PADRAO = 5


def codificar_parametros(parametros: dict) -> str:
    return ";".join(f"{chave}={valor}" for chave, valor in parametros.items())


def decodificar_parametros(texto: str) -> dict:
    parametros = {}
    if not texto:
        return parametros
    for par in texto.split(";"):
        if "=" not in par:
            continue
        chave, valor = par.split("=", 1)
        parametros[chave] = valor
    return parametros


CHAVE_CRIPTOGRAFIA = "REDES"


def calcular_checksum(dados: bytes) -> int:
    if len(dados) % 2 != 0:
        dados += b"\x00"
    soma = 0
    for i in range(0, len(dados), 2):
        palavra = (dados[i] << 8) + dados[i + 1]
        soma += palavra
        soma = (soma & 0xFFFF) + (soma >> 16)
    return ~soma & 0xFFFF


def cifrar_vigenere(texto: str, chave: str = CHAVE_CRIPTOGRAFIA) -> str:
    resultado = []
    for i, char in enumerate(texto):
        deslocamento = ord(chave[i % len(chave)])
        char_cifrado = chr((ord(char) + deslocamento) % 256)
        resultado.append(char_cifrado)
    return "".join(resultado)


def decifrar_vigenere(texto_cifrado: str, chave: str = CHAVE_CRIPTOGRAFIA) -> str:
    resultado = []
    for i, char in enumerate(texto_cifrado):
        deslocamento = ord(chave[i % len(chave)])
        char_decifrado = chr((ord(char) - deslocamento) % 256)
        resultado.append(char_decifrado)
    return "".join(resultado)


FORMATO_CABECALHO = "!HHBHB"
TAMANHO_CABECALHO = struct.calcsize(FORMATO_CABECALHO)


def criar_pacote(seq_num: int, ack_num: int, flags: int, payload_texto: str) -> bytes:
    payload_cifrado = cifrar_vigenere(payload_texto)
    payload_bytes = payload_cifrado.encode("latin1")
    tamanho_payload = len(payload_bytes)

    cabecalho_temp = struct.pack(FORMATO_CABECALHO, seq_num, ack_num, flags, 0, tamanho_payload)
    checksum = calcular_checksum(cabecalho_temp + payload_bytes)
    cabecalho_final = struct.pack(FORMATO_CABECALHO, seq_num, ack_num, flags, checksum, tamanho_payload)
    return cabecalho_final + payload_bytes


def desempacotar_pacote(dados_brutos: bytes):
    if len(dados_brutos) < TAMANHO_CABECALHO:
        return None

    cabecalho_bytes = dados_brutos[:TAMANHO_CABECALHO]
    payload_bytes = dados_brutos[TAMANHO_CABECALHO:]

    seq_num, ack_num, flags, checksum_recebido, tamanho_payload = struct.unpack(FORMATO_CABECALHO, cabecalho_bytes)

    cabecalho_validacao = struct.pack(FORMATO_CABECALHO, seq_num, ack_num, flags, 0, tamanho_payload)
    checksum_calculado = calcular_checksum(cabecalho_validacao + payload_bytes)

    is_valido = checksum_recebido == checksum_calculado

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


def _recv_exato(conn: socket.socket, tamanho: int):
    dados = b""
    while len(dados) < tamanho:
        parte = conn.recv(tamanho - len(dados))
        if not parte:
            return None
        dados += parte
    return dados


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