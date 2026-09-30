import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_DADOS = BASE_DIR / "dados"
PASTA_RELATORIOS = BASE_DIR / "relatorios"

PASTA_DADOS.mkdir(parents=True, exist_ok=True)
PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

ARQUIVO_HISTORICO = PASTA_DADOS / "historico_precos.csv"
ARQUIVO_DROGARIAS = PASTA_DADOS / "drogarias.csv"
ARQUIVO_PRODUTOS = PASTA_DADOS / "produtos.csv"

COLUNAS_PRODUTOS = [
    "produto_id", "nome", "principio_ativo", "dosagem",
    "apresentacao", "fabricante", "categoria", "quantidade_mensal", "ean",
    "url_pacheco", "url_venancio", "url_drogasmil", "url_raia"
]

COLUNAS_HISTORICO = [
    "data_hora", "produto_id", "drogaria", "filial",
    "laboratorio", "modalidade", "condicao_preco", "valor_total",
    "quantidade_caixas", "custo_por_caixa", "frete",
    "estoque", "fonte", "url", "observacoes"
]

def inicializar_arquivos_se_necessario():
    if not ARQUIVO_PRODUTOS.exists():
        df_prod = pd.DataFrame([
            {
                "produto_id": "MED001",
                "nome": "Puran T4",
                "principio_ativo": "Levotiroxina sódica",
                "dosagem": "112 µg",
                "apresentacao": "30 comprimidos",
                "fabricante": "Sanofi Aventis",
                "categoria": "Referência",
                "quantidade_mensal": 1,
                "ean": "7897595903372",
                "url_pacheco": "https://www.drogariaspacheco.com.br/puran-t4-112mcg-sanofi-aventis-30-comprimidos/p",
                "url_venancio": "https://www.drogariavenancio.com.br/puran-t4-112mcg-sanofi-aventis-30-comprimidos/p",
                "url_drogasmil": "https://www.drogasmil.com.br/puran-t4-112mcg-30-comprimidos/p",
                "url_raia": "https://www.drogaraia.com.br/puran-t4-112mcg-30-comprimidos.html"
            }
        ])
        df_prod.to_csv(ARQUIVO_PRODUTOS, index=False, encoding="utf-8-sig")
    else:
        # Garantir novas colunas se o arquivo já existia
        try:
            df_atual = pd.read_csv(ARQUIVO_PRODUTOS, encoding="utf-8-sig")
            alterado = False
            for col in COLUNAS_PRODUTOS:
                if col not in df_atual.columns:
                    if col == "categoria":
                        df_atual[col] = "Referência"
                    elif col == "quantidade_mensal":
                        df_atual[col] = 1
                    else:
                        df_atual[col] = ""
                    alterado = True
            if alterado:
                df_atual[COLUNAS_PRODUTOS].to_csv(ARQUIVO_PRODUTOS, index=False, encoding="utf-8-sig")
        except Exception:
            pass

    if not ARQUIVO_DROGARIAS.exists():
        df_drog = pd.DataFrame([
            {
                "drogaria": "Drogarias Pacheco",
                "filial": "Rua Conde de Bonfim, 580 — Tijuca",
                "cadastro_cpf": True,
                "url_produto": "https://www.drogariaspacheco.com.br/puran-t4-112mcg-sanofi-aventis-30-comprimidos/p",
                "tipo_coleta": "automatica"
            },
            {
                "drogaria": "Droga Raia",
                "filial": "Rua Conde de Bonfim, 536 — Tijuca",
                "cadastro_cpf": True,
                "url_produto": "https://www.drogaraia.com.br/puran-t4-112mcg-30-comprimidos.html",
                "tipo_coleta": "assistida"
            },
            {
                "drogaria": "Drogaria Venancio",
                "filial": "Rua Conde de Bonfim, 532 — Tijuca",
                "cadastro_cpf": False,
                "url_produto": "https://www.drogariavenancio.com.br/puran-t4-112mcg-sanofi-aventis-30-comprimidos/p",
                "tipo_coleta": "automatica"
            },
            {
                "drogaria": "Drogasmil",
                "filial": "Praça Saenz Peña, 29 — Tijuca",
                "cadastro_cpf": False,
                "url_produto": "https://www.drogasmil.com.br/puran-t4-112mcg-30-comprimidos/p",
                "tipo_coleta": "automatica"
            },
        ])
        df_drog.to_csv(ARQUIVO_DROGARIAS, index=False, encoding="utf-8-sig")

    if not ARQUIVO_HISTORICO.exists():
        df_hist = pd.DataFrame(columns=COLUNAS_HISTORICO)
        df_hist.to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")

