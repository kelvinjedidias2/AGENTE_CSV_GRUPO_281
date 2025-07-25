import pandas as pd
import zipfile
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog, ttk
import threading
from openai import OpenAI
from datetime import datetime
import chardet
import numpy as np
import logging
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from pandastable import Table

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nf_agent_gui.log'),
        logging.StreamHandler()
    ]
)

class NFExpertGUI:
    def __init__(self, root):
        self.root = root
        self.dataframes = {}
        self.current_file = None
        self.client = None
        self.column_stats = {}
        self.setup_ui()
        self.load_config()
        self.setup_analytics()
        self.show_welcome_message()
        
    def setup_ui(self):
        """Configura a interface gráfica principal"""
        self.root.title("Sistema Especialista em Notas Fiscais - Grupo 281")
        self.root.geometry("1400x900")
        self.root.state('zoomed')  # Maximiza a janela
        
        # Configuração do tema
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#f0f2f5')
        self.style.configure('TLabel', background='#f0f2f5', font=('Segoe UI', 9))
        self.style.configure('TButton', font=('Segoe UI', 9))
        self.style.configure('TNotebook', background='#f0f2f5')
        self.style.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'))
        
        # Layout principal
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        
        # Painel esquerdo (Dados e Análise)
        left_pane = ttk.PanedWindow(self.main_pane, orient=tk.VERTICAL)
        self.main_pane.add(left_pane)
        
        # Painel direito (Chat e Visualização)
        right_pane = ttk.PanedWindow(self.main_pane, orient=tk.VERTICAL)
        self.main_pane.add(right_pane)
        
        # Configuração dos painéis
        self.setup_file_panel(left_pane)
        self.setup_data_panel(left_pane)
        self.setup_analysis_panel(left_pane)
        self.setup_chat_panel(right_pane)
        self.setup_visualization_panel(right_pane)
        
        # Barra de status
        self.status_var = tk.StringVar(value="🟢 Pronto")
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(status_bar, textvariable=self.status_var, anchor=tk.W).pack(side=tk.LEFT)
        
        # Configuração de atalhos
        self.root.bind('<Control-o>', lambda e: self.load_file())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        
    def setup_file_panel(self, parent):
        """Painel de gerenciamento de arquivos"""
        file_frame = ttk.LabelFrame(parent, text="📁 Gerenciamento de Arquivos", padding=10)
        parent.add(file_frame)
        
        # Barra de ferramentas
        toolbar = ttk.Frame(file_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="Carregar", command=self.load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Remover", command=self.delete_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Exportar", command=self.export_data).pack(side=tk.LEFT, padx=2)
        
        # Lista de arquivos
        self.file_tree = ttk.Treeview(file_frame, columns=('size', 'rows', 'cols'), show='headings', height=6)
        self.file_tree.heading('#0', text='Arquivo')
        self.file_tree.heading('size', text='Tamanho')
        self.file_tree.heading('rows', text='Registros')
        self.file_tree.heading('cols', text='Colunas')
        
        vsb = ttk.Scrollbar(file_frame, orient="vertical", command=self.file_tree.yview)
        hsb = ttk.Scrollbar(file_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.file_tree.bind('<<TreeviewSelect>>', self.select_file)
        
    def setup_data_panel(self, parent):
        """Painel de visualização de dados"""
        data_frame = ttk.LabelFrame(parent, text="📊 Visualização de Dados", padding=10)
        parent.add(data_frame, weight=2)
        
        # Notebook para múltiplas abas
        self.data_notebook = ttk.Notebook(data_frame)
        self.data_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Aba de tabela
        self.table_frame = ttk.Frame(self.data_notebook)
        self.data_notebook.add(self.table_frame, text='Tabela')
        
        # Usando pandastable para visualização avançada
        self.table = Table(self.table_frame, showstatusbar=True)
        self.table.show()
        
        # Aba de metadados
        self.metadata_frame = ttk.Frame(self.data_notebook)
        self.data_notebook.add(self.metadata_frame, text='Metadados')
        
        self.metadata_text = scrolledtext.ScrolledText(
            self.metadata_frame, wrap=tk.WORD, font=('Consolas', 9)
        )
        self.metadata_text.pack(fill=tk.BOTH, expand=True)
        
    def setup_analysis_panel(self, parent):
        """Painel de análise rápida"""
        analysis_frame = ttk.LabelFrame(parent, text="🔍 Análise Rápida", padding=10)
        parent.add(analysis_frame)
        
        # Botões de análise
        buttons = [
            ("Top Fornecedores", self.analyze_top_suppliers),
            ("Total de NFs", self.count_invoices),
            ("Valor Médio", self.calculate_mean_value),
            ("Distribuição", self.analyze_temporal_dist),
            ("Estatísticas", self.show_stats)
        ]
        
        for text, cmd in buttons:
            ttk.Button(analysis_frame, text=text, command=cmd).pack(fill=tk.X, pady=2)
        
    def setup_chat_panel(self, parent):
        """Painel de interação por chat"""
        chat_frame = ttk.LabelFrame(parent, text="💬 Consulta ao Especialista", padding=10)
        parent.add(chat_frame, weight=1)
        
        # Área de chat
        self.chat_area = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=('Segoe UI', 10)
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        # Configuração de tags para formatação
        self.chat_area.tag_config('user', foreground='#1a73e8')
        self.chat_area.tag_config('agent', foreground='#0d652d')
        self.chat_area.tag_config('error', foreground='#d93025')
        self.chat_area.tag_config('system', foreground='#5f6368')
        
        # Frame de entrada
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.user_input = ttk.Entry(input_frame, font=('Segoe UI', 10))
        self.user_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.user_input.bind('<Return>', lambda e: self.send_question())
        
        ttk.Button(input_frame, text="Enviar", command=self.send_question).pack(side=tk.RIGHT)
        
    def setup_visualization_panel(self, parent):
        """Painel de visualização gráfica"""
        viz_frame = ttk.LabelFrame(parent, text="📈 Visualização Gráfica", padding=10)
        parent.add(viz_frame, weight=1)
        
        # Notebook para gráficos
        self.viz_notebook = ttk.Notebook(viz_frame)
        self.viz_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Abas de gráficos
        self.plot_frame = ttk.Frame(self.viz_notebook)
        self.viz_notebook.add(self.plot_frame, text='Gráficos')
        
        # Canvas para matplotlib
        self.figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def load_config(self):
        """Carrega configurações do ambiente"""
        try:
            load_dotenv()
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY não encontrada no .env")
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            messagebox.showerror("Erro de Configuração", f"Falha na configuração: {str(e)}")
            self.root.quit()
    
    def setup_analytics(self):
        """Configura perguntas e análises pré-definidas"""
        self.predefined_questions = {
            'Maior Fornecedor': "Qual é o fornecedor com maior valor total nas notas fiscais?",
            'Total NFs': "Quantas notas fiscais existem no total?",
            'Valor Médio': "Qual é o valor médio das notas fiscais?",
            'Top 3 Fornecedores': "Quais são os 3 fornecedores com maior valor total?",
            'Distribuição Temporal': "Qual é a distribuição temporal das notas fiscais?"
        }
    
    def show_welcome_message(self):
        """Exibe mensagem de boas-vindas"""
        welcome_msg = """
╔══════════════════════════════════════════════╗
║   SISTEMA ESPECIALISTA EM NOTAS FISCAIS      ║
║               GRUPO 281                      ║
╚══════════════════════════════════════════════╝

• Carregue arquivos ZIP ou CSV com dados de NFe
• Utilize as ferramentas de análise rápida
• Consulte o especialista para perguntas complexas
• Visualize os dados em tabelas e gráficos

Dica: Você pode arrastar e soltar arquivos na janela!
"""
        self.add_message("Sistema", welcome_msg.strip(), 'system')
    
    def load_file(self, file_path=None):
        """Carrega arquivo ZIP ou CSV"""
        if not file_path:
            file_path = filedialog.askopenfilename(
                title="Selecione um arquivo",
                filetypes=[("Arquivos CSV/ZIP", "*.csv;*.zip"), ("Todos os arquivos", "*.*")]
            )
            if not file_path:
                return
        
        try:
            self.status_var.set("🔄 Carregando arquivo...")
            self.root.update()
            
            temp_dir = None
            if file_path.endswith('.zip'):
                temp_dir = self._extract_zip(file_path)
                csv_files = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
                if not csv_files:
                    messagebox.showerror("Erro", "Nenhum arquivo CSV encontrado no ZIP")
                    return
                file_path = os.path.join(temp_dir, csv_files[0])
            
            encoding = self.detect_encoding(file_path)
            df = self._read_csv_with_fallback(file_path, encoding)
            
            filename = os.path.basename(file_path)
            self.dataframes[filename] = df
            self._update_column_stats(filename, df)
            
            if not self.current_file:
                self.current_file = filename
            
            self.update_file_list()
            self.show_data()
            self.add_message("Sistema", f"Arquivo carregado: {filename} ({len(df):,} registros)", 'system')
            
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar arquivo:\n{str(e)}")
            logging.error(f"Erro ao carregar arquivo: {str(e)}")
        finally:
            if temp_dir and os.path.exists(temp_dir):
                self._cleanup_temp_dir(temp_dir)
            self.status_var.set("🟢 Pronto")
    
    def _extract_zip(self, zip_path):
        """Extrai arquivo ZIP para diretório temporário"""
        extract_path = f"temp_extract_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(extract_path, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return extract_path
    
    def detect_encoding(self, file_path):
        """Detecta a codificação do arquivo"""
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read(10000))
        return result['encoding']
    
    def _read_csv_with_fallback(self, file_path, encoding):
        """Tenta ler CSV com diferentes abordagens"""
        try:
            return pd.read_csv(file_path, encoding=encoding, low_memory=False)
        except Exception as e:
            logging.warning(f"Falha ao ler CSV, tentando abordagem alternativa: {str(e)}")
            return pd.read_csv(file_path, encoding=encoding, error_bad_lines=False)
    
    def _cleanup_temp_dir(self, temp_dir):
        """Remove diretório temporário"""
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
    
    def _update_column_stats(self, filename, df):
        """Atualiza estatísticas das colunas"""
        self.column_stats[filename] = {
            'numeric_cols': df.select_dtypes(include=np.number).columns.tolist(),
            'text_cols': df.select_dtypes(include='object').columns.tolist(),
            'date_cols': df.select_dtypes(include='datetime').columns.tolist(),
            'shape': df.shape
        }
    
    def update_file_list(self):
        """Atualiza a lista de arquivos na interface"""
        self.file_tree.delete(*self.file_tree.get_children())
        for filename, df in self.dataframes.items():
            self.file_tree.insert('', 'end', text=filename, 
                                 values=(f"{os.path.getsize(filename)/1024:.1f} KB" if os.path.exists(filename) else 'N/A',
                                 len(df), len(df.columns)))
    
    def select_file(self, event):
        """Seleciona arquivo para visualização"""
        selection = self.file_tree.selection()
        if selection:
            filename = self.file_tree.item(selection[0], 'text')
            if filename in self.dataframes:
                self.current_file = filename
                self.show_data()
                self.add_message("Sistema", f"Arquivo selecionado: {filename}", 'system')
    
    def show_data(self):
        """Exibe os dados do arquivo selecionado"""
        if self.current_file and self.current_file in self.dataframes:
            df = self.dataframes[self.current_file]
            
            # Atualiza tabela
            self.table.model.df = df
            self.table.redraw()
            
            # Atualiza metadados
            self.metadata_text.config(state=tk.NORMAL)
            self.metadata_text.delete(1.0, tk.END)
            
            metadata = f"""=== METADADOS DO ARQUIVO ===
Arquivo: {self.current_file}
Registros: {len(df):,}
Colunas: {len(df.columns)}

=== TIPOS DE DADOS ===
{df.dtypes.to_string()}

=== COLUNAS NUMÉRICAS ===
{', '.join(self.column_stats[self.current_file]['numeric_cols'])}

=== COLUNAS DE TEXTO ===
{', '.join(self.column_stats[self.current_file]['text_cols'])}

=== ESTATÍSTICAS ===
{df.describe().to_string()}
"""
            self.metadata_text.insert(tk.END, metadata)
            self.metadata_text.config(state=tk.DISABLED)
            
            # Atualiza visualização gráfica
            self.update_visualizations(df)
    
    def update_visualizations(self, df):
        """Atualiza os gráficos com os dados atuais"""
        self.figure.clear()
        
        # Gráfico de valores (se existir coluna numérica)
        numeric_cols = self.column_stats[self.current_file]['numeric_cols']
        if numeric_cols:
            ax1 = self.figure.add_subplot(211)
            try:
                df[numeric_cols[0]].plot(kind='hist', ax=ax1, bins=20)
                ax1.set_title(f'Distribuição de {numeric_cols[0]}')
                ax1.grid(True)
            except:
                pass
        
        # Gráfico de fornecedores (se existir)
        if 'fornecedor' in df.columns:
            ax2 = self.figure.add_subplot(212)
            try:
                top_suppliers = df['fornecedor'].value_counts().head(5)
                top_suppliers.plot(kind='bar', ax=ax2)
                ax2.set_title('Top 5 Fornecedores (Frequência)')
                ax2.grid(True)
            except:
                pass
        
        self.canvas.draw()
    
    def delete_file(self):
        """Remove arquivo selecionado"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Nenhum arquivo selecionado")
            return
            
        filename = self.file_tree.item(selection[0], 'text')
        if filename in self.dataframes:
            if messagebox.askyesno("Confirmar", f"Remover arquivo {filename}?"):
                del self.dataframes[filename]
                
                if self.current_file == filename:
                    self.current_file = None
                    self.table.model.df = pd.DataFrame()
                    self.table.redraw()
                    self.metadata_text.config(state=tk.NORMAL)
                    self.metadata_text.delete(1.0, tk.END)
                    self.metadata_text.config(state=tk.DISABLED)
                    self.figure.clear()
                    self.canvas.draw()
                
                self.update_file_list()
                self.add_message("Sistema", f"Arquivo removido: {filename}", 'system')
    
    def export_data(self):
        """Exporta dados consolidados"""
        if not self.dataframes:
            messagebox.showwarning("Aviso", "Nenhum dado para exportar")
            return
        
        try:
            combined_df = pd.concat(self.dataframes.values(), ignore_index=True)
            export_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                title="Salvar análise consolidada"
            )
            
            if export_path:
                if export_path.endswith('.xlsx'):
                    combined_df.to_excel(export_path, index=False)
                else:
                    combined_df.to_csv(export_path, index=False)
                
                self.add_message("Sistema", f"Dados exportados para {export_path}", 'system')
                messagebox.showinfo("Sucesso", "Dados exportados com sucesso!")
        
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar dados:\n{str(e)}")
            logging.error(f"Erro ao exportar dados: {str(e)}")
    
    def send_question(self):
        """Envia pergunta para análise"""
        question = self.user_input.get().strip()
        if question:
            self.user_input.delete(0, tk.END)
            self.ask_question(question)
    
    def ask_question(self, question):
        """Processa pergunta com análise local ou API"""
        if not self.dataframes:
            self.add_message("Erro", "Nenhum dado carregado", 'error')
            return
        
        self.add_message("Você", question, 'user')
        
        # Verifica se é uma pergunta pré-definida
        for q_text, q_content in self.predefined_questions.items():
            if question.lower() == q_text.lower() or question.lower() == q_content.lower():
                self.answer_predefined_question(q_text)
                return
        
        # Se não for pré-definida, usa API
        threading.Thread(
            target=self.process_question_with_api,
            args=(question,),
            daemon=True
        ).start()
    
    def answer_predefined_question(self, question_key):
        """Responde perguntas pré-definidas com análise local"""
        try:
            if question_key == 'Maior Fornecedor':
                answer = self.analyze_top_suppliers(1)
            elif question_key == 'Total NFs':
                answer = self.count_invoices()
            elif question_key == 'Valor Médio':
                answer = self.calculate_mean_value()
            elif question_key == 'Top 3 Fornecedores':
                answer = self.analyze_top_suppliers(3)
            elif question_key == 'Distribuição Temporal':
                answer = self.analyze_temporal_dist()
            
            self.add_message("Agente", answer, 'agent')
        except Exception as e:
            self.add_message("Erro", f"Falha na análise: {str(e)}", 'error')
    
    def process_question_with_api(self, question):
        """Processa pergunta usando a API da OpenAI"""
        self.status_var.set("🔄 Consultando especialista...")
        
        try:
            # Combina amostras de todos os dataframes
            combined_sample = pd.concat(
                [df.sample(min(1000, len(df))) for df in self.dataframes.values()]
            )
            
            prompt = (
                "Você é um especialista em notas fiscais brasileiras (NF-e). "
                "Analise os dados e responda de forma técnica e precisa.\n\n"
                f"Dados (amostra representativa):\n{combined_sample.to_string()}\n\n"
                f"Pergunta: {question}\n\n"
                "Inclua insights relevantes sobre:"
                "\n- Relação entre fornecedores e valores"
                "\n- Padrões temporais"
                "\n- Anomalias potenciais"
                "\n- Conformidade com legislação brasileira"
            )
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "Você é um analista especialista em NF-e brasileiras."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            answer = response.choices[0].message.content
            self.add_message("Agente", answer, 'agent')
            
        except Exception as e:
            self.add_message("Erro", f"Falha na consulta: {str(e)}", 'error')
            logging.error(f"Erro na API: {str(e)}")
        finally:
            self.status_var.set("🟢 Pronto")
    
    def add_message(self, sender, message, tag=None):
        """Adiciona mensagem ao chat"""
        self.chat_area.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_area.insert(tk.END, f"[{timestamp}] {sender}:\n{message}\n\n", tag)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.see(tk.END)
    
    # Métodos de análise local
    def analyze_top_suppliers(self, top_n=3):
        """Analisa os maiores fornecedores"""
        try:
            combined_df = pd.concat(self.dataframes.values(), ignore_index=True)
            
            if 'fornecedor' not in combined_df.columns or 'valor' not in combined_df.columns:
                return "❌ Colunas 'fornecedor' ou 'valor' não encontradas nos dados"
            
            result = combined_df.groupby('fornecedor')['valor'].sum().nlargest(top_n)
            return f"🔝 Top {top_n} fornecedores por valor total:\n\n{result.to_string()}"
        
        except Exception as e:
            return f"❌ Erro na análise: {str(e)}"
    
    def count_invoices(self):
        """Conta o total de notas fiscais"""
        try:
            total = sum(len(df) for df in self.dataframes.values())
            return f"📊 Total de notas fiscais: {total:,}"
        except Exception as e:
            return f"❌ Erro na contagem: {str(e)}"
    
    def calculate_mean_value(self):
        """Calcula o valor médio das notas"""
        try:
            combined_df = pd.concat(self.dataframes.values(), ignore_index=True)
            
            if 'valor' not in combined_df.columns:
                return "❌ Coluna 'valor' não encontrada"
            
            mean_val = combined_df['valor'].mean()
            return f"💰 Valor médio das notas: R${mean_val:,.2f}"
        except Exception as e:
            return f"❌ Erro no cálculo: {str(e)}"
    
    def analyze_temporal_dist(self):
        """Analisa distribuição temporal"""
        try:
            combined_df = pd.concat(self.dataframes.values(), ignore_index=True)
            
            if 'data' not in combined_df.columns:
                return "❌ Coluna 'data' não encontrada"
            
            combined_df['data'] = pd.to_datetime(combined_df['data'])
            temporal = combined_df.resample('M', on='data').size()
            
            return f"📅 Distribuição temporal (mensal):\n\n{temporal.to_string()}"
        except Exception as e:
            return f"❌ Erro na análise temporal: {str(e)}"
    
    def show_stats(self):
        """Mostra estatísticas básicas"""
        try:
            combined_df = pd.concat(self.dataframes.values(), ignore_index=True)
            
            if 'valor' not in combined_df.columns:
                return "❌ Coluna 'valor' não encontrada"
            
            stats = combined_df['valor'].describe()
            return f"📈 Estatísticas dos valores:\n\n{stats.to_string()}"
        except Exception as e:
            return f"❌ Erro ao calcular estatísticas: {str(e)}"

if __name__ == "__main__":
    root = tk.Tk()
    app = NFExpertGUI(root)
    root.mainloop()