# Central de Instalação

Uma ferramenta gráfica para Windows que centraliza a instalação e extração de programas, automatizando o trabalho repetitivo de descompactar, instalar e criar atalhos.

## 📦 O que ela faz?

- **Instalação de EXE e MSI:** Executa instaladores com argumentos de instalação silenciosa configuráveis.
- **Extração de Compactados:** Descompacta arquivos .zip, .7z, .rar e outros, com suporte a senha.
- **Perfis de Instalação:** Identifica automaticamente instaladores conhecidos e sugere os argumentos corretos (ex: 7-Zip, WinRAR, VLC, etc.).
- **Atalhos para Portáteis:** Cria atalhos na área de trabalho e no menu Iniciar para programas que não precisam de instalação.
- **Interface Personalizável:** Cores de fundo, botões, caixas e letras configuráveis. Suporte a Português e Inglês.
- **Backup do Catálogo:** Permite exportar e importar sua lista de programas para usar em outro computador.

## 🚀 Como usar

1. Baixe o arquivo `.exe` na seção [Releases](https://github.com/SEU-USUARIO/SEU-REPOSITORIO/releases).
2. Execute o `CentralInstalacao.exe`. Não é necessário instalar Python, Pillow ou 7-Zip.
3. Adicione seus instaladores e arquivos compactados.
4. Configure cada item (argumentos, destino, senha, etc.).
5. Marque os programas desejados e clique em "Instalar selecionados".

## ⚠️ Limitações Conhecidas

- As senhas dos compactados são salvas em **texto simples** no arquivo de catálogo local. Não use senhas críticas.
- A ferramenta executa instaladores escolhidos pelo usuário. Ela **não é um antivírus** e não verifica a segurança dos arquivos.
- Um perfil reconhecido não garante que uma versão futura do instalador aceite os mesmos argumentos. A responsabilidade final é do usuário.
- A interface foi projetada para telas com escala até 250%. Em escalas maiores, ela mantém o tamanho máximo para evitar que os controles fiquem inacessíveis.

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+** com interface gráfica em **Tkinter**.
- **7-Zip** (integrado ao executável) para extração de compactados.
- **Pillow** para carregamento de ícones PNG/JPG.
- **PyInstaller** para empacotamento em um único executável para Windows.

## 🤝 Como contribuir

Contribuições são bem-vindas! Se você encontrar um bug ou tiver uma sugestão, abra uma [Issue](https://github.com/SEU-USUARIO/SEU-REPOSITORIO/issues).

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

*Este projeto foi desenvolvido com o auxílio de inteligência artificial.*