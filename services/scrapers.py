import json
import re
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

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

def contem_palavra_exata(palavra: str, texto: str) -> bool:
    """Verifica se a palavra existe como termo inteiro no texto, evitando falsos positivos como 'bup' em 'ibupril'."""
    padrao = r'(?:^|[^\w])' + re.escape(palavra) + r'(?:$|[^\w])'
    return bool(re.search(padrao, texto, re.IGNORECASE))

def extrair_volume_ou_qtd(texto: str) -> set:
    """Extrai quantidade de comprimidos/cápsulas ou volume em ml/g para evitar misturar embalagens de 30 e 60."""
    t_lower = texto.lower()
    m_qtd = re.findall(r'(\d+)\s*(?:comprimidos?|comp|cpr|c[aá]psulas?|caps?|unidades?|un|doses?)', t_lower)
    m_vol = re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:ml|g|kg)', t_lower)
    res = set()
    if m_qtd:
        for q in m_qtd:
            res.add(int(q))
    if m_vol:
        for v in m_vol:
            res.add(v.replace(',', '.'))
    return res

def limpar_termo_busca(nome: str, dosagem: str = "", principio_ativo: str = "", apresentacao: str = "") -> str:
    """Limpa o nome para busca em APIs de catálogo sem quebrar com caracteres inválidos."""
    # Remove texto entre parênteses: ex "Puran T4 (Levotiroxina 112mcg)" -> "Puran T4"
    nome_limpo = re.sub(r"\(.*?\)", "", nome)
    if "/" in nome_limpo:
        nome_limpo = nome_limpo.split("/")[0].strip()
    nome_limpo = re.sub(r'[,"]', "", nome_limpo).strip()
    
    dosagem_norm = dosagem.replace("µg", "mcg").replace(" ", "").strip() if dosagem else ""
    # Se a dosagem já estiver no nome, não duplicar (evita "Sertralina 50mg 50mg")
    if dosagem_norm and dosagem_norm.lower() not in nome_limpo.lower():
        termo = f"{nome_limpo} {dosagem_norm}"
    else:
        termo = nome_limpo
        
    return re.sub(r"\s+", " ", termo).strip()

def validar_candidato(
    nome_candidato: str,
    nome_buscado: str,
    dosagem_buscada: str = "",
    principio_ativo: str = "",
    apresentacao_buscada: str = ""
) -> bool:
    """Valida estritamente se o produto retornado corresponde ao medicamento desejado."""
    if not nome_candidato:
        return False
    c_lower = nome_candidato.lower()
    
    # 1. Palavras exatas do nome ou princípio ativo (evita match de bup em ibupril)
    nb_clean = re.sub(r"\(.*?\)", "", nome_buscado).lower()
    palavras_nome = [p for p in re.split(r"[\s/]+", nb_clean) if len(p) >= 3 and not re.match(r"^\d", p)]
    palavras_ativo = [p for p in re.split(r"[\s/]+", principio_ativo.lower()) if len(p) >= 4 and p not in ("cloridrato", "hemifumarato", "sodica", "sdica", "calcica")]
    
    tem_nome = any(contem_palavra_exata(p, c_lower) for p in palavras_nome)
    tem_ativo = any(contem_palavra_exata(p, c_lower) for p in palavras_ativo)
    if not (tem_nome or tem_ativo):
        return False
        
    # 2. Dosagem (ex: 300mg não pode casar com 150mg)
    if dosagem_buscada:
        d_alvo = dosagem_buscada.lower().replace(" ", "").replace("µg", "mcg")
        d_candidato = [x.replace(" ", "").replace("µg", "mcg") for x in re.findall(r"(\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui|ml))", c_lower)]
        if d_candidato and d_alvo not in d_candidato:
            return False

    # 3. Volume ou Quantidade de comprimidos (30 comp vs 60 comp)
    alvo_vols = extrair_volume_ou_qtd(f"{nome_buscado} {apresentacao_buscada}")
    cand_vols = extrair_volume_ou_qtd(nome_candidato)
    if alvo_vols and cand_vols:
        if not (alvo_vols & cand_vols):
            return False
            
    return True

