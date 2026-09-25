with open("templates/index.html", "r", encoding="utf-8") as f:
    text = f.read()

# Marcadores exatos
tag_comp = '<section id="aba-comparador"'
tag_cesta = '<section id="aba-cesta"'
tag_lab = '<section id="aba-laboratorios"'

p_comp = text.find(tag_comp)
p_cesta = text.find(tag_cesta)
p_lab = text.find(tag_lab)

print(f"p_comp: {p_comp}, p_cesta: {p_cesta}, p_lab: {p_lab}")

# Achar os comentários antes de cada section
p_comment_comp = text.rfind("<!-- ===", 0, p_comp)
p_comment_cesta = text.rfind("<!-- ===", 0, p_cesta)
p_comment_lab = text.rfind("<!-- ===", 0, p_lab)

print(f"comment_comp: {p_comment_comp}, comment_cesta: {p_comment_cesta}, comment_lab: {p_comment_lab}")

chunk_comp = text[p_comment_comp:p_comment_cesta]
chunk_cesta = text[p_comment_cesta:p_comment_lab]

# No chunk_cesta, trocar 'class="hidden space-y-5"' por 'class="space-y-5"'
chunk_cesta_updated = chunk_cesta.replace('<section id="aba-cesta" class="hidden space-y-5">', '<section id="aba-cesta" class="space-y-5">')

# No chunk_comp, trocar 'class="space-y-5"' por 'class="hidden space-y-5"'
chunk_comp_updated = chunk_comp.replace('<section id="aba-comparador" class="space-y-5">', '<section id="aba-comparador" class="hidden space-y-5">')

# Trocar o título do comentário
chunk_cesta_updated = chunk_cesta_updated.replace('<!-- ABA: TRATAMENTO MENSAL COMPLETO (CESTA)', '<!-- ABA 1: TRATAMENTO MENSAL COMPLETO (CESTA)')
chunk_comp_updated = chunk_comp_updated.replace('<!-- ABA 1: COMPARADOR DE FARMÁCIAS', '<!-- ABA 2: COMPARADOR DE FARMÁCIAS')

new_text = text[:p_comment_comp] + chunk_cesta_updated + chunk_comp_updated + text[p_comment_lab:]

# No final, garantir que no DOMContentLoaded carregarCestaMensal seja chamada
if "carregarCestaMensal();" not in new_text[new_text.rfind("DOMContentLoaded"):]:
    new_text = new_text.replace(
        "await carregarListaMedicamentos();\n            atualizarComparacao();",
        "await carregarListaMedicamentos();\n            carregarCestaMensal();\n            atualizarComparacao();"
    )

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(new_text)

print("Inversão realizada com sucesso!")
