import 'package:flutter/material.dart';
import '../models/produto.dart';
import '../services/api_service.dart';

class PresencialScreen extends StatefulWidget {
  const PresencialScreen({super.key});

  @override
  State<PresencialScreen> createState() => _PresencialScreenState();
}

class _PresencialScreenState extends State<PresencialScreen> {
  List<Produto> _produtos = [];
  Produto? _produtoSelecionado;
  String _drogaria = 'Drogaria Venancio';
  String _filial = 'Rua Conde de Bonfim, 532 — Tijuca';
  final _valorController = TextEditingController();
  final _labController = TextEditingController();
  final _obsController = TextEditingController();
  bool _salvando = false;

  final Map<String, String> _filiais = {
    'Drogaria Venancio': 'Rua Conde de Bonfim, 532 — Tijuca',
    'Drogarias Pacheco': 'Rua Conde de Bonfim, 580 — Tijuca',
    'Droga Raia': 'Rua Conde de Bonfim, 536 — Tijuca',
    'Drogasmil': 'Praça Saenz Peña, 29 — Tijuca',
  };

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    try {
      final prods = await ApiService.listarProdutos();
      setState(() {
        _produtos = prods;
        if (prods.isNotEmpty) _produtoSelecionado = prods.first;
      });
    } catch (_) {}
  }

  Future<void> _salvar() async {
    final valor = double.tryParse(_valorController.text.replaceAll(',', '.')) ?? 0.0;
    if (valor <= 0 || _produtoSelecionado == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Informe um valor válido')),
      );
      return;
    }

    setState(() => _salvando = true);
    final sucesso = await ApiService.salvarRegistroPresencial({
      'drogaria': _drogaria,
      'filial': _filial,
      'modalidade': 'Loja física — balcão',
      'condicao_preco': 'Preço balcão informado',
      'valor_total': valor,
      'quantidade_caixas': 1,
      'frete': 0.0,
      'estoque': 'Disponível na loja',
      'fonte': 'App Mobile / Balcão',
      'produto_id': _produtoSelecionado!.produtoId,
      'observacoes': '${_labController.text} • ${_obsController.text}'
    });

    setState(() => _salvando = false);
    if (sucesso) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Preço presencial salvo com sucesso!')),
      );
      _valorController.clear();
      _obsController.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Loja Física / Balcão', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF094067),
        foregroundColor: Colors.white,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Registrar Cotação Presencial',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const Text(
            'Passou na farmácia na Tijuca ou ligou pro balcão? Anote o valor aqui.',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 16),

          DropdownButtonFormField<Produto>(
            value: _produtoSelecionado,
            decoration: const InputDecoration(labelText: 'Medicamento', border: OutlineInputBorder()),
            items: _produtos.map((p) => DropdownMenuItem(value: p, child: Text(p.tituloCompleto))).toList(),
            onChanged: (p) => setState(() => _produtoSelecionado = p),
          ),
          const SizedBox(height: 12),

          DropdownButtonFormField<String>(
            value: _drogaria,
            decoration: const InputDecoration(labelText: 'Drogaria', border: OutlineInputBorder()),
            items: _filiais.keys.map((d) => DropdownMenuItem(value: d, child: Text(d))).toList(),
            onChanged: (d) {
              if (d != null) {
                setState(() {
                  _drogaria = d;
                  _filial = _filiais[d] ?? '';
                });
              }
            },
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _valorController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'Preço Balcão (R\$)', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _labController,
            decoration: const InputDecoration(labelText: 'Laboratório / Marca', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _obsController,
            decoration: const InputDecoration(labelText: 'Observações (Ex: desconto com CPF)', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 16),

          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF094067),
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            onPressed: _salvando ? null : _salvar,
            icon: const Icon(Icons.save),
            label: const Text('Salvar Cotação de Balcão', style: TextStyle(fontWeight: FontWeight.bold)),
          )
        ],
      ),
    );
  }
}
