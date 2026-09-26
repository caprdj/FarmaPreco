import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form, BackgroundTasks, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from services.scrapers import (
    consultar_pacheco,
    consultar_venancio,
    consultar_drogasmil,
    consultar_todas_automaticas,
    consultar_precos_laboratorios,
    get_sp_time
)
from services.storage import (
    carregar_historico,
    salvar_registro,
    salvar_multiplos_registros,
    gerar_relatorio_csv,
    carregar_produtos,
    obter_produto_por_id,
    cadastrar_produto,
    atualizar_produto,
    excluir_produto,
    carregar_drogarias,
    inicializar_arquivos_se_necessario,
    PASTA_PRINTS,
    obter_status_prints_raia
)
from services.comparator import comparar_precos
from services.ocr_service import analisar_print_raia

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="FarmaPreço - Comparador de Medicamentos na Tijuca")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/prints/raia", StaticFiles(directory=str(PASTA_PRINTS)), name="prints_raia")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/manifest.json")
def get_manifest():
    return FileResponse(str(STATIC_DIR / "manifest.json"), media_type="application/manifest+json")

@app.get("/sw.js")
def get_sw():
    return FileResponse(str(STATIC_DIR / "sw.js"), media_type="application/javascript")

inicializar_arquivos_se_necessario()

class RegistroManual(BaseModel):
    drogaria: str
    filial: str
    modalidade: str
    condicao_preco: str
    valor_total: float
    quantidade_caixas: int = 1
    frete: float = 0.0
    estoque: str = "Não confirmado"
    fonte: str = "Manual"
    url: str = ""
    observacoes: str = ""
    produto_id: str = "MED001"

class NovoProduto(BaseModel):
    nome: str
    principio_ativo: str = ""
    dosagem: str = ""
    apresentacao: str = ""
    fabricante: str = ""
    categoria: str = "Outros"
    quantidade_mensal: int = 1
    ean: str = ""
    url_pacheco: str = ""
    url_venancio: str = ""
    url_drogasmil: str = ""
    url_raia: str = ""

class EditarProduto(BaseModel):
    nome: Optional[str] = None
    principio_ativo: Optional[str] = None
    dosagem: Optional[str] = None
    apresentacao: Optional[str] = None
    fabricante: Optional[str] = None
    categoria: Optional[str] = None
    quantidade_mensal: Optional[int] = None
    ean: Optional[str] = None
    url_pacheco: Optional[str] = None
    url_venancio: Optional[str] = None
    url_drogasmil: Optional[str] = None
    url_raia: Optional[str] = None

class ConfirmarPrecoRaia(BaseModel):
    produto_id: str
    preco_comum: float
    laboratorio: str = "Droga Raia"
    estoque: str = "Disponível para retirada"
    tem_promo: bool = False
    qtd_promo: int = 1
    preco_promo: float = 0.0
    url_comprovante: str = ""
    observacoes: str = ""

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, produto_id: Optional[str] = None):
    produtos = carregar_produtos()
    produtos_ordenados = sorted(produtos, key=lambda x: str(x.get("nome", "")).lower())
    drogarias = carregar_drogarias()
    
    prod_principal = None
    if produto_id:
        prod_principal = obter_produto_por_id(produto_id)
    if not prod_principal and produtos_ordenados:
        prod_principal = produtos_ordenados[0]
        
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "produto": prod_principal or {},
            "produtos": produtos_ordenados,
            "drogarias": drogarias
        }
    )

@app.get("/api/produtos")
async def api_listar_produtos():
    produtos = carregar_produtos()
    produtos_ordenados = sorted(produtos, key=lambda x: str(x.get("nome", "")).lower())
    return JSONResponse(produtos_ordenados)

@app.post("/api/produtos")
async def api_cadastrar_produto(dados: NovoProduto):
    novo = cadastrar_produto(dados.model_dump())
    return JSONResponse({"sucesso": True, "produto": novo})

@app.get("/api/produtos/{produto_id}")
async def api_obter_produto(produto_id: str):
    produto = obter_produto_por_id(produto_id)
    if produto:
        return JSONResponse(produto)
    return JSONResponse({"sucesso": False, "mensagem": "Produto não encontrado"}, status_code=404)

@app.put("/api/produtos/{produto_id}")
@app.post("/api/produtos/{produto_id}/editar")
async def api_editar_produto(produto_id: str, dados: EditarProduto):
    atualizado = atualizar_produto(produto_id, {k: v for k, v in dados.model_dump().items() if v is not None})
    if atualizado:
        return JSONResponse({"sucesso": True, "produto": atualizado})
    return JSONResponse({"sucesso": False, "mensagem": "Produto não encontrado"}, status_code=404)

@app.delete("/api/produtos/{produto_id}")
async def api_excluir_produto(produto_id: str):
    sucesso = excluir_produto(produto_id)
    return JSONResponse({"sucesso": sucesso})