def carregar_produtos() -> List[Dict[str, Any]]:
    inicializar_arquivos_se_necessario()
    try:
        df = pd.read_csv(ARQUIVO_PRODUTOS, encoding="utf-8-sig").fillna("")
        return df.to_dict(orient="records")
    except Exception:
        return []

def obter_produto_por_id(produto_id: str) -> Optional[Dict[str, Any]]:
    prods = carregar_produtos()
    for p in prods:
        if str(p.get("produto_id")) == str(produto_id):
            return p
    return prods[0] if prods else None

def cadastrar_produto(dados: Dict[str, Any]) -> Dict[str, Any]:
    inicializar_arquivos_se_necessario()
    prods = carregar_produtos()
    
    # Gerar novo produto_id incremental
    max_num = 0
    for p in prods:
        pid = str(p.get("produto_id", ""))
        if pid.startswith("MED"):
            try:
                num = int(pid.replace("MED", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
                
    novo_id = f"MED{max_num + 1:03d}"
    
    novo = {
        "produto_id": novo_id,
        "nome": dados.get("nome", "").strip(),
        "principio_ativo": dados.get("principio_ativo", "").strip(),
        "dosagem": dados.get("dosagem", "").strip(),
        "apresentacao": dados.get("apresentacao", "").strip(),
        "fabricante": dados.get("fabricante", "").strip(),
        "categoria": dados.get("categoria", "Genérico").strip(),
        "quantidade_mensal": int(dados.get("quantidade_mensal", 1) or 1),
        "ean": str(dados.get("ean", "")).strip(),
        "url_pacheco": str(dados.get("url_pacheco", "")).strip(),
        "url_venancio": str(dados.get("url_venancio", "")).strip(),
        "url_drogasmil": str(dados.get("url_drogasmil", "")).strip(),
        "url_raia": str(dados.get("url_raia", "")).strip()
    }
    
    df_novo = pd.DataFrame([novo])
    if prods:
        df_atual = pd.DataFrame(prods)
        df_final = pd.concat([df_atual, df_novo], ignore_index=True)
    else:
        df_final = df_novo
        
    df_final[COLUNAS_PRODUTOS].to_csv(ARQUIVO_PRODUTOS, index=False, encoding="utf-8-sig")
    return novo

def excluir_produto(produto_id: str) -> bool:
    inicializar_arquivos_se_necessario()
    prods = carregar_produtos()
    novos = [p for p in prods if str(p.get("produto_id")) != str(produto_id)]
    if len(novos) < len(prods):
        pd.DataFrame(novos)[COLUNAS_PRODUTOS].to_csv(ARQUIVO_PRODUTOS, index=False, encoding="utf-8-sig")
        return True
    return False

def atualizar_produto(produto_id: str, dados: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    inicializar_arquivos_se_necessario()
    prods = carregar_produtos()
    produto_atualizado = None
    for p in prods:
        if str(p.get("produto_id")) == str(produto_id):
            for campo in ["nome", "principio_ativo", "dosagem", "apresentacao", "fabricante", "categoria", "ean", "url_pacheco", "url_venancio", "url_drogasmil", "url_raia"]:
                if campo in dados and dados[campo] is not None:
                    p[campo] = str(dados[campo]).strip()
            if "quantidade_mensal" in dados and dados["quantidade_mensal"] is not None:
                try:
                    p["quantidade_mensal"] = int(dados["quantidade_mensal"])
                except (ValueError, TypeError):
                    pass
            produto_atualizado = p
            break
            
    if produto_atualizado:
        pd.DataFrame(prods)[COLUNAS_PRODUTOS].to_csv(ARQUIVO_PRODUTOS, index=False, encoding="utf-8-sig")
        return produto_atualizado
    return None

def carregar_drogarias() -> List[Dict[str, Any]]:
    inicializar_arquivos_se_necessario()
    try:
        df = pd.read_csv(ARQUIVO_DROGARIAS, encoding="utf-8-sig")
        return df.to_dict(orient="records")
    except Exception:
        return []

def carregar_historico() -> pd.DataFrame:
    inicializar_arquivos_se_necessario()
    if ARQUIVO_HISTORICO.exists():
        try:
            df = pd.read_csv(ARQUIVO_HISTORICO, encoding="utf-8-sig")
            for col in COLUNAS_HISTORICO:
                if col not in df.columns:
                    df[col] = ""
            return df[COLUNAS_HISTORICO].copy()
        except Exception:
            pass
    return pd.DataFrame(columns=COLUNAS_HISTORICO)

def registro_ja_existe(df: pd.DataFrame, novo: Dict[str, Any]) -> bool:
    if df.empty:
        return False
    
    dados = df.copy()
    data_novo = str(novo.get("data_hora", ""))[:10]
    
    mesma_data = dados["data_hora"].astype(str).str[:10] == data_novo
    mesmo_prod = dados["produto_id"].astype(str) == str(novo.get("produto_id", ""))
    mesma_drogaria = dados["drogaria"].astype(str) == str(novo.get("drogaria", ""))
    mesma_modalidade = dados["modalidade"].astype(str) == str(novo.get("modalidade", ""))
    mesma_condicao = dados["condicao_preco"].astype(str) == str(novo.get("condicao_preco", ""))
    
    try:
        val_novo = round(float(novo.get("valor_total", 0)), 2)
        qtd_novo = int(novo.get("quantidade_caixas", 1))
        
        mesmo_valor = pd.to_numeric(dados["valor_total"], errors="coerce").round(2) == val_novo
        mesma_qtd = pd.to_numeric(dados["quantidade_caixas"], errors="coerce").fillna(1).astype(int) == qtd_novo
        
        dups = dados[mesma_data & mesmo_prod & mesma_drogaria & mesma_modalidade & mesma_condicao & mesmo_valor & mesma_qtd]
        return not dups.empty
    except Exception:
        return False

def salvar_registro(novo: Dict[str, Any], forcar_duplicado: bool = False) -> Dict[str, Any]:
    inicializar_arquivos_se_necessario()
    df = carregar_historico()
    
    if not forcar_duplicado and registro_ja_existe(df, novo):
        return {
            "salvo": False,
            "motivo": "Registro equivalente já existe para hoje."
        }
    
    linha = {col: novo.get(col, "") for col in COLUNAS_HISTORICO}
    nova_df = pd.DataFrame([linha])
    
    if df.empty:
        df_final = nova_df
    else:
        df_final = pd.concat([df, nova_df], ignore_index=True)
        
    df_final[COLUNAS_HISTORICO].to_csv(ARQUIVO_HISTORICO, index=False, encoding="utf-8-sig")
    return {"salvo": True, "registro": linha}

def salvar_multiplos_registros(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    inicializar_arquivos_se_necessario()
    salvos = 0
    duplicados = 0
    
    for reg in registros:
        res = salvar_registro(reg)
        if res["salvo"]:
            salvos += 1
        else:
            duplicados += 1
            
    return {"total": len(registros), "salvos": salvos, "duplicados": duplicados}

def gerar_relatorio_csv() -> str:
    inicializar_arquivos_se_necessario()
    df = carregar_historico()
    if not df.empty:
        df = df.sort_values("data_hora", ascending=False)
    nome_arquivo = f"comparacao_precos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    caminho = PASTA_RELATORIOS / nome_arquivo
    df.to_csv(caminho, index=False, encoding="utf-8-sig")
    return str(caminho)

PASTA_PRINTS = PASTA_DADOS / "prints_raia"
PASTA_PRINTS.mkdir(parents=True, exist_ok=True)
VALIDADE_PRINT_DIAS = 3

def obter_status_prints_raia(produto_id: Optional[str] = None) -> List[Dict[str, Any]]:
    produtos = carregar_produtos()
    df_hist = carregar_historico()
    agora = datetime.now()
    status_lista = []
    
    for p in produtos:
        pid = p["produto_id"]
        if produto_id and pid != produto_id:
            continue
            
        registros_raia = pd.DataFrame()
        if not df_hist.empty and "drogaria" in df_hist.columns and "produto_id" in df_hist.columns:
            mask = (df_hist["drogaria"].astype(str).str.lower().str.contains("raia")) & (df_hist["produto_id"].astype(str) == str(pid))
            registros_raia = df_hist[mask].copy()
            
        if not registros_raia.empty:
            registros_raia["dt"] = pd.to_datetime(registros_raia["data_hora"], errors="coerce")
            registros_raia = registros_raia.dropna(subset=["dt"]).sort_values("dt", ascending=True)
            
        if not registros_raia.empty:
            ultimo = registros_raia.iloc[-1]
            dt_upload = ultimo["dt"]
            diff_segundos = (agora - dt_upload).total_seconds()
            dias_decorridos = round(diff_segundos / 86400, 1)
            horas_restantes = max(0.0, round((VALIDADE_PRINT_DIAS * 86400 - diff_segundos) / 3600, 1))
            dias_restantes = max(0.0, round(horas_restantes / 24, 1))
            
            expirado = False
            status_tipo = "valido"
            badge_class = "bg-emerald-100 text-emerald-800 border-emerald-300"
            msg_validade = f"Preço cadastrado em {dt_upload.strftime('%d/%m/%Y')}"
                
            custo_caixa = float(ultimo.get("custo_por_caixa", 0.0))
            url_comprovante = str(ultimo.get("url", ""))
            obs = str(ultimo.get("observacoes", ""))
            lab = str(ultimo.get("laboratorio", p.get("fabricante", "")))
            
            status_lista.append({
                "produto_id": pid,
                "nome": p["nome"],
                "dosagem": p["dosagem"],
                "fabricante": p["fabricante"],
                "tem_cotacao": True,
                "data_upload": dt_upload.strftime("%d/%m/%Y %H:%M"),
                "dias_decorridos": dias_decorridos,
                "dias_restantes": 999,
                "horas_restantes": 999,
                "expirado": False,
                "status_tipo": "valido",
                "badge_class": badge_class,
                "mensagem_validade": msg_validade,
                "preco_por_caixa": custo_caixa,
                "laboratorio": lab,
                "url_comprovante": url_comprovante,
                "url_loja": p.get("url_raia", ""),
                "observacoes": obs
            })
        else:
            status_lista.append({
                "produto_id": pid,
                "nome": p["nome"],
                "dosagem": p["dosagem"],
                "fabricante": p["fabricante"],
                "tem_cotacao": False,
                "data_upload": None,
                "dias_decorridos": None,
                "dias_restantes": 0,
                "horas_restantes": 0,
                "expirado": False,
                "status_tipo": "sem_preco",
                "badge_class": "bg-slate-100 text-slate-700 border-slate-300",
                "mensagem_validade": "Sem preço cadastrado",
                "preco_por_caixa": None,
                "laboratorio": None,
                "url_comprovante": "",
                "url_loja": p.get("url_raia", ""),
                "observacoes": ""
            })
            
    return status_lista
