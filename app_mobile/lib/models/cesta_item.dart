class CestaItem {
  final String produtoId;
  final String nome;
  final String dosagem;
  final String fabricante;
  final String apresentacao;
  final int quantidadeMensal;
  final double melhorPreco;
  final String melhorFarmacia;
  final Map<String, double?> precosFarmacias;
  final Map<String, dynamic> detalhesFarmacias;
  final Map<String, dynamic> statusRaia;

  CestaItem({
    required this.produtoId,
    required this.nome,
    required this.dosagem,
    required this.fabricante,
    required this.apresentacao,
    required this.quantidadeMensal,
    required this.melhorPreco,
    required this.melhorFarmacia,
    required this.precosFarmacias,
    required this.detalhesFarmacias,
    required this.statusRaia,
  });

  factory CestaItem.fromJson(Map<String, dynamic> json) {
    Map<String, double?> precos = {};
    if (json['precos_farmacias'] is Map) {
      json['precos_farmacias'].forEach((k, v) {
        if (v != null) {
          precos[k.toString()] = (v as num).toDouble();
        } else {
          precos[k.toString()] = null;
        }
      });
    }

    return CestaItem(
      produtoId: json['produto_id'] ?? '',
      nome: json['nome'] ?? '',
      dosagem: json['dosagem'] ?? '',
      fabricante: json['fabricante'] ?? '',
      apresentacao: json['apresentacao'] ?? '',
      quantidadeMensal: (json['quantidade_mensal'] as num?)?.toInt() ?? 1,
      melhorPreco: (json['melhor_preco'] as num?)?.toDouble() ?? 0.0,
      melhorFarmacia: json['melhor_farmacia'] ?? 'Nenhuma',
      precosFarmacias: precos,
      detalhesFarmacias: json['detalhes_farmacias'] ?? {},
      statusRaia: json['status_raia'] ?? {},
    );
  }
}

class CestaResposta {
  final bool sucesso;
  final int totalMedicamentos;
  final double totalMensalOtimizado;
  final Map<String, double> totaisPorDrogaria;
  final List<CestaItem> itens;
  final int raiaTotalExpirados;
  final bool temRaiaExpirada;

  CestaResposta({
    required this.sucesso,
    required this.totalMedicamentos,
    required this.totalMensalOtimizado,
    required this.totaisPorDrogaria,
    required this.itens,
    required this.raiaTotalExpirados,
    required this.temRaiaExpirada,
  });

  factory CestaResposta.fromJson(Map<String, dynamic> json) {
    Map<String, double> totais = {};
    if (json['totais_por_drogaria'] is Map) {
      json['totais_por_drogaria'].forEach((k, v) {
        if (v != null) {
          totais[k.toString()] = (v as num).toDouble();
        }
      });
    }

    List<CestaItem> listaItens = [];
    if (json['itens'] is List) {
      listaItens = (json['itens'] as List)
          .map((i) => CestaItem.fromJson(i))
          .toList();
    }

    return CestaResposta(
      sucesso: json['sucesso'] ?? false,
      totalMedicamentos: json['total_medicamentos'] ?? 0,
      totalMensalOtimizado: (json['total_mensal_otimizado'] as num?)?.toDouble() ?? 0.0,
      totaisPorDrogaria: totais,
      itens: listaItens,
      raiaTotalExpirados: json['raia_total_expirados'] ?? 0,
      temRaiaExpirada: json['tem_raia_expirada'] ?? false,
    );
  }
}
