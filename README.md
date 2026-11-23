# Trabalho_1-Infra

Aplicação cliente-servidor desenvolvida em Python para a disciplina de Infraestrutura de Redes. O objetivo do projeto é implementar na camada de aplicação um protocolo de transporte confiável (RDT) sobre sockets TCP, tratando corrupção, perda e entrega fora de ordem de mensagens. A implementação foi desenvolvida de forma incremental durante os checkpoints da atividade.

# Checkpoint 1 - Handshake e Sockets

Nesta primeira etapa, a aplicação implementa:

- Comunicação entre cliente e servidor utilizando sockets;
- Conexão através de `localhost`;
- Handshake inicial entre cliente e servidor;
- Definição do modo de operação;
- Definição do tamanho máximo da mensagem;
- Definição do tamanho da janela de recepção.

# Checkpoint 2 - Protocolo Sem Erros

Troca de mensagens completa entre cliente e servidor assumindo um canal sem erros: fatiamento da mensagem em blocos de 4 caracteres, envio em janela deslizante, confirmação cumulativa (Go-Back-N) e encerramento via FIN/ACK+FIN.

# Checkpoint 3 - Inserção de Erros e Perdas

Nesta etapa, o protocolo passou a cobrir todas as características de transporte confiável exigidas (soma de verificação, temporizador, número de sequência, reconhecimento positivo e negativo, janela com paralelismo), com a inserção determinística de falhas e a demonstração do comportamento correto de recuperação:

- **Reconhecimento negativo (NAK)**: o servidor responde com um pacote `NAK` explícito (em vez de apenas repetir o último ACK) quando detecta um pacote corrompido (checksum inválido) ou fora de ordem.
- **Go-Back-N vs. Repetição Seletiva**: o cliente escolhe no handshake qual confirmação será usada. Em GBN, um NAK volta a janela inteira a partir do ponto indicado. Em Repetição Seletiva, pacotes fora de ordem são bufferizados pelo servidor e confirmados individualmente, e um NAK retransmite apenas o pacote específico.
- **Envio individual vs. em lote**: o cliente também escolhe no handshake entre enviar os pacotes um a um (aguardando confirmação de cada) ou em janela (múltiplos pacotes em paralelo).
- **Injeção determinística de falhas**: antes do envio, o cliente informa quais `SeqNum` deseja simular como corrompidos (um bit é invertido no pacote já pronto) ou como perdidos (o pacote simplesmente não é enviado nessa tentativa). A falha é sempre decidida do lado cliente e detectada/tratada pelo servidor.
- **Robustez no encerramento (FIN)**: o servidor não fecha a conexão imediatamente após confirmar o FIN; ele aguarda por um curto intervalo um possível reenvio do FIN (caso o ACK+FIN tenha se perdido ou corrompido no caminho) antes de encerrar, evitando que o cliente receba um erro de conexão ao tentar retransmitir.

## Especificação do protocolo de aplicação

### Formato do pacote

Cada pacote é composto por um cabeçalho de tamanho fixo seguido do payload cifrado:

| Campo          | Tamanho | Descrição                                            |
|----------------|---------|-------------------------------------------------------|
| SeqNum         | 2 bytes | Número de sequência do pacote                         |
| AckNum         | 2 bytes | Número de sequência confirmado/referenciado           |
| Flags          | 1 byte  | Combinação de flags de controle (ver abaixo)          |
| Checksum       | 2 bytes | Checksum (algoritmo internet, calculado à mão)        |
| TamanhoPayload | 1 byte  | Tamanho do payload em bytes                           |
| Payload        | N bytes | Dado da aplicação, cifrado com Vigenère (até 4 chars em pacotes de dados) |

### Flags

| Flag      | Valor | Significado                                   |
|-----------|-------|------------------------------------------------|
| `SYN`     | 0x01  | Início de conexão / handshake                  |
| `ACK`     | 0x02  | Reconhecimento positivo                        |
| `FIN`     | 0x04  | Sinal de encerramento da conexão               |
| `DATA`    | 0x08  | (reservado para dados, uso informativo)        |
| `NAK`     | 0x10  | Reconhecimento negativo (erro detectado)       |

### Handshake

1. Cliente → Servidor: `SYN` com payload `MODO=<LOTE|INDIVIDUAL>;CONF=<GBN|SR>;MAXMSG=<n>`.
2. Servidor → Cliente: `SYN+ACK` com payload `JANELA=<1..5>;MODO=...;CONF=...;MAXMSG=...` confirmando os parâmetros negociados.

### Transferência de dados

- Cada bloco de até 4 caracteres é enviado como um pacote com flag `ACK` e seu `SeqNum`.
- O servidor responde com `ACK` (dado aceito), `NAK` (dado corrompido ou fora de ordem, em GBN) ou um `ACK` individual bufferizando o dado (fora de ordem, em SR).
- Em caso de timeout do lado do cliente, os pacotes ainda não confirmados são retransmitidos (toda a janela em GBN; apenas os pendentes em SR).

### Encerramento

1. Cliente → Servidor: `FIN` com `SeqNum` igual ao total de blocos enviados.
2. Servidor → Cliente: `ACK+FIN`. O servidor aguarda brevemente por um FIN repetido (caso sua confirmação se perca) antes de fechar a conexão.

# Como executar

Pré-requisito: Python 3.

No terminal, dentro da pasta do projeto, execute primeiro o servidor:

`python server.py`

Em outro terminal, execute o cliente:

`python cliente.py`

O cliente se conecta ao servidor através do endereço `127.0.0.1`, na porta `50000`.

# Pontos extras implementados

- **Checksum (integridade)**: implementado manualmente em `protocolo.py` (algoritmo internet checksum), sem uso de bibliotecas prontas.
- **Criptografia simétrica**: cifra de Vigenère implementada manualmente em `protocolo.py`, usada para cifrar/decifrar o payload de cada pacote.

# Tecnologias
- Linguagem Python
- Sockets (TCP)
