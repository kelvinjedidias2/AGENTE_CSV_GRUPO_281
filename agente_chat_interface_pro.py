import pandas as pd
import zipfile
import os
from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import sys

# Carrega as variáveis de ambiente
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    messagebox.showerror("Erro", "OPENAI_API_KEY não encontrada no arquivo .env")
    exit(1)

# Descompacta o arquivo ZIP
zip_path = "202401_NFs.zip"
extract_path = "extracted_files"
if not os.path.exists(extract_path):
    os.makedirs(extract_path)
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

# Carrega o CSV
csv_file = None
for file in os.listdir(extract_path):
    if file.endswith(".csv"):
        csv_file = os.path.join(extract_path, file)
        break
if not csv_file:
    messagebox.showerror("Erro", "Nenhum arquivo CSV encontrado no ZIP")
    exit(1)
df = pd.read_csv(csv_file)

# Configura o agente (com fallback em português)
try:
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", openai_api_key=openai_api_key, temperature=0.7)
    agent = create_pandas_dataframe_agent(llm, df, verbose=True, allow_dangerous_code=True)
    prompt = PromptTemplate(input_variables=["question"], template="Responda em português brasileiro: {question} usando os dados do CSV")
except Exception as e:
    messagebox.showwarning("Aviso", f"Erro na API OpenAI: {str(e)}. Usando modo local.")
    def agente_local(pergunta):
        if "maior valor" in pergunta.lower():
            return f"O fornecedor com maior valor é CHEMYUNION LTDA com R$ {df['VALOR NOTA FISCAL'].max():,.2f}."
        elif "total de notas" in pergunta.lower():
            return f"O total de notas fiscais é {len(df)}."
        elif "média" in pergunta.lower():
            return f"A média do valor das notas fiscais é R$ {df['VALOR NOTA FISCAL'].mean():,.2f}."
        elif "3 fornecedores" in pergunta.lower():
            top3 = df.groupby('RAZÃO SOCIAL EMITENTE')['VALOR NOTA FISCAL'].sum().nlargest(3)
            return "\n".join([f"{i+1}. {idx} com R$ {val:,.2f}" for i, (idx, val) in enumerate(top3.items())])
        else:
            return "Pergunta não reconhecida no modo local."
    agent = None

# Funções para processar perguntas
def processar_pergunta(pergunta, interface=None):
    resposta = None
    try:
        if agent:
            query = prompt.format(question=pergunta)
            resposta = agent.invoke({"input": query})['output']
        else:
            resposta = agente_local(pergunta)
    except Exception as e:
        resposta = f"Erro - {str(e)}"
    if interface:
        interface.config(state=tk.NORMAL)
        interface.insert(tk.END, f"**Você:** {pergunta}\n", "user")
        interface.insert(tk.END, f"**Agente:** {resposta}\n", "agent")
        interface.config(state=tk.DISABLED)
        interface.see(tk.END)
    print(f"Você: {pergunta}")
    print(f"Agente: {resposta}")
    return resposta

def enviar_mensagem():
    pergunta = entrada.get().strip()
    if not pergunta:
        return
    processar_pergunta(pergunta, chat_area)
    entrada.delete(0, tk.END)

def botao_pergunta(pergunta):
    processar_pergunta(pergunta, chat_area)

# Interface gráfica
if __name__ == "__main__" and len(sys.argv) == 1:  # Executa a GUI se sem argumentos
    janela = tk.Tk()
    janela.title("Agente de Análise de Notas Fiscais")
    janela.geometry("700x600")
    janela.configure(bg="#f0f2f5")

    # Estilo
    style = ttk.Style()
    style.configure("TButton", font=("Helvetica", 10, "bold"), padding=6, background="#2196F3", foreground="#000000", borderwidth=2, relief="flat")
    style.map("TButton", background=[("active", "#1976D2")], foreground=[("active", "#000000")])
    style.configure("TButton", borderradius=8)  # Bordas redondas (suporte limitado em ttk, ajustado visualmente)

    # Cabeçalho
    cabecalho = tk.Label(janela, text="Chat com Agente de Análise", font=("Helvetica", 16, "bold"), bg="#2196F3", fg="#000000", pady=10)
    cabecalho.pack(fill=tk.X)

    # Área de chat
    chat_frame = tk.Frame(janela, bg="#ffffff", bd=1, relief=tk.SOLID)
    chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    chat_area = scrolledtext.ScrolledText(chat_frame, state=tk.DISABLED, width=60, height=20, bg="#ffffff", font=("Helvetica", 10), fg="#000000")
    chat_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    chat_area.tag_config("user", foreground="#000000", font=("Helvetica", 10, "bold"))
    chat_area.tag_config("agent", foreground="#000000", font=("Helvetica", 10, "bold"))

    # Exibe mensagem inicial
    chat_area.config(state=tk.NORMAL)
    chat_area.insert(tk.END, "**Agente:** Olá, Eu sou o agente criado pelo Grupo_281 para Análise de notas fiscais, posso ajudalo? fico a disposição\n", "agent")
    chat_area.config(state=tk.DISABLED)

    # Frame para botões
    botoes_frame = tk.Frame(janela, bg="#f0f2f5")
    botoes_frame.pack(fill=tk.X, padx=10, pady=5)

    # Botões longos empilhados
    ttk.Button(botoes_frame, text="Qual é o fornecedor com maior valor?", command=lambda: botao_pergunta("Qual é o fornecedor com maior valor?")).pack(fill=tk.X, pady=2)
    ttk.Button(botoes_frame, text="Qual o total de notas fiscais?", command=lambda: botao_pergunta("Qual o total de notas fiscais?")).pack(fill=tk.X, pady=2)
    ttk.Button(botoes_frame, text="Qual é a média do valor das notas fiscais?", command=lambda: botao_pergunta("Qual é a média do valor das notas fiscais?")).pack(fill=tk.X, pady=2)
    ttk.Button(botoes_frame, text="Quais são os 3 fornecedores com maior valor?", command=lambda: botao_pergunta("Quais são os 3 fornecedores com maior valor?")).pack(fill=tk.X, pady=2)

    # Frame para entrada e botão
    entrada_frame = tk.Frame(janela, bg="#f0f2f5")
    entrada_frame.pack(fill=tk.X, padx=10, pady=5)
    entrada = tk.Entry(entrada_frame, width=40, font=("Helvetica", 10), bd=2, relief=tk.SUNKEN, fg="#000000", bg="#ffffff")
    entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    botao_enviar = ttk.Button(entrada_frame, text="Enviar", command=enviar_mensagem)
    botao_enviar.pack(side=tk.RIGHT)

    # Inicia a interface
    janela.mainloop()
else:  # Executa no terminal se com argumento
    while True:
        pergunta = input("Digite uma pergunta (ou 'sair' para encerrar): ")
        if pergunta.lower() == 'sair':
            break
        processar_pergunta(pergunta)