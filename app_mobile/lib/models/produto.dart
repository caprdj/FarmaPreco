class Produto {
  final String produtoId;
  final String nome;
  final String principioAtivo;
  final String dosagem;
  final String apresentacao;
  final String fabricante;
  final String categoria;
  final String ean;
  final int quantidadeMensal;
  final String? urlPacheco;
  final String? urlVenancio;
  final String? urlRaia;
  final String? urlDrogasmil;

  Produto({
    required this.produtoId,
    required this.nome,
    required this.principioAtivo,
    required this.dosagem,
    required this.apresentacao,
    required this.fabricante,
    required this.categoria,
    required this.ean,
    required this.quantidadeMensal,
    this.urlPacheco,
    this.urlVenancio,
    this.urlRaia,
    this.urlDrogasmil,
  });

  factory Produto.fromJson(Map<String, dynamic> json) {
    return Produto(
      produtoId: json['produto_id'] ?? '',
      nome: json['nome'] ?? '',
      principioAtivo: json['principio_ativo'] ?? '',
      dosagem: json['dosagem'] ?? '',
      apresentacao: json['apresentacao'] ?? '',
      fabricante: json['fabricante'] ?? '',
      categoria: json['categoria'] ?? 'Referência',
      ean: json['ean'] ?? '',
      quantidadeMensal: int.tryParse(json['quantidade_mensal']?.toString() ?? '1') ?? 1,
      urlPacheco: json['url_pacheco'],
      urlVenancio: json['url_venancio'],
      urlRaia: json['url_raia'],
      urlDrogasmil: json['url_drogasmil'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'produto_id': produtoId,
      'nome': nome,
      'principio_ativo': principioAtivo,
      'dosagem': dosagem,
      'apresentacao': apresentacao,
      'fabricante': fabricante,
      'categoria': categoria,
      'ean': ean,
      'quantidade_mensal': quantidadeMensal,
      'url_pacheco': urlPacheco,
      'url_venancio': urlVenancio,
      'url_raia': urlRaia,
      'url_drogasmil': urlDrogasmil,
    };
  }

  String get tituloCompleto => '$nome $dosagem';
}