def extrair_promocao(offer: Dict[str, Any], preco_unit: float) -> Optional[Dict[str, Any]]:
    """Identifica ofertas do tipo LEVE X PAGUE Y no nó de teasers da VTEX."""
    teasers = offer.get("PromotionTeasers") or offer.get("Teasers") or []
    for t in teasers:
        t_name = str(t.get("Name") or t.get("<Name>k__BackingField") or "").upper()
        m = re.search(r"LEVE\s*(\d+)\s*PAGUE\s*(\d+)", t_name)
        if m:
            leve = int(m.group(1))
            pague = int(m.group(2))
            if leve > pague > 0:
                total_promo = round(preco_unit * pague, 2)
                custo_caixa_promo = round(total_promo / leve, 2)
                return {
                    "tipo": "leve_x_pague_y",
                    "descricao": f"Leve {leve} e Pague {pague}",
                    "quantidade_leve": leve,
                    "quantidade_paga": pague,
                    "valor_total": total_promo,
                    "custo_por_caixa": custo_caixa_promo
                }
    return None

def extrair_preco_html(html: str) -> Tuple[Optional[float], Optional[float], Optional[str], Optional[str], bool, Optional[str]]:
    """Extrai informações de preço e produto do HTML de lojas VTEX."""
    preco_online = None
    preco_referencia = None
    nome_produto = None
    sku_id = None
    disponivel = True
    laboratorio = None

    # 1. Tentar skuJson_0
    m = re.search(r"var\s+skuJson_0\s*=\s*(\{.*?\});\s*CATALOG_SDK", html, flags=re.DOTALL)
    if m:
        try:
            dados = json.loads(m.group(1))
            nome_produto = dados.get("name")
            skus = dados.get("skus", [])
            if skus:
                sku = skus[0]
                sku_id = str(sku.get("sku", ""))
                best_price = sku.get("bestPrice")
                if best_price is not None and best_price > 0:
                    preco_online = best_price / 100
                list_price = sku.get("listPrice")
                if list_price is not None and list_price > 0:
                    preco_referencia = list_price / 100
                disponivel = bool(sku.get("available", True))
        except Exception:
            pass

    # 2. Tentar JSON-LD
    if preco_online is None:
        soup = BeautifulSoup(html, "html.parser")
        for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if not s.string: continue
            try:
                ld = json.loads(s.string)
                candidates = ld if isinstance(ld, list) else [ld]
                for item in candidates:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        nome_produto = nome_produto or item.get("name")
                        brand_obj = item.get("brand", {})
                        if isinstance(brand_obj, dict):
                            laboratorio = brand_obj.get("name")
                        elif isinstance(brand_obj, str):
                            laboratorio = brand_obj
                        sku_id = sku_id or str(item.get("sku", ""))
                        offers = item.get("offers", {})
                        if "lowPrice" in offers and float(offers["lowPrice"]) > 0:
                            preco_online = float(offers["lowPrice"])
                        elif "price" in offers and float(offers["price"]) > 0:
                            preco_online = float(offers["price"])
                        elif "offers" in offers and isinstance(offers["offers"], list) and offers["offers"]:
                            sub = offers["offers"][0]
                            if "price" in sub and float(sub["price"]) > 0:
                                preco_online = float(sub["price"])
                                disponivel = "InStock" in str(sub.get("availability", ""))
                        if preco_online: break
                if preco_online: break
            except Exception:
                continue

    return preco_online, preco_referencia, nome_produto, sku_id, disponivel, laboratorio

def consultar_vtex_ean(domain: str, ean: str) -> Optional[Dict[str, Any]]:
    """Busca produto no catálogo VTEX usando o código de barras oficial EAN (100% exato)."""
    if not ean or str(ean).strip() in ("0", "", "None") or len(str(ean).strip()) < 7:
        return None
    ean_clean = str(ean).strip()
    try:
        url = f"https://{domain}/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{ean_clean}"
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=12)
        if resp.status_code in (200, 206):
            produtos = resp.json()
            if isinstance(produtos, list) and produtos:
                p = produtos[0]
                items = p.get("items", [])
                if items:
                    sku = items[0]
                    sellers = sku.get("sellers", [])
                    if sellers:
                        offer = sellers[0].get("commertialOffer", {})
                        price = offer.get("Price")
                        if price and float(price) > 0:
                            preco_float = round(float(price), 2)
                            promo = extrair_promocao(offer, preco_float)
                            return {
                                "produto": p.get("productName"),
                                "laboratorio": p.get("brand") or "",
                                "preco_online": preco_float,
                                "preco_referencia": round(float(offer.get("ListPrice")), 2) if offer.get("ListPrice") else None,
                                "disponivel": bool(offer.get("IsAvailable", True)),
                                "sku": str(sku.get("itemId", "")),
                                "url": p.get("link") or "",
                                "promocao": promo
                            }
    except Exception:
        pass
    return None

