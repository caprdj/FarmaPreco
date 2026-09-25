import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/cesta_item.dart';
import '../services/api_service.dart';

class CestaScreen extends StatefulWidget {
  const CestaScreen({super.key});

  @override
  State<CestaScreen> createState() => _CestaScreenState();
}

class _CestaScreenState extends State<CestaScreen> {
  final currencyFormat = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
  CestaResposta? _cesta;
  final Set<String> _selecionados = {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await ApiService.obterCestaMensal();
      setState(() {
        _cesta = res;
        _loading = false;
        // Se for primeira carga ou vazio, seleciona todos por padrão
        if (_selecionados.isEmpty && res.itens.isNotEmpty) {
          _selecionados.addAll(res.itens.map((e) => e.produtoId));
        }
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _marcarTodos(bool marcar) {
    setState(() {
      if (marcar && _cesta != null) {
        _selecionados.addAll(_cesta!.itens.map((e) => e.produtoId));
      } else {
        _selecionados.clear();
      }
    });
  }

  void _toggleItem(String id) {
    setState(() {
      if (_selecionados.contains(id)) {
        _selecionados.remove(id);
      } else {
        _selecionados.add(id);
      }
    });
  }

  double get _totalOtimizadoSelecionados {
    if (_cesta == null) return 0.0;
    return _cesta!.itens
        .where((it) => _selecionados.contains(it.produtoId))
        .fold(0.0, (sum, it) => sum + it.melhorPreco);
  }

  Map<String, double> get _totaisPorDrogariaSelecionados {
    final Map<String, double> map = {
      'Drogaria Venancio': 0.0,
      'Drogarias Pacheco': 0.0,
      'Drogasmil': 0.0,
      'Droga Raia': 0.0,
    };
    if (_cesta == null) return map;
    for (final it in _cesta!.itens) {
      if (!_selecionados.contains(it.produtoId)) continue;
      it.precosFarmacias.forEach((farmacia, preco) {
        if (map.containsKey(farmacia)) {
          map[farmacia] = (map[farmacia] ?? 0.0) + preco;
        }
      });
    }
    return map;
  }

  @override
  Widget build(BuildContext context) {
    final totalSelecionados = _selecionados.length;
    final totalItens = _cesta?.itens.length ?? 0;
    final todosMarcados = totalSelecionados == totalItens && totalItens > 0;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lista Completa', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF094067),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(todosMarcados ? Icons.check_box : Icons.check_box_outline_blank),
            tooltip: todosMarcados ? 'Desmarcar Todos' : 'Marcar Todos',
            onPressed: () => _marcarTodos(!todosMarcados),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _carregar,
            tooltip: 'Recalcular',
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.red),
                        const SizedBox(height: 12),
                        Text('Erro ao carregar lista: $_error', textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        ElevatedButton.icon(
                          onPressed: _carregar,
                          icon: const Icon(Icons.refresh),
                          label: const Text('Tentar Novamente'),
                        )
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _carregar,
                  child: ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      // Banner Otimizado para itens selecionados
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF0F766E), Color(0xFF065F46)],
                          ),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.between,
                              children: [
                                const Text(
                                  'MELHOR PREÇO (SELECIONADOS)',
                                  style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: Colors.white24,
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    '$totalSelecionados de $totalItens selecionados',
                                    style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              currencyFormat.format(_totalOtimizadoSelecionados),
                              style: const TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w900),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Soma calculada exclusivamente para os itens marcados para compra',
                              style: const TextStyle(color: Colors.white70, fontSize: 11),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),

                      // Botões rápidos de seleção
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _marcarTodos(true),
                              icon: const Icon(Icons.done_all, size: 16),
                              label: const Text('Marcar Todos', style: TextStyle(fontSize: 11)),
                              style: OutlinedButton.styleFrom(
                                visualDensity: VisualDensity.compact,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () => _marcarTodos(false),
                              icon: const Icon(Icons.clear, size: 16),
                              label: const Text('Desmarcar Todos', style: TextStyle(fontSize: 11)),
                              style: OutlinedButton.styleFrom(
                                visualDensity: VisualDensity.compact,
                                padding: const EdgeInsets.symmetric(vertical: 8),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),

                      // Totais por Drogaria
                      const Text(
                        'Total dos itens selecionados por farmácia:',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black87),
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _totaisPorDrogariaSelecionados.entries.map((e) {
                          return Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: Colors.grey.shade300),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(e.key, style: const TextStyle(fontSize: 11, color: Colors.grey, fontWeight: FontWeight.w600)),
                                Text(
                                  currencyFormat.format(e.value),
                                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black87),
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 16),

                      // Alerta Droga Raia se houver expirados
                      if (_cesta?.temRaiaExpirada == true)
                        Container(
                          padding: const EdgeInsets.all(12),
                          margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(
                            color: Colors.amber.shade50,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.amber.shade300),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.warning_amber_rounded, color: Colors.amber.shade800),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'Existem ${_cesta?.raiaTotalExpirados} cotações da Droga Raia vencidas (> 3 dias).',
                                  style: TextStyle(fontSize: 12, color: Colors.amber.shade900, fontWeight: FontWeight.w600),
                                ),
                              ),
                            ],
                          ),
                        ),

                      // Lista de Itens com Checkboxes de Seleção
                      Row(
                        mainAxisAlignment: MainAxisAlignment.between,
                        children: [
                          const Text(
                            'Marque o que vai comprar no mês:',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          Text(
                            '$totalSelecionados selecionados',
                            style: const TextStyle(fontSize: 12, color: Colors.teal, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),

                      ...(_cesta?.itens ?? []).map((item) {
                        final isSelected = _selecionados.contains(item.produtoId);

                        return Opacity(
                          opacity: isSelected ? 1.0 : 0.45,
                          child: Card(
                            margin: const EdgeInsets.only(bottom: 8),
                            elevation: isSelected ? 1 : 0,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                              side: BorderSide(
                                color: isSelected ? Colors.teal.shade200 : Colors.grey.shade200,
                              ),
                            ),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => _toggleItem(item.produtoId),
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Checkbox(
                                          value: isSelected,
                                          activeColor: Colors.teal,
                                          onChanged: (val) => _toggleItem(item.produtoId),
                                          visualDensity: VisualDensity.compact,
                                        ),
                                        Expanded(
                                          child: Text(
                                            '${item.nome} ${item.dosagem}',
                                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: Colors.cyan.shade50,
                                            borderRadius: BorderRadius.circular(6),
                                          ),
                                          child: Text(
                                            '${item.quantidadeMensal} un/mês',
                                            style: TextStyle(fontSize: 11, color: Colors.cyan.shade900, fontWeight: FontWeight.bold),
                                          ),
                                        ),
                                      ],
                                    ),
                                    Padding(
                                      padding: const EdgeInsets.only(left: 40),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            '${item.fabricante} • ${item.apresentacao}',
                                            style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                          ),
                                          const Divider(height: 16),
                                          Row(
                                            mainAxisAlignment: MainAxisAlignment.between,
                                            children: [
                                              Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  const Text('Melhor Opção:', style: TextStyle(fontSize: 10, color: Colors.grey)),
                                                  Text(
                                                    item.melhorFarmacia,
                                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.black87),
                                                  ),
                                                ],
                                              ),
                                              Text(
                                                currencyFormat.format(item.melhorPreco),
                                                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Colors.teal),
                                              ),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
    );
  }
}