@app.get("/api/comparar")
async def api_comparar(
    quantidade: int = 1,
    somente_confirmado: bool = False,
    modalidade: str = "todas",
    produto_id: str = "MED001"
):
    resultado = comparar_precos(
        quantidade_desejada=quantidade,
        somente_confirmado=somente_confirmado,
        filtro_modalidade=modalidade,
        produto_id=produto_id
    )
    return JSONResponse(resultado)

@app.get("/api/laboratorios/comparar")
async def api_comparar_laboratorios(principio_ativo: str, dosagem: str = ""):
    resultado = consultar_precos_laboratorios(principio_ativo=principio_ativo, dosagem=dosagem)
    return JSONResponse(resultado)

@app.get("/api/cesta-mensal")
async def api_cesta_mensal():
    produtos = carregar_produtos()
    itens = []
    total_otimizado = 0.0
    totais_por_drogaria = {
        "Drogaria Venancio": 0.0,
        "Drogarias Pacheco": 0.0,
        "Drogasmil": 0.0,
        "Droga Raia": 0.0
    }
    itens_cotados_por_drogaria = {
        "Drogaria Venancio": 0,
        "Drogarias Pacheco": 0,
        "Drogasmil": 0,
        "Droga Raia": 0
    }

    status_raia = obter_status_prints_raia()
    status_raia_map = {s["produto_id"]: s for s in status_raia}

    for p in produtos:
        pid = p["produto_id"]
        qtd = int(p.get("quantidade_mensal", 1) or 1)
        comp = comparar_precos(quantidade_desejada=qtd, produto_id=pid)
        
        melhor = comp.get("melhor_opcao")
        preco_otimizado = melhor["total_estimado"] if melhor else 0.0
        drogaria_otimizada = melhor["drogaria"] if melhor else "Pendente"
        total_otimizado += preco_otimizado
        
        precos_farmacias = {}
        detalhes_farmacias = {}
        for of in comp.get("ofertas", []):
            drog = of["drogaria"]
            if drog not in precos_farmacias:
                precos_farmacias[drog] = of["total_estimado"]
                detalhes_farmacias[drog] = {
                    "total": of["total_estimado"],
                    "unitario": of["custo_por_caixa"],
                    "laboratorio": of.get("laboratorio", ""),
                    "is_raia": of.get("is_raia", False),
                    "expirado_3dias": of.get("expirado_3dias", False),
                    "dias_desde_upload": of.get("dias_desde_upload", 0.0),
                    "url": of.get("url", "")
                }
                totais_por_drogaria[drog] = round(totais_por_drogaria.get(drog, 0.0) + of["total_estimado"], 2)
                itens_cotados_por_drogaria[drog] = itens_cotados_por_drogaria.get(drog, 0) + 1

        info_raia = status_raia_map.get(pid, {})

        itens.append({
            "produto_id": pid,
            "nome": p["nome"],
            "dosagem": p["dosagem"],
            "fabricante": p["fabricante"],
            "apresentacao": p["apresentacao"],
            "quantidade_mensal": qtd,
            "melhor_preco": preco_otimizado,
            "melhor_farmacia": drogaria_otimizada,
            "precos_farmacias": precos_farmacias,
            "detalhes_farmacias": detalhes_farmacias,
            "status_raia": info_raia
        })
        
    prints_expirados_total = sum(1 for s in status_raia if s["expirado"])

    return JSONResponse({
        "sucesso": True,
        "total_medicamentos": len(itens),
        "total_mensal_otimizado": round(total_otimizado, 2),
        "totais_por_drogaria": totais_por_drogaria,
        "itens_cotados_por_drogaria": itens_cotados_por_drogaria,
        "itens": itens,
        "status_raia": status_raia,
        "raia_total_expirados": prints_expirados_total,
        "tem_raia_expirada": prints_expirados_total > 0
    })

