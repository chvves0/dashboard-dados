"""
Dashboard de Engajamento com o MEJ (ECM)
Análise do indicador a partir de duas bases:
  - Produtos_de_Conexão.csv   → participações EJ × produto
  - Dados_Gerais_da_Rede.csv  → universo completo de EJs da rede
"""

import io
import math
import re
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Configuração e identidade visual
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Engajamento com o MEJ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY    = "#02195B"
AMARELO = "#FFC831"
VERDE   = "#2D783A"
VERDE_CLARO = "#6FA043"
LARANJA = "#E08A2E"
VERMELHO= "#C8442E"
VINHO   = "#8C2D1B"
OURO    = "#E0A800"
CINZA   = "#9AA3B2"
LINHA   = "#E3E6EC"
TEXTO   = "#0B1B3D"
MUDO    = "#68718A"

FUNDO_KPI  = "#FFFFFF"
BORDA_KPI  = LINHA
ROTULO_KPI = MUDO
VALOR_KPI  = TEXTO
LEGENDA_KPI= MUDO
TRILHOS_KPI= [NAVY, VERDE, OURO]

# --------------------------------------------------------------------------
# Origem dos dados — dois arquivos separados
# --------------------------------------------------------------------------
# Cole links raw do GitHub para cada arquivo, ou deixe vazio para usar os
# CSVs que estão ao lado do app.py (ou dentro de uma pasta "dados/").

URL_PRODUTOS     = ""   # ex.: "https://raw.githubusercontent.com/.../Produtos_de_Conexão.csv"
URL_DADOS_GERAIS = ""   # ex.: "https://raw.githubusercontent.com/.../Dados_Gerais_da_Rede.csv"

CACHE_MINUTOS = 10

PASTA_APP = Path(__file__).resolve().parent

NOMES_PRODUTOS = [
    "Produtos_de_Conexão.csv",
    "Produtos_de_Conexao.csv",
    "produtos_de_conexao.csv",
    "produtos_de_conexão.csv",
]

NOMES_GERAIS = [
    "Dados_Gerais_da_Rede.csv",
    "dados_gerais_da_rede.csv",
    "Dados_Gerais.csv",
    "dados_gerais.csv",
]

SITUACOES = {
    "zerada":    {"rotulo": "Zeradas · 0% de alcance",     "cor": VINHO,       "ordem": 0},
    "ate25":     {"rotulo": "0,1% a 25% da meta",          "cor": VERMELHO,    "ordem": 1},
    "ate50":     {"rotulo": "26% a 50% da meta",           "cor": LARANJA,     "ordem": 2},
    "ate75":     {"rotulo": "51% a 75% da meta",           "cor": OURO,        "ordem": 3},
    "ate99":     {"rotulo": "76% a 99% da meta",           "cor": VERDE_CLARO, "ordem": 4},
    "batida":    {"rotulo": "Meta batida · 100% ou mais",  "cor": VERDE,       "ordem": 5},
}
ORDEM_SIT = sorted(SITUACOES, key=lambda k: SITUACOES[k]["ordem"])


def faixa_alcance(alcance, membros) -> str:
    """Classifica a EJ pela fatia da própria meta que já alcançou.

    Os cortes são fechados à direita (25% cai em '0,1% a 25%', 25,4% já cai na
    faixa seguinte), então não sobra buraco entre as faixas.

    EJ sem membros na base — em que o alcance seria uma divisão por zero — entra
    como zerada. O bloco da meta da FEJERS mostra quantas são.
    """
