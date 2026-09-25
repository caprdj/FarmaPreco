import json
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

HEADERS_DEFAULT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/html, */*"
}

def get_sp_time() -> str:
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def consultar_pacheco(url: Optional[str] = None, produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    termo = "puran t4"
    if produto:
        termo = f"{produto.get('nome', '')} {produto.get('dosagem', '')}".strip()
        if produto.get("url_pacheco"):
            url = produto["url_pacheco"]

    url = url or "https://www.drogariaspacheco.com.br/puran-t4-112mcg-sanofi-aventis-30-comprimidos/p"
    
    preco_online = None
    preco_referencia = None
    nome_produto = (produto.get("nome") if produto else None) or termo
    sku_id = ""
    disponivel = True
    link_final = url

    # 1. Tentar acessar a página do produto diretamente
    try:
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            padrao = r"var\s+skuJson_0\s*=\s*(\{.*?\});\s*CATALOG_SDK"
            match = re.search(padrao, html, flags=re.DOTALL)
            if match:
                try:
                    dados = json.loads(match.group(1))
                    nome_produto = dados.get("name", nome_produto)
                    skus = dados.get("skus", [])
                    if skus:
                        sku = skus[0]
                        sku_id = str(sku.get("sku", ""))
                        best_price = sku.get("bestPrice")
                        if best_price is not None:
                            preco_online = best_price / 100
                        list_price = sku.get("listPrice")
                        if list_price is not None:
                            preco_referencia = list_price / 100
                        disponivel = bool(sku.get("available", True))
                except Exception:
                    pass

            if preco_online is None:
                soup = BeautifulSoup(html, "html.parser")
                for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
                    if not s.string: continue
                    try:
                        ld = json.loads(s.string)
                        if ld.get("@type") == "Product" and "offers" in ld:
                            nome_produto = ld.get("name", nome_produto)
                            offers = ld.get("offers", {})
                            p = offers.get("price") or offers.get("lowPrice")
                            if p:
                                preco_online = float(p)
                                disponivel = "InStock" in str(offers.get("availability", ""))
                                break
                    except Exception:
                        continue
    except Exception:
        pass

    # 2. Fallback via Catalog API da Pacheco
    if preco_online is None:
        try:
            api_url = f"https://www.drogariaspacheco.com.br/api/catalog_system/pub/products/search/{urllib.parse.quote(termo)}"
            resp_api = requests.get(api_url, headers=HEADERS_DEFAULT, timeout=15)
            if resp_api.status_code in (200, 206):
                itens = resp_api.json()
                if itens and isinstance(itens, list):
                    item = itens[0]
                    nome_produto = item.get("productName", nome_produto)
                    link_final = item.get("link", link_final)
                    sku_obj = item.get("items", [{}])[0]
                    sku_id = str(sku_obj.get("itemId", ""))
                    sellers = sku_obj.get("sellers", [])
                    if sellers:
                        offer = sellers[0].get("commertialOffer", {})
                        p = offer.get("Price")
                        if p and float(p) > 0:
                            preco_online = float(p)
                            preco_referencia = float(offer.get("ListPrice")) if offer.get("ListPrice") else None
                            disponivel = bool(offer.get("IsAvailable", True))
        except Exception:
            pass

    if preco_online is None:
        return {
            "sucesso": False,
            "drogaria": "Drogarias Pacheco",
            "erro": f"Não foi possível obter preço na Drogarias Pacheco para '{termo}'."
        }

    return {
        "sucesso": True,
        "drogaria": "Drogarias Pacheco",
        "filial": "Rua Conde de Bonfim, 580 — Tijuca",
        "produto": nome_produto,
        "preco_online": round(preco_online, 2),
        "preco_referencia": round(preco_referencia, 2) if preco_referencia else None,
        "disponivel": disponivel,
        "estoque_status": "Não confirmado" if disponivel else "Indisponível",
        "sku": sku_id,
        "url": link_final,
        "promocao": None,
        "data_hora": get_sp_time()
    }

def consultar_venancio(ean: str = "", produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    termo = "puran t4"
    if produto:
        if produto.get("ean"):
            ean = str(produto["ean"])
        termo = f"{produto.get('nome', '')} {produto.get('dosagem', '')}".strip()
    
    url_termo = urllib.parse.quote(termo)
    api_url = f"https://www.drogariavenancio.com.br/api/catalog_system/pub/products/search/{url_termo}"
    url_pagina = produto.get("url_venancio") if produto and produto.get("url_venancio") else "https://www.drogariavenancio.com.br/"
    
    headers = {
        "User-Agent": HEADERS_DEFAULT["User-Agent"],
        "Accept": "application/json"
    }

    try:
        resp = requests.get(api_url, headers=headers, timeout=20)
        if resp.status_code not in (200, 206):
            resp.raise_for_status()
        produtos = resp.json()
    except Exception as e:
        return {
            "sucesso": False,
            "drogaria": "Drogaria Venancio",
            "erro": f"Erro ao consultar catálogo da Venancio: {str(e)}"
        }

    if not isinstance(produtos, list) or not produtos:
        return {
            "sucesso": False,
            "drogaria": "Drogaria Venancio",
            "erro": f"Medicamento não localizado para '{termo}' na Drogaria Venancio."
        }

    produto_alvo = None
    item_alvo = None

    # Tenta achar por EAN se tiver
    if ean and ean != "0":
        for p in produtos:
            for it in p.get("items", []):
                if str(it.get("ean", "")) == ean:
                    produto_alvo = p
                    item_alvo = it
                    break
            if produto_alvo:
                break

    # Se não achou por EAN, filtra para evitar pacotes hospitalares gigantes (ex: dipirona 200 comp)
    if not produto_alvo:
        candidatos = []
        for p in produtos:
            sku = p.get("items", [{}])[0]
            price = sku.get("sellers", [{}])[0].get("commertialOffer", {}).get("Price")
            if price and float(price) > 0:
                candidatos.append((float(price), p, sku))
        if candidatos:
            candidatos.sort(key=lambda x: x[0])
            # Pega o primeiro ou menor preço de varejo
            produto_alvo = candidatos[0][1]
            item_alvo = candidatos[0][2]

    if not produto_alvo or not item_alvo:
        produto_alvo = produtos[0]
        item_alvo = produto_alvo.get("items", [{}])[0]

    sellers = item_alvo.get("sellers", [])
    offer = sellers[0].get("commertialOffer", {}) if sellers else {}
    
    preco = offer.get("Price")
    preco_ref = offer.get("ListPrice")
    disponivel = bool(offer.get("IsAvailable", True))

    if preco is None or preco <= 0:
        return {
            "sucesso": False,
            "drogaria": "Drogaria Venancio",
            "erro": "Preço da Venancio não identificado na oferta comercial."
        }

    # Detectar promoção LEVE X PAGUE Y
    promocao = None
    teasers = offer.get("PromotionTeasers") or offer.get("Teasers") or []
    for t in teasers:
        t_name = str(t.get("Name") or t.get("<Name>k__BackingField") or "").upper()
        m = re.search(r"LEVE\s*(\d+)\s*PAGUE\s*(\d+)", t_name)
        if m:
            leve = int(m.group(1))
            pague = int(m.group(2))
            if leve > pague > 0:
                total_promo = round(preco * pague, 2)
                custo_caixa_promo = round(total_promo / leve, 2)
                promocao = {
                    "tipo": "leve_x_pague_y",
                    "descricao": f"Leve {leve} e Pague {pague}",
                    "quantidade_leve": leve,
                    "quantidade_paga": pague,
                    "valor_total": total_promo,
                    "custo_por_caixa": custo_caixa_promo
                }
                break

    return {
        "sucesso": True,
        "drogaria": "Drogaria Venancio",
        "filial": "Rua Conde de Bonfim, 532 — Tijuca",
        "produto": produto_alvo.get("productName", termo),
        "preco_online": round(float(preco), 2),
        "preco_referencia": round(float(preco_ref), 2) if preco_ref else None,
        "disponivel": disponivel,
        "estoque_status": "Não confirmado" if disponivel else "Indisponível",
        "sku": str(item_alvo.get("itemId", "")),
        "url": produto_alvo.get("link") or url_pagina,
        "promocao": promocao,
        "data_hora": get_sp_time()
    }

def consultar_drogasmil(url: Optional[str] = None, produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    termo = "puran t4"
    if produto:
        termo = f"{produto.get('nome', '')} {produto.get('dosagem', '')}".strip()
        if produto.get("url_drogasmil"):
            url = produto["url_drogasmil"]

    url = url or "https://www.drogasmil.com.br/puran-t4-112mcg-30-comprimidos/p"
    preco = None
    nome_prod = (produto.get("nome") if produto else None) or termo
    sku = ""
    disponivel = True
    link_final = url

    # 1. Tentar acesso direto na URL
    try:
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
            for s in scripts:
                if not s.string: continue
                try:
                    data = json.loads(s.string)
                    candidates = data if isinstance(data, list) else [data]
                    for item in candidates:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            nome_prod = item.get("name", nome_prod)
                            sku = str(item.get("sku", ""))
                            offers = item.get("offers", {})
                            if "lowPrice" in offers:
                                preco = float(offers["lowPrice"])
                            elif "price" in offers:
                                preco = float(offers["price"])
                            elif "offers" in offers and isinstance(offers["offers"], list) and offers["offers"]:
                                sub_offer = offers["offers"][0]
                                if "price" in sub_offer:
                                    preco = float(sub_offer["price"])
                                    disponivel = "InStock" in str(sub_offer.get("availability", ""))
                            if preco: break
                    if preco: break
                except Exception:
                    continue
    except Exception:
        pass

    # 2. Fallback via Catalog API da Drogasmil
    if preco is None:
        try:
            api_url = f"https://www.drogasmil.com.br/api/catalog_system/pub/products/search/{urllib.parse.quote(termo)}"
            resp_api = requests.get(api_url, headers=HEADERS_DEFAULT, timeout=15)
            if resp_api.status_code in (200, 206):
                itens = resp_api.json()
                if itens and isinstance(itens, list):
                    item = itens[0]
                    nome_prod = item.get("productName", nome_prod)
                    link_final = item.get("link", link_final)
                    sku_obj = item.get("items", [{}])[0]
                    sku = str(sku_obj.get("itemId", ""))
                    sellers = sku_obj.get("sellers", [])
                    if sellers:
                        offer = sellers[0].get("commertialOffer", {})
                        p = offer.get("Price")
                        if p and float(p) > 0:
                            preco = float(p)
                            disponivel = bool(offer.get("IsAvailable", True))
        except Exception:
            pass

    if preco is None:
        return {
            "sucesso": False,
            "drogaria": "Drogasmil",
            "erro": f"Não foi possível obter preço na Drogasmil para '{termo}'."
        }

    return {
        "sucesso": True,
        "drogaria": "Drogasmil",
        "filial": "Praça Saenz Peña, 29 — Tijuca",
        "produto": nome_prod,
        "preco_online": round(preco, 2),
        "preco_referencia": None,
        "disponivel": disponivel,
        "estoque_status": "Não confirmado" if disponivel else "Indisponível",
        "sku": sku,
        "url": link_final,
        "promocao": None,
        "data_hora": get_sp_time()
    }

def consultar_todas_automaticas(produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "pacheco": consultar_pacheco(produto=produto),
        "venancio": consultar_venancio(produto=produto),
        "drogasmil": consultar_drogasmil(produto=produto)
    }

def consultar_precos_laboratorios(principio_ativo: str, dosagem: str = "") -> Dict[str, Any]:
    termo = f"{principio_ativo} {dosagem}".strip()
    url_termo = urllib.parse.quote(termo)
    api_url = f"https://www.drogariavenancio.com.br/api/catalog_system/pub/products/search/{url_termo}"

    headers = {
        "User-Agent": HEADERS_DEFAULT["User-Agent"],
        "Accept": "application/json"
    }

    try:
        resp = requests.get(api_url, headers=headers, timeout=20)
        if resp.status_code not in (200, 206):
            return {"sucesso": False, "mensagem": f"Erro de catálogo: HTTP {resp.status_code}", "laboratorios": []}
        produtos = resp.json()
    except Exception as e:
        return {"sucesso": False, "mensagem": str(e), "laboratorios": []}

    if not isinstance(produtos, list) or not produtos:
        return {"sucesso": False, "mensagem": f"Nenhum produto encontrado para '{termo}'.", "laboratorios": []}

    mapa_lab: Dict[str, Dict[str, Any]] = {}

    for p in produtos:
        brand = str(p.get("brand", "")).strip().upper()
        if not brand:
            brand = "OUTROS"

        nome_prod = str(p.get("productName", "")).strip()
        link = p.get("link", "")
        
        items = p.get("items", [])
        if not items: continue
            
        sku = items[0]
        ean = sku.get("ean", "")
        sellers = sku.get("sellers", [])
        if not sellers: continue
            
        offer = sellers[0].get("commertialOffer", {})
        price = offer.get("Price")
        list_price = offer.get("ListPrice")
        available = bool(offer.get("IsAvailable", True))

        if price is None or price <= 0: continue

        price = round(float(price), 2)
        list_price = round(float(list_price), 2) if list_price else None

        nome_lower = nome_prod.lower()
        if "generico" in nome_lower or "genérico" in nome_lower:
            categoria = "Genérico"
        elif any(ref in brand.lower() for ref in ["sanofi", "abbott", "merck", "pfizer", "novartis", "bayer", "roche"]):
            categoria = "Referência"
        elif any(gen in brand.lower() for gen in ["ems", "medley", "eurofarma", "neo quimica", "teuto", "prati", "germed", "biosintetica"]):
            categoria = "Genérico"
        else:
            categoria = "Similar"

        item_dict = {
            "laboratorio": brand,
            "nome_produto": nome_prod,
            "preco": price,
            "preco_referencia": list_price,
            "categoria": categoria,
            "disponivel": available,
            "ean": ean,
            "drogaria": "Drogaria Venancio",
            "url": link
        }

        if brand not in mapa_lab or price < mapa_lab[brand]["preco"]:
            mapa_lab[brand] = item_dict

    lista_labs = list(mapa_lab.values())
    if not lista_labs:
        return {"sucesso": False, "mensagem": "Nenhum preço válido encontrado.", "laboratorios": []}

    lista_labs.sort(key=lambda x: x["preco"])
    mais_caro = max(lista_labs, key=lambda x: x["preco"])
    mais_barato = lista_labs[0]

    for lab in lista_labs:
        dif = round(mais_caro["preco"] - lab["preco"], 2)
        pct = round((dif / mais_caro["preco"]) * 100, 1) if mais_caro["preco"] > 0 else 0.0
        lab["economia_reais"] = dif
        lab["economia_pct"] = pct

    return {
        "sucesso": True,
        "termo": termo,
        "total_laboratorios": len(lista_labs),
        "laboratorio_mais_barato": mais_barato,
        "laboratorio_mais_caro": mais_caro,
        "diferenca_maxima": round(mais_caro["preco"] - mais_barato["preco"], 2),
        "economia_maxima_pct": mais_barato["economia_pct"],
        "laboratorios": lista_labs
    }