@app.post("/api/coletar/todas")
async def api_coletar_todas(produto_id: str = "MED001"):
    produto = obter_produto_por_id(produto_id)
    resultados = consultar_todas_automaticas(produto=produto)
    registros_para_salvar = []
    detalhes = []

    # 1. Pacheco
    pacheco = resultados["pacheco"]
    if pacheco.get("sucesso"):
        reg = {
            "data_hora": pacheco["data_hora"],
            "produto_id": produto_id,
            "drogaria": pacheco["drogaria"],
            "filial": pacheco["filial"],
            "modalidade": "Online — retirada",
            "condicao_preco": "Preço comum",
            "valor_total": pacheco["preco_online"],
            "quantidade_caixas": 1,
            "custo_por_caixa": pacheco["preco_online"],
            "frete": 0.0,
            "estoque": pacheco["estoque_status"],
            "fonte": "Site — coleta automática",
            "url": pacheco["url"],
            "observacoes": f"Coleta automática. SKU: {pacheco.get('sku', '')}. Ref: R$ {pacheco.get('preco_referencia') or 'N/A'}"
        }
        registros_para_salvar.append(reg)
        detalhes.append({"drogaria": "Drogarias Pacheco", "sucesso": True, "preco": pacheco["preco_online"]})
    else:
        detalhes.append({"drogaria": "Drogarias Pacheco", "sucesso": False, "erro": pacheco.get("erro")})

    # 2. Venancio
    venancio = resultados["venancio"]
    if venancio.get("sucesso"):
        reg_v = {
            "data_hora": venancio["data_hora"],
            "produto_id": produto_id,
            "drogaria": venancio["drogaria"],
            "filial": venancio["filial"],
            "modalidade": "Online — retirada",
            "condicao_preco": "Preço comum",
            "valor_total": venancio["preco_online"],
            "quantidade_caixas": 1,
            "custo_por_caixa": venancio["preco_online"],
            "frete": 0.0,
            "estoque": venancio["estoque_status"],
            "fonte": "Site — coleta automática",
            "url": venancio["url"],
            "observacoes": f"Catálogo público Venancio. SKU: {venancio.get('sku', '')}. Ref: R$ {venancio.get('preco_referencia') or 'N/A'}"
        }
        registros_para_salvar.append(reg_v)
        
        promo = venancio.get("promocao")
        if promo:
            reg_v_promo = {
                "data_hora": venancio["data_hora"],
                "produto_id": produto_id,
                "drogaria": venancio["drogaria"],
                "filial": venancio["filial"],
                "modalidade": "Online — retirada",
                "condicao_preco": "Promoção por quantidade",
                "valor_total": promo["valor_total"],
                "quantidade_caixas": promo["quantidade_leve"],
                "custo_por_caixa": promo["custo_por_caixa"],
                "frete": 0.0,
                "estoque": venancio["estoque_status"],
                "fonte": "Site — coleta automática",
                "url": venancio["url"],
                "observacoes": f"Promoção {promo['descricao']} identificada no catálogo. Total: R$ {promo['valor_total']:.2f}"
            }
            registros_para_salvar.append(reg_v_promo)

        detalhes.append({
            "drogaria": "Drogaria Venancio",
            "sucesso": True,
            "preco": venancio["preco_online"],
            "promocao": promo["descricao"] if promo else None
        })
    else:
        detalhes.append({"drogaria": "Drogaria Venancio", "sucesso": False, "erro": venancio.get("erro")})

    # 3. Drogasmil
    drogasmil = resultados["drogasmil"]
    if drogasmil.get("sucesso"):
        reg_m = {
            "data_hora": drogasmil["data_hora"],
            "produto_id": produto_id,
            "drogaria": drogasmil["drogaria"],
            "filial": drogasmil["filial"],
            "modalidade": "Online — retirada",
            "condicao_preco": "Preço comum",
            "valor_total": drogasmil["preco_online"],
            "quantidade_caixas": 1,
            "custo_por_caixa": drogasmil["preco_online"],
            "frete": 0.0,
            "estoque": drogasmil["estoque_status"],
            "fonte": "Site — coleta automática",
            "url": drogasmil["url"],
            "observacoes": f"JSON-LD Drogasmil. SKU: {drogasmil.get('sku', '')}"
        }
        registros_para_salvar.append(reg_m)
        detalhes.append({"drogaria": "Drogasmil", "sucesso": True, "preco": drogasmil["preco_online"]})
    else:
        detalhes.append({"drogaria": "Drogasmil", "sucesso": False, "erro": drogasmil.get("erro")})

    status_salvamento = salvar_multiplos_registros(registros_para_salvar)

    return JSONResponse({
        "sucesso": True,
        "produto_id": produto_id,
        "detalhes": detalhes,
        "salvamento": status_salvamento
    })

@app.post("/api/registrar")
async def api_registrar(dados: RegistroManual):
    custo_por_caixa = round((dados.valor_total + dados.frete) / max(1, dados.quantidade_caixas), 2)
    from services.scrapers import get_sp_time
    
    novo = {
        "data_hora": get_sp_time(),
        "produto_id": dados.produto_id,
        "drogaria": dados.drogaria,
        "filial": dados.filial,
        "modalidade": dados.modalidade,
        "condicao_preco": dados.condicao_preco,
        "valor_total": round(dados.valor_total, 2),
        "quantidade_caixas": int(dados.quantidade_caixas),
        "custo_por_caixa": custo_por_caixa,
        "frete": round(dados.frete, 2),
        "estoque": dados.estoque,
        "fonte": dados.fonte,
        "url": dados.url,
        "observacoes": dados.observacoes
    }
    
    res = salvar_registro(novo, forcar_duplicado=True)
    return JSONResponse({"sucesso": True, "resultado": res})

