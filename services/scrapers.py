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
    """Verifica se a palavra existe como termo inteiro no texto, normalizando variações de catálogo."""
    p_norm = palavra.lower().replace("quetiapiana", "quetiapina")
    t_norm = texto.lower().replace("quetiapiana", "quetiapina")
    padrao = r'(?:^|[^\w])' + re.escape(p_norm) + r'(?:$|[^\w])'
    return bool(re.search(padrao, t_norm, re.IGNORECASE))

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

TERMOS_GENERICOS = {
    "shampoo", "condicionador", "sabonete", "solucao", "solução", "creme", "gel",
    "pomada", "tonico", "tônico", "locao", "loção", "spray", "gotas", "capsula",
    "capsulas", "cápsula", "cápsulas", "comprimido", "comprimidos", "comp", "cpr",
    "frasco", "frascos", "kit", "refil", "oleo", "óleo", "serum", "sérum", "fortalecedor",
    "fortalecedora", "hidratante", "limpeza", "facial", "capilar", "antiqueda",
    "anticaspa", "engrossador", "reparador", "anti-idade", "antiidade", "corporal",
    "intimo", "íntimo", "protetor", "solar", "fps", "tratamento", "uso", "diario",
    "diário", "infantil", "adulto", "unidades", "unidade", "un", "cx", "caixa",
    "caixas", "original", "tradicional", "plus", "extra", "suave",
    "intenso", "concentrado", "cuidado", "cuidados", "cor", "clara", "tom", "generico",
    "genérico", "similar", "liquido", "líquido", "com", "para", "dosador", "lata", "azul",
    "medicamento", "revestidos", "liberacao", "prolongada", "acao", "rápida", "rapida"
}

def extrair_tokens_obrigatorios(nome_buscado: str, principio_ativo: str = "", fabricante: str = "") -> List[set]:
    """Retorna listas de tokens distintivos de cada alternativa do produto."""
    texto_total = f"{nome_buscado} / {principio_ativo}"
    opcoes = re.split(r"[/,;()]+", texto_total)
    
    conjuntos_opcoes = []
    for op in opcoes:
        palavras = [w for w in re.findall(r"[a-záéíóúãõâêîôûç0-9]+", op.lower()) if len(w) >= 3 and not w.isdigit()]
        distintivas = [w for w in palavras if w not in TERMOS_GENERICOS]
        if distintivas:
            conjuntos_opcoes.append(set(distintivas))
            
    if fabricante and str(fabricante).lower() not in ("generico", "genérico", "similar", "marca", "referencia", "referência", "outros", "não informado"):
        for fab_part in re.split(r"[/,;()]+", str(fabricante)):
            fabs = [w for w in re.findall(r"[a-záéíóúãõâêîôûç]+", fab_part.lower()) if len(w) >= 3 and w not in TERMOS_GENERICOS]
            if fabs:
                conjuntos_opcoes.append(set(fabs))
            
    return conjuntos_opcoes

def validar_candidato(
    nome_candidato: str,
    nome_buscado: str,
    dosagem_buscada: str = "",
    principio_ativo: str = "",
    apresentacao_buscada: str = "",
    fabricante_buscado: str = "",
    brand_candidato: str = ""
) -> bool:
    """Valida com rigor estrito se o produto retornado corresponde ao medicamento ou dermocosmético desejado."""
    if not nome_candidato:
        return False
    c_lower = nome_candidato.lower()
    b_lower = (brand_candidato or "").lower()
    texto_cand = f"{c_lower} {b_lower}"
    
    # 1. Tokens distintivos obrigatórios (marcas, patentes ou princípios ativos)
    opcoes_tokens = extrair_tokens_obrigatorios(nome_buscado, principio_ativo, fabricante_buscado)
    if opcoes_tokens:
        casou_alguma_opcao = False
        for conjunto in opcoes_tokens:
            if all(contem_palavra_exata(tok, texto_cand) for tok in conjunto):
                casou_alguma_opcao = True
                break
        if not casou_alguma_opcao:
            return False

    # 2. Incompatibilidade direta de forma farmacêutica / tipo
    nb_lower = nome_buscado.lower()
    if "condicionador" in nb_lower and "shampoo" in c_lower and "condicionador" not in c_lower:
        return False
    if "shampoo" in nb_lower and "condicionador" in c_lower and "shampoo" not in c_lower:
        return False
    if any(k in nb_lower for k in ["solucao", "solução", "locao", "loção", "tonico", "tônico"]) and "shampoo" in c_lower and not any(k in c_lower for k in ["solucao", "solução", "locao", "loção", "tonico", "tônico"]):
        return False
    if "shampoo" in nb_lower and any(k in c_lower for k in ["locao", "loção", "tonico", "tônico"]) and "shampoo" not in c_lower:
        return False
    if ("íntimo" in nb_lower or "intimo" in nb_lower) and ("íntimo" not in c_lower and "intimo" not in c_lower):
        return False
    if "refil" not in nb_lower and "refil" in c_lower:
        return False
    # Kits: se o produto buscado não é kit, rejeita kits de múltiplos frascos
    if "kit" not in nb_lower and "kit" in c_lower:
        return False
    if "kit" in nb_lower and "kit" not in c_lower and not any(u in c_lower for u in ["2 unidades", "2 un", "2 frascos", "combo", "duo", "pack"]):
        return False

    # 3. Dosagem estrita (ex: 300mg não pode casar com 150mg)
    if dosagem_buscada:
        d_alvo = dosagem_buscada.lower().replace(" ", "").replace("µg", "mcg")
        d_candidato = [x.replace(" ", "").replace("µg", "mcg") for x in re.findall(r"(\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ui|ml|fps))", c_lower)]
        if d_candidato and d_alvo not in d_candidato:
            return False

    # 4. Volume ou Quantidade de comprimidos (30 comp vs 60 comp, 200ml vs 400ml)
    alvo_vols = extrair_volume_ou_qtd(f"{nome_buscado} {dosagem_buscada} {apresentacao_buscada}")
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

