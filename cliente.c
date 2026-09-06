#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#include <stdio.h>
#include <stdlib.h>

#define TAMANHO_BUFFER 1024
#define PORTA "8888"
#define IP_SERVIDOR "127.0.0.1"

int main(int argc, char**argv){
    WSADATA wsaData; // Variavel do winsock
    int iResult; // Variavel de status
    
    SOCKET ConnectSocket = INVALID_SOCKET; // Socket de conexão do cliente

    //estrutura de endereço
    struct addrinfo *result = NULL,
                    *ptr = NULL,
                    hints;
    //buffers de recepção e envio
    char sendbuf[TAMANHO_BUFFER];
    char recvbuf[TAMANHO_BUFFER];
    int recvbuflen = TAMANHO_BUFFER; //Comprimento do buffer de recepção

    //inicializa o winsock
    iResult = WSAStartup(MAKEWORD(2,2), &wsaData);
    if (iResult !=0) {
        printf("WSAStartup falhou com erro: %d\n", iResult);
        system("pause");
        return 1;
    }

    //pega informações da máquina
    char hostname[NI_MAXHOST];
    gethostname(hostname,NI_MAXHOST);
    printf("===============\nCliente: Nome: %s\n", hostname);

    //pega o ip da máquina e exibe
    PHOSTENT phe = gethostbyname(hostname);
    int i;
    for(i=0; phe->h_addr_list[i]; i++){
        struct in_addr addr;
        memcpy(&addr, phe->h_addr_list[i], sizeof(struct in_addr));
        printf("\nCliente: IP: %s", inet_ntoa(addr));
    }

    //inicializa o tipo de conexão
    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_INET; // IPv4
    hints.ai_socktype = SOCK_STREAM; // TCP
    hints.ai_protocol = IPPROTO_TCP; // Protocolo TCP

    //resolve o endereço e porta do servidor
    iResult= getaddrinfo(IP_SERVIDOR, PORTA, &hints, &result);
    if (iResult !=0){
        printf("getaddrinfo falhou com o erro: %d\n", iResult);
        WSACleanup();
        system("pause");
        return 1;
    }

    // tenta conectar no endereço do servidor
    printf("===============\nTentando se conectar no servidor de endereço %s na porta %s...\n", IP_SERVIDOR, PORTA);
    for(ptr=result; ptr!=NULL; ptr=ptr->ai_next){

        //cria um socket para conectar no servidor
        ConnectSocket =socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol);
        if(ConnectSocket==INVALID_SOCKET){
            printf("Socket falhou com o erro: %ld\n", WSAGetLastError());
            WSACleanup();
            system("pause");
            return 1;
        }

        //tenta conectar ao servidor
        iResult = connect(ConnectSocket, ptr->ai_addr, (int)ptr->ai_addrlen);
        if (iResult==SOCKET_ERROR){
            closesocket(ConnectSocket);
            ConnectSocket = INVALID_SOCKET;
            continue;
        }
        break;

    }

    freeaddrinfo(result);

    if(ConnectSocket==INVALID_SOCKET){
        printf("Não foi possível conectar ao servidor!\n");
        system("pause");
        WSACleanup();
        return 1;
    }

    i=0;

    strcpy(sendbuf, "MODE=GBN;MAX=30");

    iResult = send(ConnectSocket, sendbuf, (int)strlen(sendbuf), 0);
    
    int janela;
    iResult = recv(ConnectSocket, recvbuf, recvbuflen, 0);

    if (iResult > 0) {
        recvbuf[iResult] = '\0';
        printf("Resposta do servidor: \"%s\"\n", recvbuf);
        sscanf(recvbuf, "WINDOW=%d", &janela);
        printf("Janela recebida: %d\n", janela);
    }

    //encerra a conexão
    //iResult=shutdown(ConnectSocket,SD_SEND);
    //if (iResult == SOCKET_ERROR){
    //    printf("Falhou encerrar conexão com erro: %d\n", WSAGetLastError);
    //    closesocket(ConnectSocket);
    //    WSACleanup();
    //    system("pause");
    //    return 1;
    //}

    //cleanup
    printf("Encerrando o socket...");
    closesocket(ConnectSocket);
    WSACleanup();

    system("pause");
    return 0;
}