@app.get("/api/historico")
async def api_historico(produto_id: Optional[str] = None):
    df = carregar_historico()
    if df.empty:
        return JSONResponse({"total": 0, "registros": []})
    
    if produto_id:
        df = df[df["produto_id"].astype(str) == str(produto_id)]
        
    df["data_hora_sort"] = df["data_hora"]
    df = df.sort_values("data_hora_sort", ascending=False).drop(columns=["data_hora_sort"], errors="ignore")
    return JSONResponse({
        "total": len(df),
        "registros": df.to_dict(orient="records")
    })

@app.get("/api/relatorio/csv")
async def download_relatorio():
    caminho = gerar_relatorio_csv()
    return FileResponse(
        caminho,
        media_type="text/csv",
        filename=os.path.basename(caminho)
    )

@app.get("/api/raia/status")
async def api_raia_status(produto_id: Optional[str] = None):
    status_lista = obter_status_prints_raia(produto_id)
    return JSONResponse(status_lista)

@app.post("/api/raia/upload-print")
async def api_raia_upload_print(
    file: UploadFile = File(...),
    produto_id: Optional[str] = Form(None)
):
    from datetime import datetime
    ext = Path(file.filename or "print.png").suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        ext = ".png"
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid_tag = produto_id or "detect"
    nome_salvo = f"raia_{pid_tag}_{timestamp_str}{ext}"
    caminho_salvo = PASTA_PRINTS / nome_salvo
    
    conteudo = await file.read()
    with open(caminho_salvo, "wb") as f:
        f.write(conteudo)
        
    resultado_ocr = analisar_print_raia(caminho_salvo, produto_id_hint=produto_id)
    resultado_ocr["url_comprovante"] = f"/prints/raia/{nome_salvo}"
    resultado_ocr["nome_arquivo"] = nome_salvo
    
    return JSONResponse(resultado_ocr)

@app.post("/api/raia/confirmar-preco")
async def api_raia_confirmar_preco(dados: ConfirmarPrecoRaia):
    produto = obter_produto_por_id(dados.produto_id)
    nome_prod = produto.get("nome", "") if produto else ""
    url_loja = produto.get("url_raia", "https://www.drogaraia.com.br") if produto else "https://www.drogaraia.com.br"
    agora_sp = get_sp_time()
    
    obs_final = f"Print comprovatório anexado. {dados.observacoes}".strip()
    
    # 1. Registro do preço unitário / comum
    reg_comum = {
        "data_hora": agora_sp,
        "produto_id": dados.produto_id,
        "drogaria": "Droga Raia",
        "filial": "Rua Conde de Bonfim, 536 — Tijuca",
        "laboratorio": dados.laboratorio,
        "modalidade": "Online — retirada",
        "condicao_preco": "Preço comum",
        "valor_total": round(dados.preco_comum, 2),
        "quantidade_caixas": 1,
        "custo_por_caixa": round(dados.preco_comum, 2),
        "frete": 0.0,
        "estoque": dados.estoque,
        "fonte": "Print de tela / OCR",
        "url": dados.url_comprovante or url_loja,
        "observacoes": obs_final
    }
    salvar_registro(reg_comum, forcar_duplicado=True)
    
    # 2. Se houver promoção por quantidade
    if dados.tem_promo and dados.qtd_promo > 1 and dados.preco_promo > 0:
        total_promo = round(dados.preco_promo * dados.qtd_promo, 2)
        reg_promo = {
            "data_hora": agora_sp,
            "produto_id": dados.produto_id,
            "drogaria": "Droga Raia",
            "filial": "Rua Conde de Bonfim, 536 — Tijuca",
            "laboratorio": dados.laboratorio,
            "modalidade": "Online — retirada",
            "condicao_preco": "Promoção por quantidade",
            "valor_total": total_promo,
            "quantidade_caixas": dados.qtd_promo,
            "custo_por_caixa": round(dados.preco_promo, 2),
            "frete": 0.0,
            "estoque": dados.estoque,
            "fonte": "Print de tela / OCR",
            "url": dados.url_comprovante or url_loja,
            "observacoes": f"Promoção Leve {dados.qtd_promo} por R$ {dados.preco_promo:.2f} cada. {obs_final}"
        }
        salvar_registro(reg_promo, forcar_duplicado=True)
        
    return JSONResponse({
        "sucesso": True,
        "mensagem": "Preço da Droga Raia registrado com validade de 3 dias!",
        "produto_id": dados.produto_id
    })

if __name__ == "__main__":
    import uvicorn
    porta = int(os.environ.get("PORT", 8000))
    print(f"Iniciando servidor FarmaPreço na porta {porta}...")
    uvicorn.run("portal:app", host="0.0.0.0", port=porta, reload=False)