def consultar_vtex_search(
    domain: str,
    termo: str,
    nome_alvo: str,
    dosagem_alvo: str = "",
    ativo_alvo: str = "",
    apresentacao_alvo: str = ""
) -> Optional[Dict[str, Any]]:
    """Busca textual no catálogo VTEX aplicando validação estrita de candidatos."""
    try:
        url = f"https://{domain}/api/catalog_system/pub/products/search/{urllib.parse.quote(termo)}"
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=15)
        if resp.status_code in (200, 206):
            produtos = resp.json()
            if isinstance(produtos, list) and produtos:
                candidatos_validos = []
                for p in produtos:
                    pname = p.get("productName", "")
                    if not validar_candidato(pname, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
                        continue
                    items = p.get("items", [])
                    if items:
                        sku = items[0]
                        sellers = sku.get("sellers", [])
                        if sellers:
                            offer = sellers[0].get("commertialOffer", {})
                            price = offer.get("Price")
                            if price and float(price) > 0:
                                preco_float = round(float(price), 2)
                                promo = extrair_promocao(offer, preco_float)
                                item_candidato = {
                                    "produto": pname,
                                    "laboratorio": p.get("brand") or "",
                                    "preco_online": preco_float,
                                    "preco_referencia": round(float(offer.get("ListPrice")), 2) if offer.get("ListPrice") else None,
                                    "disponivel": bool(offer.get("IsAvailable", True)),
                                    "sku": str(sku.get("itemId", "")),
                                    "url": p.get("link") or "",
                                    "promocao": promo
                                }
                                candidatos_validos.append(item_candidato)

                if candidatos_validos:
                    # Se tiver mais de um, preferir aquele com preço varejo comum (menor preço)
                    candidatos_validos.sort(key=lambda x: x["preco_online"])
                    return candidatos_validos[0]
    except Exception:
        pass
    return None

def consultar_pacheco(url: Optional[str] = None, produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nome_alvo = "Puran T4"
    dosagem_alvo = ""
    ativo_alvo = ""
    apresentacao_alvo = ""
    fabricante_padrao = "Marca"
    ean = ""
    
    if produto:
        nome_alvo = produto.get("nome", "")
        dosagem_alvo = produto.get("dosagem", "")
        ativo_alvo = produto.get("principio_ativo", "")
        apresentacao_alvo = produto.get("apresentacao", "")
        fabricante_padrao = produto.get("fabricante", "") or "Marca"
        ean = str(produto.get("ean", "")).strip()
        if produto.get("url_pacheco"):
            url = produto["url_pacheco"]

    # Tier 1: Busca pelo código de barras EAN oficial
    if ean and ean not in ("0", ""):
        res_ean = consultar_vtex_ean("www.drogariaspacheco.com.br", ean)
        if res_ean and validar_candidato(res_ean["produto"], nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
            return {
                "sucesso": True,
                "drogaria": "Drogarias Pacheco",
                "filial": "Rua Conde de Bonfim, 580 — Tijuca",
                "produto": res_ean["produto"],
                "laboratorio": res_ean.get("laboratorio") or fabricante_padrao,
                "preco_online": res_ean["preco_online"],
                "preco_referencia": res_ean["preco_referencia"],
                "disponivel": res_ean["disponivel"],
                "estoque_status": "Não confirmado" if res_ean["disponivel"] else "Indisponível",
                "sku": res_ean["sku"],
                "url": res_ean["url"] or url or "",
                "promocao": res_ean.get("promocao"),
                "data_hora": get_sp_time()
            }

    # Tier 2: Acesso direto à URL do produto na Pacheco
    if url and "drogariaspacheco.com.br" in url:
        try:
            resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=12)
            if resp.status_code == 200 and "ProductLinkNotFound" not in resp.url:
                preco_online, preco_referencia, nome_prod, sku_id, disponivel, lab = extrair_preco_html(resp.text)
                if preco_online and preco_online > 0:
                    nome_final = nome_prod or nome_alvo
                    if validar_candidato(nome_final, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
                        return {
                            "sucesso": True,
                            "drogaria": "Drogarias Pacheco",
                            "filial": "Rua Conde de Bonfim, 580 — Tijuca",
                            "produto": nome_final,
                            "laboratorio": lab or fabricante_padrao,
                            "preco_online": round(preco_online, 2),
                            "preco_referencia": round(preco_referencia, 2) if preco_referencia else None,
                            "disponivel": disponivel,
                            "estoque_status": "Não confirmado" if disponivel else "Indisponível",
                            "sku": sku_id or "",
                            "url": resp.url,
                            "promocao": None,
                            "data_hora": get_sp_time()
                        }
        except Exception:
            pass

    # Tier 3: Busca textual no catálogo da Pacheco com termo limpo e validação
    termo = limpar_termo_busca(nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    res_busca = consultar_vtex_search("www.drogariaspacheco.com.br", termo, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    if res_busca:
        return {
            "sucesso": True,
            "drogaria": "Drogarias Pacheco",
            "filial": "Rua Conde de Bonfim, 580 — Tijuca",
            "produto": res_busca["produto"],
            "laboratorio": res_busca.get("laboratorio") or fabricante_padrao,
            "preco_online": res_busca["preco_online"],
            "preco_referencia": res_busca["preco_referencia"],
            "disponivel": res_busca["disponivel"],
            "estoque_status": "Não confirmado" if res_busca["disponivel"] else "Indisponível",
            "sku": res_busca["sku"],
            "url": res_busca["url"],
            "promocao": res_busca.get("promocao"),
            "data_hora": get_sp_time()
        }

    return {
        "sucesso": False,
        "drogaria": "Drogarias Pacheco",
        "erro": f"Medicamento não localizado para '{termo}' nas Drogarias Pacheco."
    }

def consultar_venancio(ean: str = "", produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nome_alvo = "Puran T4"
    dosagem_alvo = ""
    ativo_alvo = ""
    apresentacao_alvo = ""
    fabricante_padrao = "Marca"
    url = None

    if produto:
        nome_alvo = produto.get("nome", "")
        dosagem_alvo = produto.get("dosagem", "")
        ativo_alvo = produto.get("principio_ativo", "")
        apresentacao_alvo = produto.get("apresentacao", "")
        fabricante_padrao = produto.get("fabricante", "") or "Marca"
        ean = str(produto.get("ean", "")).strip()
        if produto.get("url_venancio"):
            url = produto["url_venancio"]

    # Tier 1: Busca pelo código de barras EAN oficial
    if ean and ean not in ("0", ""):
        res_ean = consultar_vtex_ean("www.drogariavenancio.com.br", ean)
        if res_ean and validar_candidato(res_ean["produto"], nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
            return {
                "sucesso": True,
                "drogaria": "Drogaria Venancio",
                "filial": "Rua Conde de Bonfim, 532 — Tijuca",
                "produto": res_ean["produto"],
                "laboratorio": res_ean.get("laboratorio") or fabricante_padrao,
                "preco_online": res_ean["preco_online"],
                "preco_referencia": res_ean["preco_referencia"],
                "disponivel": res_ean["disponivel"],
                "estoque_status": "Não confirmado" if res_ean["disponivel"] else "Indisponível",
                "sku": res_ean["sku"],
                "url": res_ean["url"] or url or "",
                "promocao": res_ean.get("promocao"),
                "data_hora": get_sp_time()
            }

    # Tier 2: Acesso direto à URL do produto na Venancio
    if url and "drogariavenancio.com.br" in url:
        try:
            resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=12)
            if resp.status_code == 200 and "ProductLinkNotFound" not in resp.url:
                preco_online, preco_referencia, nome_prod, sku_id, disponivel, lab = extrair_preco_html(resp.text)
                if preco_online and preco_online > 0:
                    nome_final = nome_prod or nome_alvo
                    if validar_candidato(nome_final, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
                        return {
                            "sucesso": True,
                            "drogaria": "Drogaria Venancio",
                            "filial": "Rua Conde de Bonfim, 532 — Tijuca",
                            "produto": nome_final,
                            "laboratorio": lab or fabricante_padrao,
                            "preco_online": round(preco_online, 2),
                            "preco_referencia": round(preco_referencia, 2) if preco_referencia else None,
                            "disponivel": disponivel,
                            "estoque_status": "Não confirmado" if disponivel else "Indisponível",
                            "sku": sku_id or "",
                            "url": resp.url,
                            "promocao": None,
                            "data_hora": get_sp_time()
                        }
        except Exception:
            pass

    # Tier 3: Busca textual no catálogo da Venancio com termo limpo e validação
    termo = limpar_termo_busca(nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    res_busca = consultar_vtex_search("www.drogariavenancio.com.br", termo, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    if res_busca:
        return {
            "sucesso": True,
            "drogaria": "Drogaria Venancio",
            "filial": "Rua Conde de Bonfim, 532 — Tijuca",
            "produto": res_busca["produto"],
            "laboratorio": res_busca.get("laboratorio") or fabricante_padrao,
            "preco_online": res_busca["preco_online"],
            "preco_referencia": res_busca["preco_referencia"],
            "disponivel": res_busca["disponivel"],
            "estoque_status": "Não confirmado" if res_busca["disponivel"] else "Indisponível",
            "sku": res_busca["sku"],
            "url": res_busca["url"],
            "promocao": res_busca.get("promocao"),
            "data_hora": get_sp_time()
        }

    return {
        "sucesso": False,
        "drogaria": "Drogaria Venancio",
        "erro": f"Medicamento não localizado para '{termo}' na Drogaria Venancio."
    }

def consultar_drogasmil(url: Optional[str] = None, produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    nome_alvo = "Puran T4"
    dosagem_alvo = ""
    ativo_alvo = ""
    apresentacao_alvo = ""
    fabricante_padrao = "Marca"
    ean = ""

    if produto:
        nome_alvo = produto.get("nome", "")
        dosagem_alvo = produto.get("dosagem", "")
        ativo_alvo = produto.get("principio_ativo", "")
        apresentacao_alvo = produto.get("apresentacao", "")
        fabricante_padrao = produto.get("fabricante", "") or "Marca"
        ean = str(produto.get("ean", "")).strip()
        if produto.get("url_drogasmil"):
            url = produto["url_drogasmil"]

    # Tier 1: Busca pelo código de barras EAN oficial
    if ean and ean not in ("0", ""):
        res_ean = consultar_vtex_ean("www.drogasmil.com.br", ean)
        if res_ean and validar_candidato(res_ean["produto"], nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
            return {
                "sucesso": True,
                "drogaria": "Drogasmil",
                "filial": "Praça Saenz Peña, 29 — Tijuca",
                "produto": res_ean["produto"],
                "laboratorio": res_ean.get("laboratorio") or fabricante_padrao,
                "preco_online": res_ean["preco_online"],
                "preco_referencia": res_ean["preco_referencia"],
                "disponivel": res_ean["disponivel"],
                "estoque_status": "Não confirmado" if res_ean["disponivel"] else "Indisponível",
                "sku": res_ean["sku"],
                "url": res_ean["url"] or url or "",
                "promocao": res_ean.get("promocao"),
                "data_hora": get_sp_time()
            }

    # Tier 2: Acesso direto à URL do produto na Drogasmil
    if url and "drogasmil.com.br" in url:
        try:
            resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=12)
            if resp.status_code == 200 and "ProductLinkNotFound" not in resp.url:
                preco_online, preco_referencia, nome_prod, sku_id, disponivel, lab = extrair_preco_html(resp.text)
                if preco_online and preco_online > 0:
                    nome_final = nome_prod or nome_alvo
                    if validar_candidato(nome_final, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo):
                        return {
                            "sucesso": True,
                            "drogaria": "Drogasmil",
                            "filial": "Praça Saenz Peña, 29 — Tijuca",
                            "produto": nome_final,
                            "laboratorio": lab or fabricante_padrao,
                            "preco_online": round(preco_online, 2),
                            "preco_referencia": round(preco_referencia, 2) if preco_referencia else None,
                            "disponivel": disponivel,
                            "estoque_status": "Não confirmado" if disponivel else "Indisponível",
                            "sku": sku_id or "",
                            "url": resp.url,
                            "promocao": None,
                            "data_hora": get_sp_time()
                        }
        except Exception:
            pass

    # Tier 3: Busca textual no catálogo da Drogasmil com termo limpo e validação
    termo = limpar_termo_busca(nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    res_busca = consultar_vtex_search("www.drogasmil.com.br", termo, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo)
    if res_busca:
        return {
            "sucesso": True,
            "drogaria": "Drogasmil",
            "filial": "Praça Saenz Peña, 29 — Tijuca",
            "produto": res_busca["produto"],
            "laboratorio": res_busca.get("laboratorio") or fabricante_padrao,
            "preco_online": res_busca["preco_online"],
            "preco_referencia": res_busca["preco_referencia"],
            "disponivel": res_busca["disponivel"],
            "estoque_status": "Não confirmado" if res_busca["disponivel"] else "Indisponível",
            "sku": res_busca["sku"],
            "url": res_busca["url"],
            "promocao": res_busca.get("promocao"),
            "data_hora": get_sp_time()
        }

    return {
        "sucesso": False,
        "drogaria": "Drogasmil",
        "erro": f"Medicamento não localizado para '{termo}' na Drogasmil."
    }

def consultar_todas_automaticas(produto: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "pacheco": consultar_pacheco(produto=produto),
        "venancio": consultar_venancio(produto=produto),
        "drogasmil": consultar_drogasmil(produto=produto)
    }

def consultar_precos_laboratorios(principio_ativo: str, dosagem: str = "", apresentacao: str = "") -> Dict[str, Any]:
    termo = limpar_termo_busca(principio_ativo, dosagem)
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
        if not validar_candidato(nome_prod, principio_ativo, dosagem, principio_ativo):
            continue

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

        # Identificar quantidade de comprimidos/cápsulas para cálculo unitário justo
        m_qtd = re.findall(r'(\d+)\s*(?:comprimidos?|comp|cpr|c[aá]psulas?|caps?|unidades?|un)', nome_prod.lower())
        qtd_unidades = int(m_qtd[0]) if m_qtd else 30
        preco_unitario = round(price / max(1, qtd_unidades), 2)

        nome_lower = nome_prod.lower()
        if "generico" in nome_lower or "genérico" in nome_lower:
            categoria = "Genérico"
        elif any(ref in brand.lower() for ref in ["sanofi", "abbott", "merck", "pfizer", "novartis", "bayer", "roche", "gsk"]):
            categoria = "Referência"
        elif any(gen in brand.lower() for gen in ["ems", "medley", "eurofarma", "neo quimica", "teuto", "prati", "germed", "biosintetica", "ranbaxy"]):
            categoria = "Genérico"
        else:
            categoria = "Similar"

        item_dict = {
            "laboratorio": brand,
            "nome_produto": nome_prod,
            "preco": price,
            "preco_referencia": list_price,
            "preco_por_unidade": preco_unitario,
            "quantidade_unidades": qtd_unidades,
            "qtd_unidades": qtd_unidades,
            "unidade_medida": "comp",
            "categoria": categoria,
            "disponivel": available,
            "ean": ean,
            "drogaria": "Drogaria Venancio",
            "url": link
        }

        # Chave por marca e quantidade para permitir comparar embalagens de 30 e 60 separadamente
        chave = f"{brand}_{qtd_unidades}"
        if chave not in mapa_lab or price < mapa_lab[chave]["preco"]:
            mapa_lab[chave] = item_dict

    lista_labs = list(mapa_lab.values())
    if not lista_labs:
        return {"sucesso": False, "mensagem": f"Nenhum laboratório compatível com a dosagem '{dosagem}' encontrado.", "laboratorios": []}

    # Ordenar por preço unitário (custo por comprimido), permitindo comparação justa entre 30 e 60 comp
    lista_labs.sort(key=lambda x: x["preco_por_unidade"])
    mais_caro = max(lista_labs, key=lambda x: x["preco_por_unidade"])
    mais_barato = lista_labs[0]

    for lab in lista_labs:
        dif_unit = round(mais_caro["preco_por_unidade"] - lab["preco_por_unidade"], 2)
        pct = round((dif_unit / mais_caro["preco_por_unidade"]) * 100, 1) if mais_caro["preco_por_unidade"] > 0 else 0.0
        lab["economia_reais"] = dif_unit
        lab["economia_pct"] = pct

    return {
        "sucesso": True,
        "termo": termo,
        "total_laboratorios": len(lista_labs),
        "laboratorio_mais_barato": mais_barato,
        "laboratorio_mais_caro": mais_caro,
        "diferenca_maxima": round(mais_caro["preco_por_unidade"] - mais_barato["preco_por_unidade"], 2),
        "economia_maxima_pct": mais_barato["economia_pct"],
        "laboratorios": lista_labs
    }
