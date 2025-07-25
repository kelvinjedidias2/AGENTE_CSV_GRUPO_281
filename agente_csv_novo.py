import pandas as pd
import zipfile
import os
from dotenv import load_dotenv
from openai import OpenAI
import sys
from datetime import datetime
import chardet
from typing import Dict, List, Optional
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nf_agent.log'),
        logging.StreamHandler()
    ]
)

class NFExpertSystem:
    def __init__(self):
        self.dataframes: Dict[str, pd.DataFrame] = {}
        self.current_file: Optional[str] = None
        self.client: Optional[OpenAI] = None
        self.column_stats: Dict[str, Dict] = {}
        self.load_config()
        self.setup_analytics()
        
    def load_config(self) -> None:
        """Carrega configurações do ambiente e inicializa cliente OpenAI"""
        try:
            load_dotenv()
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY não encontrada no .env")
            self.client = OpenAI(api_key=self.api_key)
        except Exception as e:
            logging.error(f"Falha na configuração: {str(e)}")
            sys.exit(1)

    def setup_analytics(self) -> None:
        """Inicializa estruturas para análise de dados"""
        self.predefined_questions = {
            '1': {
                'question': "Qual é o fornecedor com maior valor total nas notas fiscais?",
                'analysis': self._analyze_top_suppliers
            },
            '2': {
                'question': "Quantas notas fiscais existem no total?",
                'analysis': self._count_invoices
            },
            '3': {
                'question': "Qual é o valor médio das notas fiscais?",
                'analysis': self._calculate_mean_value
            },
            '4': {
                'question': "Quais são os 3 fornecedores com maior valor total?",
                'analysis': self._analyze_top_suppliers
            },
            '5': {
                'question': "Qual é a distribuição temporal das notas fiscais?",
                'analysis': self._analyze_temporal_distribution
            }
        }

    def detect_encoding(self, file_path: str) -> str:
        """Detecta a codificação do arquivo"""
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read(10000))
        return result['encoding']

    def load_file(self, file_path: Optional[str] = None) -> bool:
        """Carrega arquivo ZIP ou CSV com tratamento robusto"""
        if not file_path:
            file_path = input("📂 Digite o caminho do arquivo (ZIP/CSV): ").strip()
        
        if not os.path.exists(file_path):
            logging.error(f"Arquivo não encontrado: {file_path}")
            return False

        try:
            temp_dir = None
            if file_path.endswith('.zip'):
                temp_dir = self._extract_zip(file_path)
                csv_files = [f for f in os.listdir(temp_dir) if f.endswith('.csv')]
                if not csv_files:
                    logging.error("Nenhum CSV encontrado no ZIP")
                    return False
                file_path = os.path.join(temp_dir, csv_files[0])

            encoding = self.detect_encoding(file_path)
            df = self._read_csv_with_fallback(file_path, encoding)
            
            filename = os.path.basename(file_path)
            self.dataframes[filename] = df
            self._update_column_stats(filename, df)
            
            if not self.current_file:
                self.current_file = filename
            
            logging.info(f"Arquivo carregado: {filename} ({len(df)} registros, {len(df.columns)} colunas)")
            return True

        except Exception as e:
            logging.error(f"Erro ao carregar arquivo: {str(e)}")
            return False
        finally:
            if temp_dir and os.path.exists(temp_dir):
                self._cleanup_temp_dir(temp_dir)

    def _extract_zip(self, zip_path: str) -> str:
        """Extrai arquivo ZIP para diretório temporário"""
        extract_path = f"temp_extract_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        os.makedirs(extract_path, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return extract_path

    def _read_csv_with_fallback(self, file_path: str, encoding: str) -> pd.DataFrame:
        """Tenta ler CSV com diferentes abordagens"""
        try:
            return pd.read_csv(file_path, encoding=encoding, low_memory=False)
        except Exception as e:
            logging.warning(f"Falha ao ler CSV, tentando abordagem alternativa: {str(e)}")
            return pd.read_csv(file_path, encoding=encoding, error_bad_lines=False)

    def _cleanup_temp_dir(self, temp_dir: str) -> None:
        """Remove diretório temporário"""
        for f in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)

    def _update_column_stats(self, filename: str, df: pd.DataFrame) -> None:
        """Atualiza estatísticas das colunas para análise"""
        self.column_stats[filename] = {
            'numeric_cols': df.select_dtypes(include=np.number).columns.tolist(),
            'text_cols': df.select_dtypes(include='object').columns.tolist(),
            'date_cols': df.select_dtypes(include='datetime').columns.tolist(),
            'shape': df.shape
        }

    def _analyze_all_files(self) -> pd.DataFrame:
        """Combina todos os dataframes para análise completa"""
        if not self.dataframes:
            raise ValueError("Nenhum dado carregado")
        return pd.concat(self.dataframes.values(), ignore_index=True)

    def _analyze_top_suppliers(self, top_n: int = 3) -> str:
        """Análise local dos maiores fornecedores"""
        try:
            combined_df = self._analyze_all_files()
            if 'fornecedor' not in combined_df.columns or 'valor' not in combined_df.columns:
                return "Colunas 'fornecedor' ou 'valor' não encontradas nos dados"
            
            result = combined_df.groupby('fornecedor')['valor'].sum().nlargest(top_n)
            return f"Top {top_n} fornecedores por valor total:\n{result.to_string()}"
        except Exception as e:
            return f"Erro na análise: {str(e)}"

    def _count_invoices(self) -> str:
        """Contagem total de notas fiscais"""
        try:
            total = sum(len(df) for df in self.dataframes.values())
            return f"Total de notas fiscais: {total:,}"
        except Exception as e:
            return f"Erro na contagem: {str(e)}"

    def _calculate_mean_value(self) -> str:
        """Cálculo do valor médio"""
        try:
            combined_df = self._analyze_all_files()
            if 'valor' not in combined_df.columns:
                return "Coluna 'valor' não encontrada"
            
            mean_val = combined_df['valor'].mean()
            return f"Valor médio das notas: R${mean_val:,.2f}"
        except Exception as e:
            return f"Erro no cálculo: {str(e)}"

    def _analyze_temporal_distribution(self) -> str:
        """Análise de distribuição temporal"""
        try:
            combined_df = self._analyze_all_files()
            if 'data' not in combined_df.columns:
                return "Coluna 'data' não encontrada"
            
            combined_df['data'] = pd.to_datetime(combined_df['data'])
            temporal = combined_df.resample('M', on='data').size()
            return f"Distribuição temporal:\n{temporal.to_string()}"
        except Exception as e:
            return f"Erro na análise temporal: {str(e)}"

    def ask_question(self, question: str) -> str:
        """Processa perguntas com análise local e consulta à API"""
        if not self.dataframes:
            return "❌ Erro: Nenhum dado carregado"
        
        # Tenta responder localmente primeiro
        if question.lower() in [q['question'].lower() for q in self.predefined_questions.values()]:
            for q in self.predefined_questions.values():
                if q['question'].lower() == question.lower():
                    try:
                        return q['analysis']()
                    except Exception as e:
                        logging.error(f"Erro na análise local: {str(e)}")
                        break
        
        # Se não for pergunta pré-definida ou falhar, usa API
        try:
            combined_sample = pd.concat(
                [df.sample(min(1000, len(df))) for df in self.dataframes.values()]
            ).to_string()
            
            prompt = (
                "Você é um especialista em notas fiscais brasileiras (NF-e). "
                "Analise os dados e responda de forma técnica e precisa.\n\n"
                f"Dados (amostra representativa):\n{combined_sample}\n\n"
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
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"❌ Erro na API: {str(e)}"

    def interactive_menu(self) -> None:
        """Menu interativo para o usuário"""
        while True:
            print("\n" + "="*60)
            print("SISTEMA ESPECIALISTA EM NOTAS FISCAIS - GRUPO 281".center(60))
            print("="*60)
            
            print("\n📂 ARQUIVOS CARREGADOS:")
            for i, filename in enumerate(self.dataframes.keys(), 1):
                print(f"{i}. {filename}{' (ATIVO)' if filename == self.current_file else ''}")
            
            print("\n🔍 MENU PRINCIPAL:")
            print("1. Carregar arquivo")
            print("2. Remover arquivo")
            print("3. Visualizar metadados")
            print("4. Perguntas pré-definidas")
            print("5. Pergunta personalizada")
            print("6. Exportar análise consolidada")
            print("7. Sair")
            
            choice = input("\n👉 Selecione uma opção: ").strip()
            
            if choice == '1':
                self.load_file()
            elif choice == '2':
                self._delete_file_interactive()
            elif choice == '3':
                self._show_metadata()
            elif choice == '4':
                self._predefined_questions_menu()
            elif choice == '5':
                self._custom_question()
            elif choice == '6':
                self._export_analysis()
            elif choice == '7':
                print("\n👋 Encerrando o sistema...")
                break
            else:
                print("❌ Opção inválida")

    def _delete_file_interactive(self) -> None:
        """Interface para remover arquivo"""
        filename = input("🗑️ Nome do arquivo a remover: ").strip()
        if filename in self.dataframes:
            del self.dataframes[filename]
            if self.current_file == filename:
                self.current_file = next(iter(self.dataframes.keys()), None)
            print(f"✅ Arquivo {filename} removido")
        else:
            print("⚠️ Arquivo não encontrado")

    def _show_metadata(self) -> None:
        """Exibe metadados dos arquivos carregados"""
        if not self.dataframes:
            print("❌ Nenhum arquivo carregado")
            return
        
        print("\n📊 METADADOS DOS ARQUIVOS:")
        for filename, df in self.dataframes.items():
            print(f"\n🔹 {filename}")
            print(f"  Registros: {len(df):,}")
            print(f"  Colunas: {len(df.columns)}")
            print("  Tipos de dados:")
            print(df.dtypes.to_string())

    def _predefined_questions_menu(self) -> None:
        """Menu de perguntas pré-definidas"""
        print("\n📊 PERGUNTAS PRÉ-DEFINIDAS:")
        for key, item in self.predefined_questions.items():
            print(f"{key}. {item['question']}")
        
        sub_choice = input("👉 Selecione uma pergunta: ").strip()
        if sub_choice in self.predefined_questions:
            answer = self.ask_question(self.predefined_questions[sub_choice]['question'])
            print(f"\n💡 RESPOSTA:\n{answer}\n")
        else:
            print("❌ Opção inválida")

    def _custom_question(self) -> None:
        """Interface para perguntas personalizadas"""
        question = input("💬 Digite sua pergunta: ").strip()
        if question:
            answer = self.ask_question(question)
            print(f"\n💡 RESPOSTA:\n{answer}\n")

    def _export_analysis(self) -> None:
        """Exporta análise consolidada para CSV"""
        if not self.dataframes:
            print("❌ Nenhum dado para exportar")
            return
        
        try:
            combined_df = self._analyze_all_files()
            export_path = f"analise_consolidada_{datetime.now().strftime('%Y%m%d')}.csv"
            combined_df.to_csv(export_path, index=False)
            print(f"✅ Análise exportada para {export_path}")
        except Exception as e:
            print(f"❌ Erro ao exportar: {str(e)}")

if __name__ == "__main__":
    agent = NFExpertSystem()
    agent.interactive_menu()