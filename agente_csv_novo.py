import pandas as pd
import zipfile
import os
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Carrega as variáveis de ambiente -> Revisado ✓
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Erro: OPENAI_API_KEY não encontrada no arquivo .env")
    exit(1)

# Descompacta o arquivo ZIP -> Revisado ✓
zip_path = "202401_NFs.zip"
extract_path = "C:/Users/kelvi/AgenteCSV_Novo/extracted_files"
if not os.path.exists(extract_path):
    os.makedirs(extract_path)
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

# Carrega o CSV -> Revisado ✓
csv_file = None
for file in os.listdir(extract_path):
    if file.endswith(".csv"):
        csv_file = os.path.join(extract_path, file)
        break
if not csv_file:
    print("Nenhum arquivo CSV encontrado no ZIP")
    exit(1)
df = pd.read_csv(csv_file)

# Calcula o fornecedor com maior valor -> Revisado ✓
max_value = df.loc[df['VALOR NOTA FISCAL'].idxmax()]
print(f"O fornecedor com maior valor é {max_value['RAZÃO SOCIAL EMITENTE']} com {max_value['VALOR NOTA FISCAL']}")

# Configura o agente com ChatOpenAI -> Revisado ✓
llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key, temperature=0.7)
agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)

# Template para perguntas
prompt = PromptTemplate(input_variables=["question"], template="Responda: {question} usando os dados do CSV")

# Perguntas padrão
perguntas_padrao = [
    "Qual é o fornecedor com maior valor?",
    "Qual o total de notas fiscais?",
    "Qual é a média do valor das notas fiscais?",
    "Quais são os 3 fornecedores com maior valor?"
]

# Executa as perguntas padrão
for question in perguntas_padrao:
    query = prompt.format(question=question)
    try:
        response = agent.invoke({"input": query})
        print(f"Resposta para '{question}': {response}")
    except Exception as e:
        print(f"Erro ao processar '{question}': {e}")

# Pergunta interativa -> Revisado ✓
try:
    user_question = input("Faça uma pergunta adicional (ex.: 'Qual o valor mínimo das notas fiscais?') ou pressione Enter para pular: ")
    if user_question:
        query = prompt.format(question=user_question)
        response = agent.invoke({"input": query})
        print(f"Resposta para '{user_question}': {response}")
except Exception as e:
    print(f"Erro ao processar a pergunta adicional: {e}")