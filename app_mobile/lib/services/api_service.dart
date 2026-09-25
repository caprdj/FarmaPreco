import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/produto.dart';
import '../models/cesta_item.dart';

class ApiService {
  static const String defaultBaseUrl = 'http://192.168.15.9:8000';
  
  static Future<String> getBaseUrl() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('api_base_url') ?? defaultBaseUrl;
  }

  static Future<void> setBaseUrl(String url) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', url);
  }

  // 1. Cesta Mensal Completa
  static Future<CestaResposta> obterCestaMensal() async {
    final base = await getBaseUrl();
    final res = await http.get(Uri.parse('$base/api/cesta-mensal'));
    if (res.statusCode == 200) {
      final data = json.decode(utf8.decode(res.bodyBytes));
      return CestaResposta.fromJson(data);
    } else {
      throw Exception('Falha ao carregar cesta mensal: ${res.statusCode}');
    }
  }

  // 2. Listar Produtos
  static Future<List<Produto>> listarProdutos() async {
    final base = await getBaseUrl();
    final res = await http.get(Uri.parse('$base/api/produtos'));
    if (res.statusCode == 200) {
      final List data = json.decode(utf8.decode(res.bodyBytes));
      return data.map((json) => Produto.fromJson(json)).toList();
    } else {
      throw Exception('Falha ao carregar produtos');
    }
  }

  // 3. Comparador por Medicamento e Quantidade
  static Future<Map<String, dynamic>> compararPrecos({
    required String produtoId,
    int quantidade = 1,
    bool somenteConfirmado = false,
    String modalidade = 'todas',
  }) async {
    final base = await getBaseUrl();
    final uri = Uri.parse(
      '$base/api/comparar?produto_id=$produtoId&quantidade=$quantidade&somente_confirmado=$somenteConfirmado&modalidade=$modalidade'
    );
    final res = await http.get(uri);
    if (res.statusCode == 200) {
      return json.decode(utf8.decode(res.bodyBytes));
    } else {
      throw Exception('Erro ao comparar preços');
    }
  }

  // 4. Status dos Prints da Droga Raia (Regra de 3 Dias)
  static Future<List<dynamic>> obterStatusRaia() async {
    final base = await getBaseUrl();
    final res = await http.get(Uri.parse('$base/api/raia/status'));
    if (res.statusCode == 200) {
      return json.decode(utf8.decode(res.bodyBytes));
    } else {
      throw Exception('Erro ao obter status da Droga Raia');
    }
  }

  // 5. Upload de Print de Tela da Droga Raia
  static Future<Map<String, dynamic>> uploadPrintRaia(File imageFile, {String? produtoId}) async {
    final base = await getBaseUrl();
    final uri = Uri.parse('$base/api/raia/upload-print');
    
    var request = http.MultipartRequest('POST', uri);
    request.files.add(await http.MultipartFile.fromPath('arquivo', imageFile.path));
    if (produtoId != null && produtoId.isNotEmpty) {
      request.fields['produto_id'] = produtoId;
    }

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);
    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes));
    } else {
      throw Exception('Erro ao enviar print');
    }
  }

  // 6. Confirmar Cotação da Droga Raia (Válida por 3 Dias)
  static Future<bool> confirmarCotacaoRaia(Map<String, dynamic> dados) async {
    final base = await getBaseUrl();
    final res = await http.post(
      Uri.parse('$base/api/raia/confirmar-preco'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(dados),
    );
    return res.statusCode == 200;
  }

  // 7. Salvar Cotação de Loja Física / Balcão
  static Future<bool> salvarRegistroPresencial(Map<String, dynamic> dados) async {
    final base = await getBaseUrl();
    final res = await http.post(
      Uri.parse('$base/api/registrar/manual'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(dados),
    );
    return res.statusCode == 200;
  }

  // 8. Coleta Automática em Tempo Real (Pacheco, Venancio, Drogasmil)
  static Future<Map<String, dynamic>> atualizarPrecosOnline(String produtoId) async {
    final base = await getBaseUrl();
    final res = await http.post(Uri.parse('$base/api/coletar/todas?produto_id=$produtoId'));
    if (res.statusCode == 200) {
      return json.decode(utf8.decode(res.bodyBytes));
    } else {
      throw Exception('Erro na coleta automática');
    }
  }
}
