## Requisitos
- Python 3.7 ou superior
- Dependências:

- Arquivo `.env` com a chave `OPENAI_API_KEY` (exemplo: `OPENAI_API_KEY=sua_chave_aqui`).
- Arquivo ZIP `202401_NFs.zip` contendo o CSV `202401_NFs_Cabecalho.csv`.

## Instalação
1. Clone o repositório ou baixe os arquivos para `C:\Users\kelvi\AgenteCSV_Novo`:

2. 2. Instale as dependências:
  
   3. (Nota: Crie um arquivo `requirements.txt` com as dependências acima se ainda não tiver.)
3. Configure o arquivo `.env` com sua chave da API OpenAI.

## Uso
### Via Interface Gráfica
1. Navegue até o diretório:

2. cd C:\Users\kelvi\AgenteCSV_Novo

2. Execute o script:

3. Clique nos botões para perguntas padrão ou use o campo "Enviar" para perguntas customizadas. A mensagem inicial "Olá, Eu sou o agente criado pelo Grupo 281 para Análise de notas fiscais" será exibida.

### Via Terminal
1. Execute o script:

2. python agente_chat_interface_pro.py


2. Digite uma pergunta (ex.: "Qual o total de notas fiscais?") e pressione Enter. Digite "sair" para encerrar.

## Estrutura do Projeto
- `agente_chat_interface_pro.py`: Interface gráfica com botões, entrada de texto e suporte a terminal.
- `agente_csv_novo.py`: Script original para análise direta do CSV (opcional, mantido como backup).
- `202401_NFs.zip`: Arquivo ZIP com os dados das notas fiscais.
- `.env`: Arquivo de configuração com a chave da API.
- `README.md`: Este arquivo de documentação.

## Limitações
- A entrega foi realizada de forma tardia devido a problemas de configuração e prazo apertado.
- A quota da API da OpenAI pode ser excedida, resultando no uso de um modo local com respostas predefinidas.
- A interface depende de uma conexão estável com a internet para a API.

## Contribuição
Desenvolvido por:GRUPO 281 DO CURSO AGENTES AUTONOMOS DE IA DE i2a2.academy  
Data: 25/06/2025  
Repositório: [https://github.com/kelvinjedidias2/AGENTE_CSV_GRUPO_281](https://github.com/kelvinjedidias2/AGENTE_CSV_GRUPO_281)

## Agradecimentos
Agradeço à i2a2.academy pelo suporte e oportunidade de aprendizado.
