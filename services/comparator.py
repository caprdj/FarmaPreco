import pandas as pd
from typing import Dict, Any, List, Optional
from services.storage import carregar_historico, obter_produto_por_id

def estoque_confirmado(valor: Any) -> bool:
    texto = str(valor).strip().lower()
    return texto in ("disponível para retirada", "disponível na loja", "confirmado")

def preparar_historico_comparacao(produto_id: str = "MED001") -> pd.DataFrame:
    dados = carregar_historico().copy()
    if dados.empty:
        return dados

    dados["data_hora"] = pd.to_datetime(dados["data_hora"], errors="coerce")
    
    colunas_numericas = ["valor_total", "quantidade_caixas", "custo_por_caixa", "frete"]
    for col in colunas_numericas:
        dados[col] = pd.to_numeric(dados[col], errors="coerce")

    dados = dados.dropna(subset=["data_hora", "custo_por_caixa", "quantidade_caixas"])
    
    if "produto_id" in dados.columns and produto_id:
        dados = dados[dados["produto_id"].astype(str) == str(produto_id)]
        
    dados = dados.sort_values("data_hora", ascending=True)

    colunas_oferta = [
        "produto_id", "drogaria", "filial", "laboratorio",
        "modalidade", "condicao_preco", "quantidade_caixas"
    ]
    
    dados = dados.drop_duplicates(subset=colunas_oferta, keep="last")
    return dados

def comparar_precos(
    quantidade_desejada: int = 1,
    somente_confirmado: bool = False,
    filtro_modalidade: Optional[str] = None,
    produto_id: str = "MED001"
) -> Dict[str, Any]:
    dados = preparar_historico_comparacao(produto_id=produto_id)
    if dados.empty:
        return {
            "sucesso": False,
            "mensagem": "Nenhum histórico de preço cadastrado ainda.",
            "ofertas": [],
            "melhor_opcao": None,
            "quantidade_desejada": quantidade_desejada
        }

    ofertas = []

    for _, reg in dados.iterrows():
        condicao = str(reg["condicao_preco"]).strip()
        qtd_reg = int(reg["quantidade_caixas"])
        custo_unitario = float(reg["custo_por_caixa"])
        frete = float(reg["frete"]) if pd.notna(reg["frete"]) else 0.0
        modalidade = str(reg["modalidade"]).strip()

        if filtro_modalidade and filtro_modalidade.lower() != "todas":
            if filtro_modalidade.lower() not in modalidade.lower():
                continue

        if condicao == "Preço comum":
            total_estimado = round(custo_unitario * quantidade_desejada + frete, 2)
            qtd_minima = 1
        elif condicao == "Promoção por quantidade":
            if quantidade_desejada != qtd_reg:
                # Se não for a quantidade exata da promoção, pula para não distorcer
                continue
            total_estimado = round(float(reg["valor_total"]) + frete, 2)
            qtd_minima = qtd_reg
        else:
            if quantidade_desejada != qtd_reg:
                continue
            total_estimado = round(float(reg["valor_total"]) + frete, 2)
            qtd_minima = qtd_reg

        disp_confirmada = estoque_confirmado(reg["estoque"])
        if somente_confirmado and not disp_confirmada:
            continue

        lab = str(reg.get("laboratorio", "")).strip()
        if not lab or lab.lower() in ("nan", "none", "null", ""):
            prod_info = obter_produto_por_id(reg.get("produto_id"))
            if prod_info and prod_info.get("fabricante"):
                lab = str(prod_info["fabricante"]).strip()
        if not lab or lab.lower() in ("nan", "none", "null", ""):
            obs = str(reg.get("observacoes", ""))
            for brand_candidate in ["EMS", "Medley", "Eurofarma", "Sanofi Aventis", "Sanofi", "Aché", "Biolab", "Prati Donaduzzi", "Prati", "Neo Química", "Aspdip", "Merck", "Abbott", "Pfizer", "Bayer"]:
                if brand_candidate.lower() in obs.lower():
                    lab = brand_candidate
                    break
        if not lab or lab.lower() in ("nan", "none", "null", ""):
            lab = "Não informado"

        is_raia = "raia" in str(reg["drogaria"]).lower()
        expirado_3dias = False
        dias_desde_upload = 0.0

        ofertas.append({
            "drogaria": str(reg["drogaria"]),
            "filial": str(reg["filial"]),
            "laboratorio": lab,
            "modalidade": modalidade,
            "condicao": condicao,
            "custo_por_caixa": custo_unitario,
            "total_estimado": total_estimado,
            "minimo_caixas": qtd_minima,
            "estoque": str(reg["estoque"]),
            "confirmado": disp_confirmada,
            "is_raia": is_raia,
            "expirado_3dias": expirado_3dias,
            "dias_desde_upload": dias_desde_upload,
            "data_hora": reg["data_hora"].strftime("%d/%m/%Y %H:%M") if pd.notna(reg["data_hora"]) else "",
            "fonte": str(reg["fonte"]),
            "url": str(reg.get("url", "")),
            "observacoes": str(reg.get("observacoes", ""))
        })

    if not ofertas:
        msg = f"Nenhuma oferta atende ao critério para {quantidade_desejada} caixa(s)."
        if somente_confirmado:
            msg += " Desmarque o filtro de estoque confirmado para ver mais opções."
        return {
            "sucesso": True,
            "mensagem": msg,
            "ofertas": [],
            "melhor_opcao": None,
            "quantidade_desejada": quantidade_desejada
        }

    # Ordenar por menor total estimado, depois menor custo por caixa
    ofertas.sort(key=lambda x: (x["total_estimado"], x["custo_por_caixa"]))

    for i, of in enumerate(ofertas, start=1):
        of["posicao"] = i

    melhor = ofertas[0]
    pior = ofertas[-1]
    economia = round(pior["total_estimado"] - melhor["total_estimado"], 2) if len(ofertas) > 1 else 0.0

    return {
        "sucesso": True,
        "quantidade_desejada": quantidade_desejada,
        "total_ofertas": len(ofertas),
        "melhor_opcao": melhor,
        "pior_opcao": pior,
        "economia_maxima": economia,
        "ofertas": ofertas
    }
