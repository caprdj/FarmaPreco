import 'package:flutter/material.dart';
import '../models/produto.dart';
import '../services/api_service.dart';

class ProdutosScreen extends StatefulWidget {
  const ProdutosScreen({super.key});

  @override
  State<ProdutosScreen> createState() => _ProdutosScreenState();
}

class _ProdutosScreenState extends State<ProdutosScreen> {
  List<Produto> _produtos = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _carregar();
  }

  Future<void> _carregar() async {
    setState(() => _loading = true);
    try {
      final prods = await ApiService.listarProdutos();
      setState(() {
        _produtos = prods;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Gerenciar Medicamentos', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF094067),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _carregar),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.between,
                  children: [
                    const Text('Medicamentos Monitorados:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    Text('${_produtos.length} cadastrados', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
                const SizedBox(height: 8),
                ..._produtos.map((p) {
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      leading: CircleAvatar(
                        backgroundColor: Colors.cyan.shade50,
                        child: Icon(Icons.medication, color: Colors.cyan.shade800, size: 20),
                      ),
                      title: Text(p.tituloCompleto, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Text(
                        '${p.fabricante} • ${p.categoria} • ${p.quantidadeMensal} un/mês',
                        style: const TextStyle(fontSize: 11),
                      ),
                      trailing: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Colors.purple.shade50,
                          borderRadius: BorderRadius.circular(4),
                          border: Border.Border.all(color: Colors.purple.shade200),
                        ),
                        child: Text(
                          p.categoria,
                          style: TextStyle(fontSize: 10, color: Colors.purple.shade700, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
    );
  }
}