def calcular_score_relevancia(
    cand: Dict[str, Any],
    nome_alvo: str,
    dosagem_alvo: str = "",
    ativo_alvo: str = "",
    apresentacao_alvo: str = "",
    fabricante_alvo: str = ""
) -> float:
    score = 0.0
    c_nome = cand["produto"].lower()
    c_brand = (cand.get("laboratorio") or "").lower()
    texto_total = f"{c_nome} {c_brand}"
    
    # 1. Tokens distintivos presentes
    opcoes = extrair_tokens_obrigatorios(nome_alvo, ativo_alvo, fabricante_alvo)
    for conjunto in opcoes:
        if all(contem_palavra_exata(tok, texto_total) for tok in conjunto):
            score += 50.0
            break

    # 2. Fabricante / Brand match
    if fabricante_alvo and str(fabricante_alvo).lower() not in ("generico", "genérico", "similar", "marca", "referencia", "referência", "outros", "não informado"):
        fab_tokens = [f.lower() for f in re.split(r"[\s/]+", str(fabricante_alvo)) if len(f) >= 3 and f.lower() not in TERMOS_GENERICOS]
        if any(ft in c_brand or ft in c_nome for ft in fab_tokens):
            score += 30.0

    # 3. Volume / Quantidade exata match
    alvo_vols = extrair_volume_ou_qtd(f"{nome_alvo} {dosagem_alvo} {apresentacao_alvo}")
    cand_vols = extrair_volume_ou_qtd(c_nome)
    if alvo_vols and cand_vols and (alvo_vols & cand_vols):
        score += 20.0
        
    return score

def consultar_vtex_search(
    domain: str,
    termo: str,
    nome_alvo: str,
    dosagem_alvo: str = "",
    ativo_alvo: str = "",
    apresentacao_alvo: str = "",
    fabricante_alvo: str = ""
) -> Optional[Dict[str, Any]]:
    """Busca textual no catálogo VTEX aplicando validação estrita e ordenação por relevância garantida."""
    try:
        url = f"https://{domain}/api/catalog_system/pub/products/search/{urllib.parse.quote(termo)}"
        resp = requests.get(url, headers=HEADERS_DEFAULT, timeout=15)
        if resp.status_code in (200, 206):
            produtos = resp.json()
            if isinstance(produtos, list) and produtos:
                candidatos_validos = []
                for p in produtos:
                    pname = p.get("productName", "")
                    pbrand = p.get("brand", "")
                    if not validar_candidato(
                        nome_candidato=pname,
                        nome_buscado=nome_alvo,
                        dosagem_buscada=dosagem_alvo,
                        principio_ativo=ativo_alvo,
                        apresentacao_buscada=apresentacao_alvo,
                        fabricante_buscado=fabricante_alvo,
                        brand_candidato=pbrand
                    ):
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
                                    "laboratorio": pbrand or "",
                                    "preco_online": preco_float,
                                    "preco_referencia": round(float(offer.get("ListPrice")), 2) if offer.get("ListPrice") else None,
                                    "disponivel": bool(offer.get("IsAvailable", True)),
                                    "sku": str(sku.get("itemId", "")),
                                    "url": p.get("link") or "",
                                    "promocao": promo
                                }
                                score = calcular_score_relevancia(
                                    item_candidato, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_alvo
                                )
                                item_candidato["score"] = score
                                candidatos_validos.append(item_candidato)

                if candidatos_validos:
                    candidatos_validos.sort(key=lambda x: (-x["score"], x["preco_online"]))
                    melhor = candidatos_validos[0]
                    if melhor["score"] >= 30.0 or not extrair_tokens_obrigatorios(nome_alvo, ativo_alvo, fabricante_alvo):
                        return melhor
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
        if res_ean and validar_candidato(res_ean["produto"], nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao, res_ean.get("laboratorio", "")):
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
                    if validar_candidato(nome_final, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao, lab or ""):
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
    res_busca = consultar_vtex_search("www.drogariaspacheco.com.br", termo, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao)
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
        if res_ean and validar_candidato(res_ean["produto"], nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao, res_ean.get("laboratorio", "")):
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
                    if validar_candidato(nome_final, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao, lab or ""):
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
    res_busca = consultar_vtex_search("www.drogariavenancio.com.br", termo, nome_alvo, dosagem_alvo, ativo_alvo, apresentacao_alvo, fabricante_padrao)
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
        "venancio": consultar_venancio(produto=produto)
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
