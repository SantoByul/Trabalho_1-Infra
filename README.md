# Trabalho_1-Infra

Aplicação cliente-servidor desenvolvida em C para a disciplina de Infraestrutura de Redes. O objetivo do projeto é implementar na camada de aplicação, um protocolo de transporte confiável sobre sockets. A implementação será desenvolvida de forma incremental durante os checkpoints da atividade.

# Checkpoint 1 - Handshake e Sockets

Nesta primeira etapa, a aplicação implementa:

- Comunicação entre cliente e servidor utilizando sockets;
- Conexão através de `localhost`;
- Handshake inicial entre cliente e servidor;
- Definição do modo de operação;
- Definição do tamanho máximo da mensagem;
- Definição do tamanho da janela de recepção.

# Como executar

Compilação:

No terminal, dentro da pasta do projeto:

`gcc servidor.c -o servidor.exe -lws2_32`
`gcc cliente.c -o cliente.exe -lws2_32`

Execução:

Primeiro, execute o servidor:

`.\servidor.exe`

Em outro terminal, execute o cliente:

`.\cliente.exe`

O cliente deverá se conectar ao servidor através do endereço 127.0.0.1, utilizando a porta 8888.

# Tecnologias
- Linguagem C
- GCC
- Winsock2
- Windows 11
