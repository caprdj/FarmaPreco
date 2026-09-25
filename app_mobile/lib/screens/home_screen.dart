import 'package:flutter/material.dart';
import 'cesta_screen.dart';
import 'comparador_screen.dart';
import 'raia_prints_screen.dart';
import 'produtos_screen.dart';
import 'presencial_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  // As 5 telas nas ordens solicitadas:
  // 1. Tratamento Mensal Completo
  // 2. Comparador de Farmácias
  // 3. Droga Raia (Prints 3d)
  // 4. Gerenciar Medicamentos
  // 5. Loja Física / Balcão
  final List<Widget> _screens = const [
    CestaScreen(),
    ComparadorScreen(),
    RaiaPrintsScreen(),
    ProdutosScreen(),
    PresencialScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: const Color(0xFF094067),
        unselectedItemColor: Colors.grey.shade600,
        selectedFontSize: 11,
        unselectedFontSize: 10,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.shopping_basket),
            label: 'Lista Completa',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.show_chart),
            label: 'Comparador',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.camera_alt),
            label: 'Droga Raia',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.medication),
            label: 'Medicamentos',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.receipt_long),
            label: 'Balcão',
          ),
        ],
      ),
    );
  }
}
