#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>

#define TAMANHO_BUFFER 1024
#define PORTA "8888"

int __cdecl main(void) {

    WSADATA wsaData; // Variavel do winsock
    int iResult; // Variavel de status

    //Sockets de conexão do servidor
    SOCKET ListenSocket = INVALID_SOCKET;
    SOCKET ClientSocket = INVALID_SOCKET;

    //estrutura de endereço
    struct addrinfo *result = NULL;
    struct addrinfo hints;

    //buffers de recepção e envio
    int iSendResult;
    char recvbuf[TAMANHO_BUFFER];
    char sendbuf[TAMANHO_BUFFER];
    int recvbuflen = TAMANHO_BUFFER;
    char modo[10];
    int maximo;
    int janela = 5;


    // Inicializar o Winsock
    iResult = WSAStartup(MAKEWORD(2, 2), &wsaData);
    if (iResult != 0) {
        printf("WSAStartup falhou com erro: %d\n", iResult);
        system("pause");
        return 1;
    }

    // pega informações da máquina
    char hostname[NI_MAXHOST];
    gethostname(hostname, NI_MAXHOST);
    printf("===============\nServidor: Nome: %s\n", hostname);

    //pega o ip da maquina e exibe
    PHOSTENT phe = gethostbyname(hostname);
    int i;
    for(i = 0; phe->h_addr_list[i] != 0; ++i) {
        struct in_addr addr;
        memcpy(&addr, phe->h_addr_list[i], sizeof(struct in_addr));
        printf("\nServidor: IP: %s", inet_ntoa(addr));
    }

    //zera a memoria e inicializa hints
    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET; // IPv4
    hints.ai_socktype = SOCK_STREAM; // TCP
    hints.ai_protocol = IPPROTO_TCP; // Protocolo TCP
    hints.ai_flags = AI_PASSIVE; // Usado para bind

    //resolve o endereço e a porta do servidor
    iResult = getaddrinfo(NULL, PORTA , &hints, &result);
    if (iResult != 0){
        printf("getaddrinfo falhou com erro: %d\n", iResult);
        WSACleanup();
        system("pause");
        return 1;
    }

    //cria um socket de conexão com o servidor
    ListenSocket = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
    if(ListenSocket == INVALID_SOCKET){
        printf("socket falhou com erro: %ld\n", WSAGetLastError());
        freeaddrinfo(result);
        WSACleanup();
        system("pause");
        return 1;
    }

    //associa o socket a porta e endereço do servidor
    iResult = bind(ListenSocket, result->ai_addr, (int)result->ai_addrlen);
    if (iResult == SOCKET_ERROR){
        printf("bind falhou com erro: %d\n", WSAGetLastError());
        freeaddrinfo(result);
        closesocket(ListenSocket);
        WSACleanup();
        system("pause");
        return 1;
    }

    freeaddrinfo(result);

    // Escuta aguardando um cliente
    printf("===============\nServidor: Aguardando um cliente na porta %s...\n", PORTA);
    iResult = listen(ListenSocket, SOMAXCONN);
    if (iResult == SOCKET_ERROR){
        printf("listen falhou com erro: %d\n", WSAGetLastError());
        closesocket(ListenSocket);
        WSACleanup();
        system("pause");
        return 1;
    }

    // Aceita o socket com o cliente
    ClientSocket = accept(ListenSocket, NULL, NULL);
    if (ClientSocket == INVALID_SOCKET){
        printf("accept falhou com erro: %d\n", WSAGetLastError());
        closesocket(ListenSocket);
        WSACleanup();
        system("pause");
        return 1;
    }

    iResult = recv(ClientSocket, recvbuf, recvbuflen, 0);
    if (iResult > 0) {
    recvbuf[iResult] = '\0';
    printf("Handshake recebido: %s\n", recvbuf);
    sscanf(recvbuf, "MODE=%[^;];MAX=%d", modo, &maximo);
    printf("Modo: %s\n", modo);
    printf("Tamanho máximo: %d\n", maximo);
    } 

    sprintf(sendbuf, "WINDOW=%d", janela);
    send(ClientSocket, sendbuf, (int)strlen(sendbuf), 0);

    closesocket(ListenSocket);

    do{
        iResult = recv(ClientSocket, recvbuf, recvbuflen, 0);
        if (iResult > 0){
            printf("Mensagem recebida: \"%.*s\"\n", iResult, recvbuf);
            
            //aqui entra o bloco de código que processa a mensagem recebida e envia uma resposta de volta pro cliente

        }else if (iResult ==0){
            printf("conexão encerrada....\n");
        } else{
            printf("recv falhou com erro: %d\n", WSAGetLastError());
            closesocket(ClientSocket);
            WSACleanup();
            system("pause");
            return 1;
        }
    } while (iResult > 0);

    // encerra a conexão
    iResult = shutdown(ClientSocket, SD_SEND);
    if (iResult == SOCKET_ERROR){
        printf("shutdown falhou com erro: %d\n", WSAGetLastError());
        closesocket(ClientSocket);
        WSACleanup();
        system("pause");
        return 1;
    }

    // cleanup
    printf("Encerrando socket...\n");
    closesocket(ClientSocket);
    WSACleanup();

    system("pause");
    return 0;
}