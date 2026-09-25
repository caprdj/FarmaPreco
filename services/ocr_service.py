import re
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from PIL import Image

try:
    import winocr
    WINOCR_AVAILABLE = True
except ImportError:
    WINOCR_AVAILABLE = False

from services.storage import carregar_produtos

async def extrair_texto_imagem_async(caminho_imagem: Path) -> str:
    if not WINOCR_AVAILABLE:
        return ""
    try:
        img = Image.open(caminho_imagem)
        # Tenta português primeiro, depois inglês
        try:
            result = await winocr.recognize_pil(img, lang="pt")
            return result.text
        except Exception:
            result = await winocr.recognize_pil(img, lang="en")
            return result.text
    except Exception as e:
        print(f"[OCR] Erro ao extrair texto: {e}")
        return ""

def extrair_texto_imagem(caminho_imagem: Path) -> str:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se já estiver rodando em loop assíncrono (FastAPI), cria nova thread ou executa
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, extrair_texto_imagem_async(caminho_imagem))
                return future.result()
        else:
            return asyncio.run(extrair_texto_imagem_async(caminho_imagem))
    except Exception:
        return asyncio.run(extrair_texto_imagem_async(caminho_imagem))

def analisar_print_raia(caminho_imagem: Path, produto_id_hint: Optional[str] = None) -> Dict[str, Any]:
    texto = extrair_texto_imagem(caminho_imagem)
    produtos = carregar_produtos()
    
    # Encontrar produto mais provável
    produto_identificado = None
    if produto_id_hint:
        for p in produtos:
            if p["produto_id"] == produto_id_hint:
                produto_identificado = p
                break

    if not produto_identificado and texto:
        texto_lower = texto.lower()
        pontuacoes = []
        for p in produtos:
            score = 0
            nome_p = p["nome"].lower()
            ativo_p = p["principio_ativo"].lower()
            dosagem_p = p["dosagem"].lower()
            fab_p = p["fabricante"].lower()
            
            # Palavras-chave específicas
            keywords = [
                k.strip().lower() for k in 
                nome_p.replace("(", " ").replace(")", " ").replace("/", " ").split() 
                if len(k.strip()) > 3
            ]
            
            for kw in keywords:
                if kw in texto_lower:
                    score += 3
            if ativo_p and any(w in texto_lower for w in ativo_p.split() if len(w) > 4):
                score += 2
            if dosagem_p.replace(" ", "") in texto_lower.replace(" ", ""):
                score += 2
            if fab_p and any(f in texto_lower for f in ["sanofi", "medley", "eurofarma", "ems", "aché", "ache", "biolab", "hypera", "lisador", "novalgina"]):
                score += 1
                
            pontuacoes.append((score, p))
            
        pontuacoes.sort(key=lambda x: x[0], reverse=True)
        if pontuacoes and pontuacoes[0][0] > 0:
            produto_identificado = pontuacoes[0][1]

    # Extrair valores monetários do texto
    # Padrão: R$ 29,90 ou 29,90 ou R$29.90
    precos_encontrados: List[float] = []
    
    # Procura valores precedidos por R$ ou R$
    matches_r = re.findall(r"R\$\s*(\d{1,4}[,\.]\d{2})", texto, re.IGNORECASE)
    for m in matches_r:
        try:
            val = float(m.replace(".", "").replace(",", "."))
            if 1.0 <= val <= 2000.0 and val not in precos_encontrados:
                precos_encontrados.append(val)
        except ValueError:
            pass

    # Se não achou com R$, procura decimais soltos
    if not precos_encontrados:
        matches_num = re.findall(r"\b(\d{1,3}[,\.]\d{2})\b", texto)
        for m in matches_num:
            try:
                val = float(m.replace(".", "").replace(",", "."))
                if 4.0 <= val <= 1000.0 and val not in precos_encontrados:
                    precos_encontrados.append(val)
            except ValueError:
                pass

    # Detectar promoção por quantidade (ex: Leve 4 por 26.09 cada ou a partir de 3 unidades)
    promo_qtd = None
    promo_preco = None
    match_leve = re.search(r"leve\s*(\d+)[^\d]+(?:por|cada|R\$)\s*(\d{1,4}[,\.]\d{2})", texto, re.IGNORECASE)
    if match_leve:
        try:
            promo_qtd = int(match_leve.group(1))
            promo_preco = float(match_leve.group(2).replace(".", "").replace(",", "."))
        except (ValueError, IndexError):
            pass

    if not promo_qtd:
        match_partir = re.search(r"a\s*partir\s*de\s*(\d+)\s*unidades?[^\d]+(?:por|cada|R\$)?\s*(\d{1,4}[,\.]\d{2})", texto, re.IGNORECASE)
        if match_partir:
            try:
                promo_qtd = int(match_partir.group(1))
                promo_preco = float(match_partir.group(2).replace(".", "").replace(",", "."))
            except (ValueError, IndexError):
                pass

    preco_sugerido = precos_encontrados[0] if precos_encontrados else None
    
    # Se achou promoção e o preço sugerido é igual ao da promoção, tenta achar outro para o unitário
    if promo_preco and preco_sugerido == promo_preco and len(precos_encontrados) > 1:
        preco_sugerido = max(precos_encontrados)

    # Identificar laboratório citado no print
    lab_sugerido = None
    texto_upper = texto.upper()
    for lab_cand in ["SANOFI", "NOVALGINA", "LISADOR", "HYPERA", "MEDLEY", "EUROFARMA", "EMS", "ACHÉ", "ACHE", "BIOLAB", "NEO QUÍMICA", "NEO QUIMICA", "PRATI"]:
        if lab_cand in texto_upper:
            if lab_cand in ("NOVALGINA", "SANOFI"):
                lab_sugerido = "Sanofi (Novalgina)" if produto_identificado and "dipirona" in produto_identificado["nome"].lower() else "Sanofi"
            elif lab_cand in ("LISADOR", "HYPERA"):
                lab_sugerido = "Hypera (Lisador)"
            elif lab_cand in ("ACHÉ", "ACHE"):
                lab_sugerido = "Aché"
            else:
                lab_sugerido = lab_cand.title()
            break

    return {
        "sucesso": True,
        "texto_extraido": texto,
        "produto_id": produto_identificado["produto_id"] if produto_identificado else (produto_id_hint or "MED001"),
        "produto_nome": produto_identificado["nome"] if produto_identificado else "",
        "preco_unitario_sugerido": preco_sugerido,
        "precos_candidatos": precos_encontrados,
        "promocao_qtd": promo_qtd,
        "promocao_preco": promo_preco,
        "laboratorio_sugerido": lab_sugerido or (produto_identificado.get("fabricante") if produto_identificado else "Droga Raia"),
        "caminho_imagem": str(caminho_imagem)
    }
