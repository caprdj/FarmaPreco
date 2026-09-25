import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/produto.dart';
import '../services/api_service.dart';

class ComparadorScreen extends StatefulWidget {
  const ComparadorScreen({super.key});

  @override
  State<ComparadorScreen> createState() => _ComparadorScreenState();
}

class _ComparadorScreenState extends State<ComparadorScreen> {
  final currencyFormat = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
  List<Produto> _produtos = [];
  Produto? _produtoSelecionado;
  int _quantidade = 1;
  bool _loading = true;
  bool _comparando = false;
  Map<String, dynamic>? _resultadoComparacao;

  @override
  void initState() {
    super.initState();
    _carregarProdutos();
  }

  Future<void> _carregarProdutos() async {
    setState(() => _loading = true);
    try {
      final prods = await ApiService.listarProdutos();
      setState(() {
        _produtos = prods;
        if (prods.isNotEmpty) {
          _produtoSelecionado = prods.first;
          _quantidade = prods.first.quantidadeMensal;
        }
        _loading = false;
      });
      if (_produtoSelecionado != null) {
        _executarComparacao();
      }
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _executarComparacao() async {
    if (_produtoSelecionado == null) return;
    setState(() => _comparando = true);
    try {
      final res = await ApiService.compararPrecos(
        produtoId: _produtoSelecionado!.produtoId,
        quantidade: _quantidade,
      );
      setState(() {
        _resultadoComparacao = res;
        _comparando = false;
      });
    } catch (e) {
      setState(() => _comparando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final melhor = _resultadoComparacao?['melhor_opcao'];
    final ofertas = (_resultadoComparacao?['ofertas'] as List?) ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Comparador de Farmácias', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF094067),
        foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                // Seletor de Medicamento
                Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Selecione o Medicamento / Produto:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.grey)),
                        const SizedBox(height: 6),
                        DropdownButtonFormField<Produto>(
                          value: _produtoSelecionado,
                          isExpanded: true,
                          decoration: InputDecoration(
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          items: _produtos.map((p) {
                            return DropdownMenuItem(
                              value: p,
                              child: Text(
                                '${p.nome} ${p.dosagem} (${p.fabricante})',
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                                overflow: TextOverflow.ellipsis,
                              ),
                            );
                          }).toList(),
                          onChanged: (p) {
                            if (p != null) {
                              setState(() {
                                _produtoSelecionado = p;
                                _quantidade = p.quantidadeMensal;
                              });
                              _executarComparacao();
                            }
                          },
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            const Text('Quantidade:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline, size: 20),
                              onPressed: _quantidade > 1
                                  ? () {
                                      setState(() => _quantidade--);
                                      _executarComparacao();
                                    }
                                  : null,
                            ),
                            Text('$_quantidade cx', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                            IconButton(
                              icon: const Icon(Icons.add_circle_outline, size: 20),
                              onPressed: () {
                                setState(() => _quantidade++);
                                _executarComparacao();
                              },
                            ),
                            const Spacer(),
                            TextButton.icon(
                              onPressed: () async {
                                if (_produtoSelecionado != null) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(content: Text('Consultando farmácias vizinhas online...')),
                                  );
                                  await ApiService.atualizarPrecosOnline(_produtoSelecionado!.produtoId);
                                  _executarComparacao();
                                }
                              },
                              icon: const Icon(Icons.sync, size: 16),
                              label: const Text('Atualizar Online', style: TextStyle(fontSize: 11)),
                            )
                          ],
                        )
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Card Melhor Opção
                if (melhor != null)
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: const Color(0xFFECFDF5),
                      border: Border.Border.all(color: const Color(0xFF10B981), width: 1.5),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.between,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.military_tech, color: Color(0xFF047857)),
                                SizedBox(width: 4),
                                Text('MELHOR OPÇÃO ENCONTRADA', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: Color(0xFF047857))),
                              ],
                            ),
                            Text(
                              currencyFormat.format(melhor['total_estimado'] ?? 0),
                              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: Color(0xFF047857)),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(
                          melhor['drogaria'] ?? '',
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.black87),
                        ),
                        Text(
                          '${melhor['filial']} • ${melhor['condicao']}',
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
                        ),
                      ],
                    ),
                  ),
                const SizedBox(height: 12),

                // Lista de Ofertas
                Row(
                  mainAxisAlignment: MainAxisAlignment.between,
                  children: [
                    const Text('Ranking de Preços na Tijuca:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    if (_comparando)
                      const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
                  ],
                ),
                const SizedBox(height: 8),

                ...ofertas.map((of) {
                  final isRaia = of['is_raia'] == true;
                  final expirado = of['expirado_3dias'] == true;

                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      leading: CircleAvatar(
                        backgroundColor: isRaia ? Colors.rose.shade50 : Colors.blue.shade50,
                        child: Icon(
                          isRaia ? Icons.camera_alt : Icons.local_pharmacy,
                          color: isRaia ? Colors.rose : Colors.blue,
                          size: 18,
                        ),
                      ),
                      title: Text(
                        of['drogaria'] ?? '',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${of['laboratorio'] ?? 'Referência'} • ${of['condicao']}', style: const TextStyle(fontSize: 11)),
                          if (isRaia && expirado)
                            const Text('Print expirado (> 3 dias)', style: TextStyle(fontSize: 10, color: Colors.red, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      trailing: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(
                            currencyFormat.format(of['total_estimado'] ?? 0),
                            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Colors.black87),
                          ),
                          Text(
                            '${currencyFormat.format(of['custo_por_caixa'] ?? 0)}/cx',
                            style: const TextStyle(fontSize: 10, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              ],
            ),
    );
  }
}
