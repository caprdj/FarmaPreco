# FarmaPreço Mobile (App para Smartphone)

Aplicativo móvel do **FarmaPreço** para comparação de preços de medicamentos e produtos de higiene/beleza nas farmácias da Tijuca (Drogaria Venancio, Drogarias Pacheco, Drogasmil e Droga Raia).

---

## 🚀 Opção 1: Uso Imediato pelo Smartphone (PWA nativo no Navegador)

Você pode usar o aplicativo no seu smartphone imediatamente sem precisar compilar nada:

1. Conecte o seu celular (Android ou iPhone) na **mesma rede Wi-Fi** do computador.
2. Abra o navegador do celular e acesse o endereço:
   ```
   http://192.168.15.9:8000
   ```
   *(Ou aponte a câmera para o QR Code disponível no botão "App Celular" do portal web).*
3. **No iPhone (Safari):** Toque no ícone de Compartilhar (quadrado com seta) e escolha **"Adicionar à Tela de Início"**.
4. **No Android (Chrome):** Toque no menu (3 pontinhos) e escolha **"Instalar aplicativo"** ou **"Adicionar à tela inicial"**.
5. O ícone do **FarmaPreço** aparecerá na tela do celular como um aplicativo completo com câmera direta para prints da Droga Raia e barra inferior com as 5 abas!

---

## 🛠️ Opção 2: Compilar e Rodar o App Flutter Nativo (Android / iOS)

O código deste diretório (`app_mobile/`) é um projeto Flutter completo estruturado com:
- `lib/models/`: Modelos de dados para medicamentos, produtos e cálculo da cesta.
- `lib/services/api_service.dart`: Comunicação HTTP com o servidor local (`portal.py`).
- `lib/screens/`:
  1. `cesta_screen.dart`: Tratamento Mensal Completo (14 itens).
  2. `comparador_screen.dart`: Comparador de Farmácias com ranking na Tijuca.
  3. `raia_prints_screen.dart`: Droga Raia com fotos da câmera e galeria (validade de 3 dias).
  4. `produtos_screen.dart`: Gerenciamento e listagem dos medicamentos monitorados.
  5. `presencial_screen.dart`: Registro de cotações em loja física ou balcão.

### Requisitos:
- Flutter SDK instalado (`flutter --version`)
- Android Studio ou Xcode

### Como executar:
```bash
cd app_mobile
flutter pub get
flutter run
```

### Como gerar o instalador APK para Android:
```bash
flutter build apk --release
```
O arquivo APK pronto para instalar ficará em:
`build/app/outputs/flutter-apk/app-release.apk`
