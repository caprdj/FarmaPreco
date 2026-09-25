import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../models/produto.dart';

class RaiaPrintsScreen extends StatefulWidget {
  const RaiaPrintsScreen({super.key});

  @override
  State<RaiaPrintsScreen> createState() => _RaiaPrintsScreenState();
}

class _RaiaPrintsScreenState extends State<RaiaPrintsScreen> {
  final currencyFormat = NumberFormat.currency(locale: 'pt_BR', symbol: 'R\$');
  final ImagePicker _picker = ImagePicker();
  List<dynamic> _statusLista = [];
  List<Produto> _produtos = [];
  bool _loading = true;
  bool _enviando = false;

  @override
  void initState() {
    super.initState();
    _carregarDados();
  }

  Future<void> _carregarDados() async {
    setState(() => _loading = true);
    try {
      final status = await ApiService.obterStatusRaia();
      final prods = await ApiService.listarProdutos();
      setState(() {
        _statusLista = status;
        _produtos = prods;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _capturarPrint(ImageSource source, {String? produtoId}) async {
    try {
      final XFile? foto = await _picker.pickImage(source: source);
      if (foto == null) return;

      setState(() => _enviando = true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enviando print da Droga Raia e analisando OCR...')),
      );

      final File arquivo = File(foto.path);
      final resultado = await ApiService.uploadPrintRaia(arquivo, produtoId: produtoId);

      setState(() => _enviando = false);
      if (resultado['sucesso'] == true) {
        _exibirDialogoConfirmacao(resultado);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(resultado['mensagem'] ?? 'Erro no processamento')),
        );
      }
    } catch (e) {
      setState(() => _enviando = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Falha ao enviar: $e')),
      );
    }
  }

  void _exibirDialogoConfirmacao(Map<String, dynamic> dadosOcr) {
    final ocr = dadosOcr['ocr'] ?? {};
    final precoController = TextEditingController(text: (ocr['preco_unitario'] ?? '').toString());
    final labController = TextEditingController(text: (ocr['laboratorio'] ?? 'Referência').toString());
    String prodId = dadosOcr['produto_id_sugerido'] ?? (_produtos.isNotEmpty ? _produtos.first.produtoId : 'MED001');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            top: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Icon(Icons.camera_enhance, color: Colors.rose),
                  SizedBox(width: 8),
                  Text('Confirmar Cotação Droga Raia', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                ],
              ),
              const SizedBox(height: 6),
              const Text(
                'Validade da cotação: 3 dias a partir de agora',
                style: TextStyle(fontSize: 11, color: Colors.grey),
              ),
              const Divider(height: 20),
              DropdownButtonFormField<String>(
                value: prodId,
                decoration: const InputDecoration(labelText: 'Medicamento / Produto', border: OutlineInputBorder()),
                items: _produtos.map((p) {
                  return DropdownMenuItem(value: p.produtoId, child: Text(p.tituloCompleto));
                }).toList(),
                onChanged: (v) {
                  if (v != null) prodId = v;
                },
              ),
              const SizedBox(height: 12),
              TextField(
                controller: precoController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Preço Comum (R\$)', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: labController,
                decoration: const InputDecoration(labelText: 'Laboratório / Marca', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.rose.shade700,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  icon: const Icon(Icons.check_circle),
                  label: const Text('Salvar com Validade de 3 Dias', style: TextStyle(fontWeight: FontWeight.bold)),
                  onPressed: () async {
                    final preco = double.tryParse(precoController.text.replaceAll(',', '.')) ?? 0.0;
                    final sucesso = await ApiService.confirmarCotacaoRaia({
                      'produto_id': prodId,
                      'preco_comum': preco,
                      'laboratorio': labController.text,
                      'estoque': 'Disponível na loja',
                      'tem_promo': false,
                      'qtd_promo': 1,
                      'preco_promo': 0.0,
                      'url_comprovante': dadosOcr['url_print'] ?? '',
                      'observacoes': 'Upload mobile app (vigência 3 dias)'
                    });

                    Navigator.pop(ctx);
                    if (sucesso) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Preço registrado por 3 dias com sucesso!')),
                      );
                      _carregarDados();
                    }
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Droga Raia (Prints 3d)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: const Color(0xFF094067),
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _carregarDados),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                // Banner Regra 3 Dias
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.rose.shade50,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.Border.all(color: Colors.rose.shade200),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.camera_alt, color: Colors.rose.shade700),
                          const SizedBox(width: 8),
                          const Text('Política de Prints (3 Dias)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.black87)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Tire um print no app da Droga Raia ou tire uma foto com a câmera. Os preços ficam válidos por exatamente 3 dias para compor sua cesta mensal.',
                        style: TextStyle(fontSize: 11, color: Colors.black87),
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.rose.shade700,
                                foregroundColor: Colors.white,
                              ),
                              onPressed: _enviando ? null : () => _capturarPrint(ImageSource.camera),
                              icon: const Icon(Icons.photo_camera, size: 16),
                              label: const Text('Tirar Foto', style: TextStyle(fontSize: 12)),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: _enviando ? null : () => _capturarPrint(ImageSource.gallery),
                              icon: const Icon(Icons.photo_library, size: 16),
                              label: const Text('Da Galeria', style: TextStyle(fontSize: 12)),
                            ),
                          ),
                        ],
                      )
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                const Text('Status de Validade por Medicamento:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                const SizedBox(height: 8),

                ..._statusLista.map((item) {
                  final status = item['status_tipo'];
                  Color badgeColor = Colors.grey;
                  String badgeTexto = 'Sem print';
                  if (status == 'valido') {
                    badgeColor = Colors.green;
                    badgeTexto = 'Válido (${item['dias_restantes']}d restantes)';
                  } else if (status == 'vencendo') {
                    badgeColor = Colors.orange;
                    badgeTexto = 'Vence hoje (${item['horas_restantes']}h)';
                  } else if (status == 'expirado') {
                    badgeColor = Colors.red;
                    badgeTexto = 'Expirado (> 3 dias)';
                  }

                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                      title: Text(item['nome'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            item['tem_cotacao'] == true
                                ? '${currencyFormat.format(item['preco_por_caixa'])} (${item['laboratorio']})'
                                : 'Sem cotação recente',
                            style: const TextStyle(fontSize: 12),
                          ),
                          const SizedBox(height: 2),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: badgeColor.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              badgeTexto,
                              style: TextStyle(color: badgeColor, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      trailing: IconButton(
                        icon: const Icon(Icons.add_a_photo, color: Colors.rose, size: 20),
                        tooltip: 'Atualizar print',
                        onPressed: () => _capturarPrint(ImageSource.gallery, produtoId: item['produto_id']),
                      ),
                    ),
                  );
                }),
              ],
            ),
    );
  }
}
