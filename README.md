<img width="450" height="400" alt="Captura de tela 2026-10-23 150938" src="https://github.com/user-attachments/assets/07936ee9-aede-4246-8512-828cd532d30d" />
<img width="450" height="400" alt="Captura de tela 2026-10-23 150442" src="https://github.com/user-attachments/assets/5cf801b1-2ace-4223-86b1-58301068530b" />

# English

# Installation Center

A graphical tool for Windows that centralizes the installation and extraction of programs, automating the repetitive work of unzipping, installing, and creating shortcuts.

## 📦 What does it do?

- **EXE and MSI Installation:** Runs installers with configurable silent installation arguments.
- **Archive Extraction:** Unzips .zip, .7z, .rar, and other files, with password support.
- **Installation Profiles:** Automatically identifies known installers and suggests the correct arguments (e.g., 7-Zip, WinRAR, VLC, etc.).
- **Portable Shortcuts:** Creates desktop and Start menu shortcuts for programs that don't require installation.
- **Customizable Interface:** Configurable background, buttons, boxes, and text colors. Portuguese and English support.
- **Catalog Backup:** Allows you to export and import your program list to use on another computer.

## 🚀 How to use

1. Download the `.exe` file from the [Releases](https://github.com/Miguel156/Automate-Installation-Center/releases) section.
2. Run `CentralInstalacao.exe`. No need to install Python, Pillow, or 7-Zip.
3. Add your installers and compressed files.
4. Configure each item (arguments, destination, password, etc.).
5. Check the desired programs and click "Install Selected".

## ⚠️ Known Limitations

- Archive passwords are stored in **plain text** in the local catalog file. Do not use critical passwords.
- The tool runs user-selected installers. It **is not an antivirus** and does not verify file security.
- A recognized profile does not guarantee that a future version of the installer will accept the same arguments. Final responsibility lies with the user.
- The interface is designed for screens with scaling up to 250%. At higher scales, it maintains maximum size to prevent controls from becoming inaccessible.

## 🛠️ Technologies Used

- **Python 3.10+** with a **Tkinter** graphical interface.
- **7-Zip** (bundled into the executable) for archive extraction.
- **Pillow** for loading PNG/JPG icons.
- **PyInstaller** for packaging into a single Windows executable.

## 🤝 How to contribute

Contributions are welcome! If you find a bug or have a suggestion, open an [Issue](https://github.com/Miguel156/Automate-Installation-Center/issues).

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/Miguel156/Automate-Installation-Center/blob/main/LICENSE) file for details.

---

*This project was developed with the assistance of artificial intelligence.*


# Português

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

1. Baixe o arquivo `.exe` na seção [Releases](https://github.com/Miguel156/Automate-Installation-Center/releases).
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

Contribuições são bem-vindas! Se você encontrar um bug ou tiver uma sugestão, abra uma [Issue](https://github.com/Miguel156/Automate-Installation-Center/issues).

## 📄 Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo [LICENSE](https://github.com/Miguel156/Automate-Installation-Center/blob/main/LICENSE) para mais detalhes.

---

*Este projeto foi desenvolvido com o auxílio de inteligência artificial.*
