# FarmaPreço Tijuca 💊🛒

Sistema inteligente para comparação e monitoramento de preços de medicamentos, dermocosméticos e produtos de higiene em farmácias vizinhas (Tijuca - Rio de Janeiro), com portal web responsivo (PWA) e aplicativo móvel (Flutter).

---

## 🌟 Funcionalidades Principais

1. **Lista Completa com Seleção Dinâmica:**
   - Visualização de todos os medicamentos de uso contínuo e produtos do mês.
   - Botões de seleção/checkbox para marcar exclusivamente os itens que você vai comprar no mês.
   - Recálculo dinâmico e em tempo real dos cards de resumo e do rodapé da tabela, somando apenas os produtos selecionados.
   - Persistência das seleções no navegador via `localStorage`.

2. **Comparador de Farmácias:**
   - Comparação direta entre **Drogaria Venancio**, **Drogarias Pacheco**, **Drogasmil** e **Droga Raia**.
   - Identificação do melhor preço unitário e economia em promoções por quantidade ("Leve 4 por X").
   - Detecção de estoque nas filiais da Tijuca (Rua Conde de Bonfim e Praça Saenz Peña).

3. **Comparador por Laboratórios e Genéricos:**
   - Comparação de preços entre laboratórios concorrentes (EMS, Medley, Eurofarma, Sanofi, Biolab, Aché, etc.).
   - Cálculo automático da porcentagem e valor em reais economizados ao trocar referências por genéricos equivalentes.

4. **Droga Raia (Upload de Prints & OCR com Validade de 3 Dias):**
   - Upload de capturas de tela dos preços no app/site da Droga Raia.
   - Suporte a arrastar e soltar (drag & drop) e colar direto com **Ctrl + V**.
   - OCR nativo para extração automática de medicamento, preços e promoções.
   - **Política de 3 Dias:** cotações expiram 72h após o upload do print, com alertas visuais indicando a necessidade de renovação.

5. **Gerenciar Medicamentos & Produtos:**
   - Cadastro tanto de **medicamentos** quanto de **produtos em geral** (cosméticos, dermocosméticos, higiene, etc.).
   - Edição de dosagens, quantidades prescritas e apresentações de produtos cadastrados.
   - Listagem e busca sempre em ordem alfabética rigorosa.

6. **Loja Física / Balcão:**
   - Registro manual de preços consultados presencialmente no balcão, telefone ou WhatsApp das filiais da Tijuca.

7. **Aplicativo para Smartphone (Flutter & PWA):**
   - Acesso via navegador mobile (PWA) no Android e iPhone.
   - App nativo Flutter na pasta `app_mobile/`, com todas as funcionalidades replicadas.

---

## 📁 Estrutura do Projeto

```
Farmacias/
├── portal.py                 # Backend FastAPI com todas as rotas e regras de negócio
├── templates/
│   └── index.html            # Portal Web moderno com Tailwind CSS e FontAwesome
├── static/                   # Manifest PWA, ícones e Service Worker
├── services/
│   ├── scrapers.py           # Scrapers e coletores de dados online
│   ├── storage.py            # Persistência CSV, histórico e regras de cálculo
│   └── ocr_raia.py           # OCR nativo e processamento de comprovantes
├── dados/
│   ├── produtos.csv          # Base de medicamentos e produtos monitorados
│   ├── historico_precos.csv  # Histórico detalhado de cotações
│   └── drogarias.csv         # Filiais e configurações
├── app_mobile/               # Aplicativo móvel completo em Flutter
│   ├── lib/                  # Código Dart (screens, models, services)
│   └── pubspec.yaml          # Dependências do app
├── prints/                   # Comprovantes e capturas da Droga Raia
└── README.md
```

---

## 🚀 Como Executar

### 1. Iniciar o Portal Web

Certifique-se de ter o Python 3.10+ instalado:

```bash
# Ativar o ambiente virtual (se aplicável)
.venv\Scripts\activate

# Instalar dependências
pip install fastapi uvicorn pandas pydantic jinja2 python-multipart pillow

# Iniciar o servidor
python portal.py
```

Acesse:
- **Computador:** `http://localhost:8000`
- **Smartphone (na mesma rede Wi-Fi):** `http://<IP_LOCAL>:8000`

### 2. Executar o Aplicativo Mobile (Flutter)

```bash
cd app_mobile
flutter pub get
flutter run
```

---

## 📄 Licença

Uso pessoal e acadêmico para monitoramento de despesas farmacêuticas.
