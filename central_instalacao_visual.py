import os, sys, json, queue, threading, subprocess, shutil, datetime, base64, uuid
from pathlib import Path
from runtime_recursos import find_7zip, run_process, spawn_process, open_licenses, self_test
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
try:
    from PIL import Image, ImageTk, ImageOps
except ImportError:
    Image = ImageTk = ImageOps = None

VERSION='0.9.0 — cores personalizáveis'
OLD_ROOT=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CentralInstalacao'
ROOT=OLD_ROOT.with_name('CentralInstalacaoVisual')
ROOT.mkdir(parents=True,exist_ok=True)
LOGS=ROOT/'logs';LOGS.mkdir(exist_ok=True)
ICONS=ROOT/'icones';ICONS.mkdir(exist_ok=True)
CONFIG=ROOT/'catalogo.json';SETTINGS=ROOT/'preferencias.json'
APARENCIA_FILE=ROOT/'aparencia.json'
LANG_FILE=ROOT/'idioma.json'
ACTIONS=['Instalar','Extrair','Extrair e instalar']
ARCHIVES=('.zip','.7z','.rar','.tar','.gz','.bz2','.xz')

# Paleta padrão (Chumbo) — será sobrescrita pelas escolhas do usuário
BG="#202125";PANEL='#202125';CARD='#33363c';HOVER='#41454c';TEXT='#f2f3f5';MUTED="#d9dee7";BLUE='#788da5';BORDER='#565c66'
def write_json(p,data):
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)

def load_custom_palette():
    """Carrega as cores personalizadas do usuário, se existirem."""
    try:
        data=json.loads(APARENCIA_FILE.read_text(encoding='utf-8'))
        if isinstance(data,dict) and 'palette' in data:
            p=data['palette']
            if all(k in p for k in ('bg','card','button','text')):
                return p
    except (OSError,ValueError,AttributeError,TypeError):
        pass
    return None

def save_custom_palette(palette):
    try:
        write_json(APARENCIA_FILE,{'palette':palette})
        return None
    except OSError as exc:
        return exc

def apply_palette(palette):
    """Aplica a paleta globalmente (variáveis do módulo)."""
    global BG,PANEL,CARD,HOVER,TEXT,MUTED,BLUE,BORDER
    BG=palette['bg']
    CARD=palette['card']
    HOVER=palette.get('hover',palette['card'])
    PANEL=palette.get('panel',palette['card'])
    TEXT=palette['text']
    MUTED=palette.get('muted',palette['text'])
    BLUE=palette.get('accent',palette['button'])
    BORDER=palette.get('border',palette['button'])

def configured_root():
    try:
        s=json.loads(SETTINGS.read_text(encoding='utf-8'))
        if s.get('mode')=='custom' and s.get('path'):return Path(s['path'])
    except (OSError,ValueError,TypeError,AttributeError):pass
    return Path.home()/'ProgramasExtraidos'

def internal(folder,relative):
    root=Path(folder).resolve();p=(root/relative).resolve()
    if not relative or Path(relative).is_absolute() or not p.is_relative_to(root):raise ValueError('Informe um caminho relativo dentro da pasta de extração.')
    return p

def find7z():
    return find_7zip()

def default_description(item):
    ext=Path(item.get('source','')).suffix.lower()
    return item.get('description') or {'Instalar':'Instalador local '+ext,'Extrair':'Pacote portátil / extração','Extrair e instalar':'Descompactar e executar instalador'}.get(item.get('action'),'Pacote local')

def create_shortcuts(item):
    target=internal(item['dest'],item.get('portable',''))
    if not target.is_file() or target.suffix.lower()!='.exe':raise ValueError('Executável portable não encontrado. Confira o caminho relativo.')
    name=''.join('_' if c in '<>:"/\\|?*' or ord(c)<32 else c for c in item['name']).strip().rstrip('.')[:120]
    if not name:raise ValueError('Nome inválido para atalho.')
    data=dict(target=str(target),name=name,desktop=item.get('desktop',False),startmenu=item.get('startmenu',False))
    env=os.environ.copy();env['CENTRAL_SHORTCUT']=json.dumps(data,ensure_ascii=True)
    script=r"""$ErrorActionPreference='Stop'
$d=$env:CENTRAL_SHORTCUT | ConvertFrom-Json
$s=New-Object -ComObject WScript.Shell
$folders=@()
if ($d.desktop) {$folders+=$s.SpecialFolders.Item('Desktop')}
if ($d.startmenu) {$folders+=$s.SpecialFolders.Item('Programs')}
foreach ($folder in $folders) {
 $path=Join-Path $folder ($d.name+'.lnk')
 if (Test-Path -LiteralPath $path) {throw ('Atalho já existe: '+$path)}
}
foreach ($folder in $folders) {
 $link=$s.CreateShortcut((Join-Path $folder ($d.name+'.lnk')))
 $link.TargetPath=$d.target
 $link.WorkingDirectory=[System.IO.Path]::GetDirectoryName($d.target)
 $link.IconLocation=$d.target+',0'
 $link.Save()
}
"""
    encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    ps=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    r=run_process([str(ps),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if r.returncode:raise RuntimeError('Falha criando atalhos. Verifique se já existem: atalhos não são sobrescritos.')

# ================== SISTEMA DE TRADUÇÃO ==================
TRANSLATIONS = {
    'pt': {
        'app_title': 'Central de instalação',
        'app_icon': '⚙',
        'header_title': 'Automação de instalação',
        'header_subtitle': 'Selecione os programas e clique em Instalar selecionados.',
        'btn_add': '＋ Adicionar',
        'btn_configure': 'Configurar item',
        'btn_open_item_folder': 'Pasta do item',
        'btn_open_root_folder': 'Pasta raiz',
        'btn_more_options': 'Mais opções ▾',
        'btn_select_all': 'Selecionar todos',
        'btn_install': '↓   Instalar selecionados',
        'btn_stop': 'Parar após item atual',
        'progress_count': '{done}/{total} concluídos',
        'btn_open_logs': 'Abrir logs',
        'log_title': 'Log de instalação',
        'status_ready': 'Pronto. Nenhum pacote é executado ao adicioná-lo.',
        'appearance_label': 'Aparência',
        'language_label': 'Idioma',
        'theme_blue': 'Azul',
        'theme_gray': 'Chumbo',
        'menu_backup': 'Fazer backup do catálogo...',
        'menu_import': 'Importar catálogo de backup...',
        'menu_change_root': 'Alterar pasta raiz',
        'menu_create_shortcuts': 'Criar atalhos do item',
        'menu_open_catalog': 'Abrir pasta do catálogo visual',
        'menu_remove': 'Remover item do catálogo',
        'menu_about': 'Sobre / licenças de terceiros',
        'catalog_empty': 'Seu catálogo está vazio.\nClique em ＋ Adicionar para selecionar instaladores e compactados.',
        'card_exe': 'EXE',
        'card_msi': 'MSI',
        'card_zip': 'ZIP',
        'status_ready_short': 'Pronto',
        'status_processing': 'Processando…',
        'status_error': 'Erro',
        'selection_info': '{sel} de {total} programa(s) marcado(s)',
        'queue_finished': 'Fila encerrada. Confira resultados e logs.',
        'msg_select_item': 'Clique no nome/cartão de um programa ou use sua engrenagem.',
        'msg_select_item_title': 'Selecionar item',
        'msg_no_selection': 'Marque ao menos um programa.',
        'msg_no_selection_title': 'Seleção',
        'msg_confirm_run': 'Instaladores modificam o sistema. Execute somente arquivos confiáveis. Continuar?',
        'msg_confirm_run_title': 'Confirmar execução',
        'msg_processing': 'Use Parar após item atual e aguarde o processo terminar.',
        'msg_processing_title': 'Processando',
        'msg_backup_ok': 'Catálogo copiado com sucesso para:\n{path}',
        'msg_backup_title': 'Backup',
        'msg_backup_error': 'Não foi possível salvar o backup:\n{exc}',
        'msg_backup_error_title': 'Erro no backup',
        'msg_import_invalid': 'Arquivo inválido ou corrompido:\n{exc}',
        'msg_import_error_title': 'Erro na importação',
        'msg_import_question': 'Deseja MESCLAR os itens do backup com o seu catálogo atual?\n\nSim = Mesclar (adiciona os novos, mantém os existentes)\nNão = Substituir (apaga o atual e usa apenas os do backup)\nCancelar = Cancelar a importação\n\nAtenção: os caminhos dos arquivos (instaladores, ZIPs) não são transferidos e precisarão ser revisados.',
        'msg_import_title': 'Importar Catálogo',
        'msg_import_merged': 'Importação concluída. {count} novo(s) item(ns) foram adicionados ao catálogo.',
        'msg_import_replaced': 'Catálogo substituído com sucesso.',
        'msg_import_confirm_title': 'Confirmar Substituição',
        'msg_import_confirm': 'Tem certeza? O catálogo atual será substituído permanentemente pelo do backup.',
        'msg_catalog_copy_question': 'Esta prévia usa um catálogo separado. Copiar os programas e preferências da versão anterior?\n\nO catálogo anterior não será alterado. Arquivos instalados/extraídos continuam nos mesmos locais.',
        'msg_catalog_copy_title': 'Copiar catálogo existente?',
        'msg_catalog_invalid': 'Não foi possível carregar. Uma cópia foi preservada.\n{exc}',
        'msg_catalog_error_title': 'Catálogo',
        'msg_shortcuts_config': 'Configure o executável portable e os locais dos atalhos primeiro.',
        'msg_shortcuts_title': 'Atalhos',
        'msg_shortcuts_confirm': 'Criar os atalhos configurados para {name}?',
        'msg_shortcuts_ok': 'Atalhos criados. Para fixar: Iniciar > Todos > programa > botão direito > Fixar em Iniciar.',
        'msg_root_question': 'Usar a pasta padrão deste usuário?\n\n{path}\n\nSim = padrão\nNão = escolher outra\nCancelar = manter: {current}',
        'msg_root_title': 'Pasta de extração',
        'msg_update_dest_question': '{count} item(ns) usam a raiz anterior. Atualizar os destinos cadastrados?\n\nIsso NÃO move arquivos nem corrige atalhos. Escolha Não para manter os programas onde estão.',
        'msg_update_dest_title': 'Atualizar destinos?',
        'msg_remove_confirm': 'Remover {name} do catálogo?\nNenhum instalador ou pasta extraída será apagado.',
        'msg_remove_title': 'Remover',
        'msg_dest_not_exists': 'A pasta de extração ainda não existe.',
        'msg_dest_title': 'Destino',
        'msg_format_unsupported': 'Formato não suportado: {name}',
        'msg_format_title': 'Formato',
        'msg_edit_title': 'Configurar programa',
        'msg_edit_window': 'Configurar — {name}',
        'field_name': 'Nome',
        'field_description': 'Descrição (opcional)',
        'field_source': 'Arquivo de origem',
        'field_action': 'Ação',
        'field_dest': 'Destino da extração',
        'field_inner': 'Instalador interno relativo',
        'field_args': 'Argumentos EXE/MSI',
        'field_portable': 'Executável portable relativo',
        'field_icon': 'Ícone PNG/JPG (opcional)',
        'field_password': 'Senha do compactado',
        'field_show_password': 'Mostrar',
        'field_silent': 'MSI silencioso (EXE usa os argumentos acima)',
        'field_desktop': 'Criar atalho na área de trabalho',
        'field_startmenu': 'Adicionar à lista do Iniciar (não fixa nos favoritos)',
        'field_hint': 'Caminho interno relativo: PastaDoPrograma\\programa.exe\nDestino é de extração, não o local de instalação do EXE/MSI.\nSenha salva em texto simples. Ícone e descrição são opcionais.\nArquivos extraídos existentes são ignorados. Use pasta vazia após falha parcial.',
        'btn_choose': 'Escolher',
        'btn_choose_exe': 'Escolher EXE',
        'btn_clear': 'Limpar',
        'btn_cancel': 'Cancelar',
        'btn_save': 'Salvar configuração',
        'msg_edit_invalid': 'Confira o nome e o arquivo de origem.',
        'msg_edit_format': 'Formato de origem não suportado.',
        'msg_edit_action': 'Ação inválida.',
        'msg_edit_dest_required': 'Informe a pasta de extração.',
        'msg_edit_shortcut_install': 'Atalhos portáteis exigem ação de extração.',
        'msg_edit_portable_exe': 'Informe um executável portable .exe.',
        'msg_edit_pillow': 'Instale Pillow para carregar PNG/JPG.',
        'msg_edit_image_format': 'Escolha uma imagem PNG ou JPG.',
        'msg_edit_title_error': 'Configuração',
        'msg_portable_error': 'Selecione um EXE dentro da pasta de extração.',
        'msg_pillow_info': 'Instale Pillow com Preparar_imagens.bat, feche e reabra o programa.',
        'log_scale_none': 'Não foi possível consultar a escala do monitor. Mantida a escala natural; reinício automático indisponível.',
        'log_scale_info': 'Escala do monitor: {actual}%. Referência máxima do conteúdo: {max}%.',
        'log_scale_changed': 'Escala alterada. Reinício do aplicativo aguardando fim da fila e fechamento das configurações.',
        'log_restart_fail': 'Não foi possível reiniciar: {exc}',
        'install_starting': 'Iniciando: {name}',
        'install_msi_silent': 'Iniciando MSI em modo silencioso.',
        'install_msi_passive': 'Iniciando MSI em modo passivo (com progresso).',
        'install_msi_log': 'Log detalhado MSI: {path}',
        'install_exe_args': 'Iniciando EXE com os argumentos cadastrados.',
        'install_exe_noargs': 'Iniciando EXE sem argumentos; pode abrir o assistente normal.',
        'install_msi_done': 'Instalação MSI concluída (código 0)',
        'install_exe_done': 'EXE encerrado com sucesso (0); confirme o programa instalado',
        'install_msi_reboot_pending': 'Instalado; reinício pendente (3010)',
        'install_msi_reboot_started': 'Instalado; reinício iniciado (1641)',
        'install_waiting': 'Aguardando o instalador encerrar… {s}s decorridos (não é porcentagem de progresso).',
        'install_finished': 'Processo terminou em {s:.1f}s; código de saída {code}.',
        'install_msi_stage': 'MSI: {stage}…',
        'extract_done': 'Extração concluída: {path}',
        'extract_error': '7-Zip retornou {code}. Confira a senha e o log.',
        'shortcuts_created': 'Atalhos criados para {name}',
        'shortcut_failed': 'AVISO de atalho: {exc}',
        'error_prefix': 'ERRO — {exc}',
        'theme_saved_error': 'Tema aplicado, mas não foi possível salvar: {exc}',
        'theme_saved_error_title': 'Aparência',
        'lang_saved_error': 'Idioma alterado, mas não foi possível salvar: {exc}',
        'lang_saved_error_title': 'Idioma',
        # NOVAS CHAVES DA ETAPA 3
        'btn_appearance': '🎨 Aparência',
        'appearance_window_title': 'Personalizar Aparência',
        'appearance_intro': 'Escolha as cores abaixo. As alterações são aplicadas imediatamente.',
        'appearance_bg': 'Fundo da janela',
        'appearance_card': 'Caixas / cartões',
        'appearance_button': 'Botões',
        'appearance_text': 'Letras',
        'appearance_reset': 'Restaurar padrão',
        'appearance_apply': 'Aplicar',
        'appearance_close': 'Fechar',
        'appearance_choose': 'Escolher cor',
        'appearance_saved': 'Aparência salva com sucesso.',
        'appearance_saved_title': 'Aparência',
        'appearance_error': 'Não foi possível salvar: {exc}',
        'appearance_error_title': 'Erro',
    },
    'en': {
        'app_title': 'Installation Center',
        'app_icon': '⚙',
        'header_title': 'Installation Automation',
        'header_subtitle': 'Select programs and click Install Selected.',
        'btn_add': '＋ Add',
        'btn_configure': 'Configure item',
        'btn_open_item_folder': 'Item folder',
        'btn_open_root_folder': 'Root folder',
        'btn_more_options': 'More options ▾',
        'btn_select_all': 'Select all',
        'btn_install': '↓   Install Selected',
        'btn_stop': 'Stop after current item',
        'progress_count': '{done}/{total} completed',
        'btn_open_logs': 'Open logs',
        'log_title': 'Installation log',
        'status_ready': 'Ready. No package is executed when added.',
        'appearance_label': 'Appearance',
        'language_label': 'Language',
        'theme_blue': 'Blue',
        'theme_gray': 'Graphite',
        'menu_backup': 'Backup catalog...',
        'menu_import': 'Import catalog backup...',
        'menu_change_root': 'Change root folder',
        'menu_create_shortcuts': 'Create item shortcuts',
        'menu_open_catalog': 'Open visual catalog folder',
        'menu_remove': 'Remove item from catalog',
        'menu_about': 'About / third-party licenses',
        'catalog_empty': 'Your catalog is empty.\nClick ＋ Add to select installers and archives.',
        'card_exe': 'EXE',
        'card_msi': 'MSI',
        'card_zip': 'ZIP',
        'status_ready_short': 'Ready',
        'status_processing': 'Processing…',
        'status_error': 'Error',
        'selection_info': '{sel} of {total} program(s) selected',
        'queue_finished': 'Queue finished. Check results and logs.',
        'msg_select_item': 'Click a program name/card or use its gear icon.',
        'msg_select_item_title': 'Select item',
        'msg_no_selection': 'Select at least one program.',
        'msg_no_selection_title': 'Selection',
        'msg_confirm_run': 'Installers modify the system. Only run trusted files. Continue?',
        'msg_confirm_run_title': 'Confirm execution',
        'msg_processing': 'Use Stop after current item and wait for the process to finish.',
        'msg_processing_title': 'Processing',
        'msg_backup_ok': 'Catalog successfully copied to:\n{path}',
        'msg_backup_title': 'Backup',
        'msg_backup_error': 'Could not save backup:\n{exc}',
        'msg_backup_error_title': 'Backup error',
        'msg_import_invalid': 'Invalid or corrupted file:\n{exc}',
        'msg_import_error_title': 'Import error',
        'msg_import_question': 'Do you want to MERGE backup items with your current catalog?\n\nYes = Merge (adds new, keeps existing)\nNo = Replace (deletes current, uses only backup)\nCancel = Cancel import\n\nWarning: file paths (installers, ZIPs) are not transferred and will need to be reviewed.',
        'msg_import_title': 'Import Catalog',
        'msg_import_merged': 'Import complete. {count} new item(s) added to catalog.',
        'msg_import_replaced': 'Catalog replaced successfully.',
        'msg_import_confirm_title': 'Confirm Replacement',
        'msg_import_confirm': 'Are you sure? The current catalog will be permanently replaced by the backup.',
        'msg_catalog_copy_question': 'This preview uses a separate catalog. Copy programs and preferences from the previous version?\n\nThe old catalog will not be changed. Installed/extracted files remain in the same locations.',
        'msg_catalog_copy_title': 'Copy existing catalog?',
        'msg_catalog_invalid': 'Could not load. A copy has been preserved.\n{exc}',
        'msg_catalog_error_title': 'Catalog',
        'msg_shortcuts_config': 'Configure the portable executable and shortcut locations first.',
        'msg_shortcuts_title': 'Shortcuts',
        'msg_shortcuts_confirm': 'Create configured shortcuts for {name}?',
        'msg_shortcuts_ok': 'Shortcuts created. To pin: Start > All > program > right click > Pin to Start.',
        'msg_root_question': 'Use this user\'s default folder?\n\n{path}\n\nYes = default\nNo = choose another\nCancel = keep: {current}',
        'msg_root_title': 'Extraction folder',
        'msg_update_dest_question': '{count} item(s) use the previous root. Update registered destinations?\n\nThis does NOT move files or fix shortcuts. Choose No to keep programs where they are.',
        'msg_update_dest_title': 'Update destinations?',
        'msg_remove_confirm': 'Remove {name} from catalog?\nNo installer or extracted folder will be deleted.',
        'msg_remove_title': 'Remove',
        'msg_dest_not_exists': 'The extraction folder does not exist yet.',
        'msg_dest_title': 'Destination',
        'msg_format_unsupported': 'Unsupported format: {name}',
        'msg_format_title': 'Format',
        'msg_edit_title': 'Configure program',
        'msg_edit_window': 'Configure — {name}',
        'field_name': 'Name',
        'field_description': 'Description (optional)',
        'field_source': 'Source file',
        'field_action': 'Action',
        'field_dest': 'Extraction destination',
        'field_inner': 'Relative internal installer',
        'field_args': 'EXE/MSI arguments',
        'field_portable': 'Relative portable executable',
        'field_icon': 'PNG/JPG icon (optional)',
        'field_password': 'Archive password',
        'field_show_password': 'Show',
        'field_silent': 'Silent MSI (EXE uses arguments above)',
        'field_desktop': 'Create desktop shortcut',
        'field_startmenu': 'Add to Start app list (not pinned)',
        'field_hint': 'Relative internal path: ProgramFolder\\program.exe\nDestination is for extraction, not the EXE/MSI install location.\nPassword saved in plain text. Icon and description are optional.\nExisting extracted files are ignored. Use an empty folder after partial failure.',
        'btn_choose': 'Choose',
        'btn_choose_exe': 'Choose EXE',
        'btn_clear': 'Clear',
        'btn_cancel': 'Cancel',
        'btn_save': 'Save configuration',
        'msg_edit_invalid': 'Check the name and source file.',
        'msg_edit_format': 'Unsupported source format.',
        'msg_edit_action': 'Invalid action.',
        'msg_edit_dest_required': 'Enter the extraction folder.',
        'msg_edit_shortcut_install': 'Portable shortcuts require an extraction action.',
        'msg_edit_portable_exe': 'Enter a portable .exe executable.',
        'msg_edit_pillow': 'Install Pillow to load PNG/JPG.',
        'msg_edit_image_format': 'Choose a PNG or JPG image.',
        'msg_edit_title_error': 'Configuration',
        'msg_portable_error': 'Select an EXE inside the extraction folder.',
        'msg_pillow_info': 'Install Pillow with Preparar_imagens.bat, close and reopen the program.',
        'log_scale_none': 'Could not query monitor scale. Natural scale kept; auto-restart unavailable.',
        'log_scale_info': 'Monitor scale: {actual}%. Maximum content reference: {max}%.',
        'log_scale_changed': 'Scale changed. App restart waiting for queue end and settings closure.',
        'log_restart_fail': 'Could not restart: {exc}',
        'install_starting': 'Starting: {name}',
        'install_msi_silent': 'Starting MSI in silent mode.',
        'install_msi_passive': 'Starting MSI in passive mode (with progress).',
        'install_msi_log': 'Detailed MSI log: {path}',
        'install_exe_args': 'Starting EXE with configured arguments.',
        'install_exe_noargs': 'Starting EXE without arguments; may open normal wizard.',
        'install_msi_done': 'MSI installation completed (code 0)',
        'install_exe_done': 'EXE ended successfully (0); confirm the program is installed',
        'install_msi_reboot_pending': 'Installed; reboot pending (3010)',
        'install_msi_reboot_started': 'Installed; reboot started (1641)',
        'install_waiting': 'Waiting for installer to finish… {s}s elapsed (not a progress percentage).',
        'install_finished': 'Process finished in {s:.1f}s; exit code {code}.',
        'install_msi_stage': 'MSI: {stage}…',
        'extract_done': 'Extraction completed: {path}',
        'extract_error': '7-Zip returned {code}. Check password and log.',
        'shortcuts_created': 'Shortcuts created for {name}',
        'shortcut_failed': 'Shortcut WARNING: {exc}',
        'error_prefix': 'ERROR — {exc}',
        'theme_saved_error': 'Theme applied, but could not save: {exc}',
        'theme_saved_error_title': 'Appearance',
        'lang_saved_error': 'Language changed, but could not save: {exc}',
        'lang_saved_error_title': 'Language',
        # NEW KEYS STAGE 3
        'btn_appearance': '🎨 Appearance',
        'appearance_window_title': 'Customize Appearance',
        'appearance_intro': 'Choose the colors below. Changes are applied immediately.',
        'appearance_bg': 'Window background',
        'appearance_card': 'Boxes / cards',
        'appearance_button': 'Buttons',
        'appearance_text': 'Text',
        'appearance_reset': 'Restore default',
        'appearance_apply': 'Apply',
        'appearance_close': 'Close',
        'appearance_choose': 'Choose color',
        'appearance_saved': 'Appearance saved successfully.',
        'appearance_saved_title': 'Appearance',
        'appearance_error': 'Could not save: {exc}',
        'appearance_error_title': 'Error',
    }
}

def _load_language():
    try:
        data = json.loads(LANG_FILE.read_text(encoding='utf-8'))
        lang = data.get('lang', 'pt')
        if lang in ('pt', 'en'):
            return lang
    except (OSError, ValueError, AttributeError):
        pass
    return 'pt'

def _save_language(lang):
    try:
        write_json(LANG_FILE, {'lang': lang})
    except OSError as exc:
        return exc
    return None

CURRENT_LANG = _load_language()

def tr(key, **kwargs):
    text = TRANSLATIONS.get(CURRENT_LANG, {}).get(key) or TRANSLATIONS['pt'].get(key) or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text

class App(tk.Tk):
    def __init__(self):
        super().__init__();self._setup_scale_limit();self.title(tr('app_title')+' — '+VERSION);self.geometry('1160x850');self.minsize(760,560);self.configure(bg=BG)
        # Carrega paleta personalizada, se existir
        custom = load_custom_palette()
        if custom:
            apply_palette(custom)
            self.configure(bg=BG)
        self.busy=False;self.items=[];self.active=None;self.events=queue.Queue();self.stop=threading.Event();self.controls=[];self.checks=[];self.images={};self.columns=2
        self.logfile=LOGS/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.log')
        self.base=configured_root();self.setup_styles()
        self._rebuild_ui_after_theme()
        self.after(100,self.poll)
    def _init_appearance(self,header):
        selector=tk.Frame(header,bg=BG)
        selector.pack(side='right',anchor='ne',padx=(12,0),pady=4)
        lang_frame=tk.Frame(selector,bg=BG);lang_frame.pack(anchor='e',pady=(0,6))
        tk.Label(lang_frame,text=tr('language_label'),bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left',padx=(0,6))
        self._lang_value=tk.StringVar(value={'pt':'Português','en':'English'}.get(CURRENT_LANG,'Português'))
        self._lang_selector=ttk.Combobox(lang_frame,textvariable=self._lang_value,values=('Português','English'),state='readonly',width=10)
        self._lang_selector.pack(side='left')
        self._lang_selector.bind('<<ComboboxSelected>>',self._choose_language)
        self.controls.append(self._lang_selector)
        theme_frame=tk.Frame(selector,bg=BG);theme_frame.pack(anchor='e')
        tk.Label(theme_frame,text=tr('appearance_label'),bg=BG,fg=MUTED,font=('Segoe UI',9)).pack(side='left',padx=(0,6))
        self._appearance_btn=self.button(theme_frame,tr('btn_appearance'),self.open_appearance_window)
        self._appearance_btn.pack(side='left')
        self.controls.append(self._appearance_btn)
    def _choose_language(self,event=None):
        if self.busy:return
        global CURRENT_LANG
        mapping={'Português':'pt','English':'en'}
        new_lang=mapping.get(self._lang_value.get(),'pt')
        if new_lang==CURRENT_LANG:return
        CURRENT_LANG=new_lang
        err=_save_language(new_lang)
        if err:messagebox.showwarning(tr('lang_saved_error_title'),tr('lang_saved_error',exc=str(err)))
        self._rebuild_ui()
    def _rebuild_ui(self):
        self.busy=False
        for w in self.winfo_children():
            w.destroy()
        self.controls=[];self.checks=[];self.images={}
        self.title(tr('app_title')+' — '+VERSION)
        header=tk.Frame(self,bg=BG);header.pack(fill='x',padx=24,pady=(22,12))
        tk.Label(header,text=tr('app_icon'),font=('Segoe UI Symbol',34),fg=BLUE,bg=BG).pack(side='left',padx=(0,14))
        titles=tk.Frame(header,bg=BG);titles.pack(side='left',fill='x',expand=True)
        tk.Label(titles,text=tr('header_title'),font=('Segoe UI',23,'bold'),fg=TEXT,bg=BG).pack(anchor='w')
        tk.Label(titles,text=tr('header_subtitle'),font=('Segoe UI',11),fg=MUTED,bg=BG).pack(anchor='w',pady=(4,0))
        tools=tk.Frame(self,bg=BG);tools.pack(fill='x',padx=24,pady=(0,10));self._toolbar=tools
        for text,cmd in [(tr('btn_add'),self.add),(tr('btn_configure'),self.edit),(tr('btn_open_item_folder'),self.open_destination),(tr('btn_open_root_folder'),self.open_root),(tr('btn_more_options'),self.more_menu)]:
            b=self.button(tools,text,cmd);b.pack(side='left',padx=(0,7));self.controls.append(b)
        self.root_text=tk.StringVar(value='Pasta raiz: '+str(self.base))
        tk.Label(self,textvariable=self.root_text,anchor='w',fg=MUTED,bg=BG,font=('Segoe UI',9)).pack(fill='x',padx=26,pady=(0,8))
        area=tk.Frame(self,bg=BORDER,bd=1);area.pack(fill='both',expand=True,padx=24)
        self.canvas=tk.Canvas(area,bg=PANEL,highlightthickness=0,height=280)
        sb=ttk.Scrollbar(area,orient='vertical',command=self.canvas.yview);self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.cards=tk.Frame(self.canvas,bg=PANEL);self.window=self.canvas.create_window((0,0),window=self.cards,anchor='nw')
        self.cards.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',self.resize_cards)
        self.bind('<MouseWheel>',self.mousewheel,add='+')
        selection=tk.Frame(self,bg=BG);selection.pack(fill='x',padx=24,pady=10)
        self.allvar=tk.BooleanVar(value=False)
        self.allcheck=tk.Checkbutton(selection,text=tr('btn_select_all'),variable=self.allvar,command=self.mark_all,bg=BG,fg=TEXT,activebackground=BG,activeforeground=TEXT,selectcolor=HOVER,font=('Segoe UI',11),cursor='hand2');self.allcheck.pack(side='left')
        self.count=tk.StringVar();tk.Label(selection,textvariable=self.count,bg=BG,fg=MUTED).pack(side='right')
        self.run=self.button(self,tr('btn_install'),self.start,primary=True);self.run.pack(fill='x',padx=24,ipady=7)
        progressrow=tk.Frame(self,bg=BG);progressrow.pack(fill='x',padx=24,pady=(10,6))
        self.progress=ttk.Progressbar(progressrow);self.progress.pack(side='left',fill='x',expand=True,padx=(0,12))
        self.progress_count=tk.StringVar(value='')
        tk.Label(progressrow,textvariable=self.progress_count,bg=BG,fg=MUTED,font=('Segoe UI',9,'bold')).pack(side='left',padx=(0,12))
        self.cancel=self.button(progressrow,tr('btn_stop'),self.stop.set);self.cancel.configure(state='disabled');self.cancel.pack(side='right')
        loghead=tk.Frame(self,bg=BG);loghead.pack(fill='x',padx=24,pady=(4,5))
        tk.Label(loghead,text=tr('log_title'),bg=BG,fg=TEXT,font=('Segoe UI',11,'bold')).pack(side='left')
        self.button(loghead,tr('btn_open_logs'),lambda:os.startfile(LOGS)).pack(side='right')
        logframe=tk.Frame(self,bg=BG);logframe.pack(fill='x',padx=24)
        self.log=tk.Text(logframe,height=7,bg='#141519',fg='#d8dde5',font=('Consolas',10),wrap='word',state='disabled',relief='flat',padx=10,pady=8)
        logs=ttk.Scrollbar(logframe,command=self.log.yview);self.log.configure(yscrollcommand=logs.set);logs.pack(side='right',fill='y');self.log.pack(side='left',fill='both',expand=True)
        self.info=tk.StringVar(value=tr('status_ready'))
        tk.Label(self,textvariable=self.info,bg=BG,fg=MUTED,anchor='w').pack(fill='x',padx=24,pady=(8,14))
        self._init_appearance(header)
        self._reserve_footer(area,selection,progressrow,loghead,logframe)
        self.after(180,self._layout_toolbar)
        self.refresh()
    def open_appearance_window(self):
        """Abre a janela de personalização de cores (4 opções: fundo, caixas, botões, letras)."""
        if self.busy:return
        w=tk.Toplevel(self);w.title(tr('appearance_window_title'));w.configure(bg=BG);w.transient(self);w.grab_set();w.geometry('520x360');w.resizable(False,False)
        tk.Label(w,text=tr('appearance_intro'),bg=BG,fg=TEXT,font=('Segoe UI',11),wraplength=480,justify='left').pack(anchor='w',padx=20,pady=(18,12))
        # Carrega paleta atual
        current=load_custom_palette() or {'bg':'#202125','card':'#33363c','button':'#3d424a','text':'#f2f3f5'}
        vars={}
        def make_row(label_key,key):
            row=tk.Frame(w,bg=BG);row.pack(fill='x',padx=20,pady=6)
            tk.Label(row,text=tr(label_key),bg=BG,fg=TEXT,font=('Segoe UI',10),width=20,anchor='w').pack(side='left')
            var=tk.StringVar(value=current.get(key,'#000000'));vars[key]=var
            preview=tk.Label(row,text='   ',bg=var.get(),width=4,relief='solid',bd=1);preview.pack(side='left',padx=(0,8))
            def pick():
                color=colorchooser.askcolor(color=var.get(),parent=w,title=tr('appearance_choose'))
                if color and color[1]:
                    var.set(color[1]);preview.configure(bg=color[1])
            self.button(row,tr('appearance_choose'),pick).pack(side='left')
        make_row('appearance_bg','bg')
        make_row('appearance_card','card')
        make_row('appearance_button','button')
        make_row('appearance_text','text')
        footer=tk.Frame(w,bg=BG);footer.pack(fill='x',padx=20,pady=(18,14),side='bottom')
        def reset():
            defaults={'bg':'#202125','card':'#33363c','button':'#3d424a','text':'#f2f3f5'}
            # Atualiza as variáveis e as prévias visuais
            for k,v in vars.items():
                v.set(defaults[k])
            for row in w.winfo_children():
                if isinstance(row,tk.Frame):
                    for c in row.winfo_children():
                        if isinstance(c,tk.Label) and c.cget('relief')=='solid':
                            # Descobre qual chave essa prévia representa olhando o texto do label ao lado
                            pass
            # Atualiza as prévias de forma direta: percorre os rows na ordem em que foram criados
            preview_widgets=[]
            for row in w.winfo_children():
                if isinstance(row,tk.Frame):
                    for c in row.winfo_children():
                        if isinstance(c,tk.Label) and c.cget('relief')=='solid':
                            preview_widgets.append(c)
            keys_order=['bg','card','button','text']
            for preview,key in zip(preview_widgets,keys_order):
                preview.configure(bg=defaults[key])
            # Salva a paleta padrão no arquivo
            default_palette={
                'bg':'#202125','card':'#33363c','panel':'#292b30','hover':'#41454c',
                'button':'#3d424a','buttonhover':'#515863','text':'#f2f3f5','muted':'#bcc0c8',
                'accent':'#788da5','border':'#565c66','log':'#141519',
                'top':'#3b3f47','bottom':'#101114','glow':'#707782'
            }
            err=save_custom_palette(default_palette)
            if err:
                messagebox.showerror(tr('appearance_error_title'),tr('appearance_error',exc=str(err)),parent=w)
                return
            apply_palette(default_palette)
            self.configure(bg=BG)
            self.setup_styles()
            self._rebuild_ui_after_theme()
            w.destroy()
        def apply():
            palette={
                'bg':vars['bg'].get(),
                'card':vars['card'].get(),
                'panel':vars['card'].get(),
                'hover':vars['button'].get(),
                'button':vars['button'].get(),
                'buttonhover':vars['button'].get(),
                'text':vars['text'].get(),
                'muted':vars['text'].get(),
                'accent':vars['button'].get(),
                'border':vars['button'].get(),
                'log':'#141519',
                'top':vars['bg'].get(),
                'bottom':vars['bg'].get(),
                'glow':vars['card'].get(),
            }
            err=save_custom_palette(palette)
            if err:messagebox.showerror(tr('appearance_error_title'),tr('appearance_error',exc=str(err)),parent=w);return
            apply_palette(palette)
            self.configure(bg=BG)
            self.setup_styles()
            self._rebuild_ui_after_theme()
            w.destroy()
        self.button(footer,tr('appearance_reset'),reset).pack(side='left')
        self.button(footer,tr('appearance_close'),w.destroy).pack(side='left',padx=8)
        self.button(footer,tr('appearance_apply'),apply).pack(side='right')
    def _rebuild_ui_after_theme(self):
        """Reconstrói a interface após mudar as cores, mantendo o mesmo idioma."""
        self.busy=False
        for w in self.winfo_children():
            w.destroy()
        self.controls=[];self.checks=[];self.images={}
        self.title(tr('app_title')+' — '+VERSION)
        header=tk.Frame(self,bg=BG);header.pack(fill='x',padx=24,pady=(22,12))
        tk.Label(header,text=tr('app_icon'),font=('Segoe UI Symbol',34),fg=BLUE,bg=BG).pack(side='left',padx=(0,14))
        titles=tk.Frame(header,bg=BG);titles.pack(side='left',fill='x',expand=True)
        tk.Label(titles,text=tr('header_title'),font=('Segoe UI',23,'bold'),fg=TEXT,bg=BG).pack(anchor='w')
        tk.Label(titles,text=tr('header_subtitle'),font=('Segoe UI',11),fg=MUTED,bg=BG).pack(anchor='w',pady=(4,0))
        tools=tk.Frame(self,bg=BG);tools.pack(fill='x',padx=24,pady=(0,10));self._toolbar=tools
        for text,cmd in [(tr('btn_add'),self.add),(tr('btn_configure'),self.edit),(tr('btn_open_item_folder'),self.open_destination),(tr('btn_open_root_folder'),self.open_root),(tr('btn_more_options'),self.more_menu)]:
            b=self.button(tools,text,cmd);b.pack(side='left',padx=(0,7));self.controls.append(b)
        self.root_text=tk.StringVar(value='Pasta raiz: '+str(self.base))
        tk.Label(self,textvariable=self.root_text,anchor='w',fg=MUTED,bg=BG,font=('Segoe UI',9)).pack(fill='x',padx=26,pady=(0,8))
        area=tk.Frame(self,bg=BORDER,bd=1);area.pack(fill='both',expand=True,padx=24)
        self.canvas=tk.Canvas(area,bg=PANEL,highlightthickness=0,height=280)
        sb=ttk.Scrollbar(area,orient='vertical',command=self.canvas.yview);self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.cards=tk.Frame(self.canvas,bg=PANEL);self.window=self.canvas.create_window((0,0),window=self.cards,anchor='nw')
        self.cards.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',self.resize_cards)
        self.bind('<MouseWheel>',self.mousewheel,add='+')
        selection=tk.Frame(self,bg=BG);selection.pack(fill='x',padx=24,pady=10)
        self.allvar=tk.BooleanVar(value=False)
        self.allcheck=tk.Checkbutton(selection,text=tr('btn_select_all'),variable=self.allvar,command=self.mark_all,bg=BG,fg=TEXT,activebackground=BG,activeforeground=TEXT,selectcolor=HOVER,font=('Segoe UI',11),cursor='hand2');self.allcheck.pack(side='left')
        self.count=tk.StringVar();tk.Label(selection,textvariable=self.count,bg=BG,fg=MUTED).pack(side='right')
        self.run=self.button(self,tr('btn_install'),self.start,primary=True);self.run.pack(fill='x',padx=24,ipady=7)
        progressrow=tk.Frame(self,bg=BG);progressrow.pack(fill='x',padx=24,pady=(10,6))
        self.progress=ttk.Progressbar(progressrow);self.progress.pack(side='left',fill='x',expand=True,padx=(0,12))
        self.progress_count=tk.StringVar(value='')
        tk.Label(progressrow,textvariable=self.progress_count,bg=BG,fg=MUTED,font=('Segoe UI',9,'bold')).pack(side='left',padx=(0,12))
        self.cancel=self.button(progressrow,tr('btn_stop'),self.stop.set);self.cancel.configure(state='disabled');self.cancel.pack(side='right')
        loghead=tk.Frame(self,bg=BG);loghead.pack(fill='x',padx=24,pady=(4,5))
        tk.Label(loghead,text=tr('log_title'),bg=BG,fg=TEXT,font=('Segoe UI',11,'bold')).pack(side='left')
        self.button(loghead,tr('btn_open_logs'),lambda:os.startfile(LOGS)).pack(side='right')
        logframe=tk.Frame(self,bg=BG);logframe.pack(fill='x',padx=24)
        self.log=tk.Text(logframe,height=7,bg='#141519',fg='#d8dde5',font=('Consolas',10),wrap='word',state='disabled',relief='flat',padx=10,pady=8)
        logs=ttk.Scrollbar(logframe,command=self.log.yview);self.log.configure(yscrollcommand=logs.set);logs.pack(side='right',fill='y');self.log.pack(side='left',fill='both',expand=True)
        self.info=tk.StringVar(value=tr('status_ready'))
        tk.Label(self,textvariable=self.info,bg=BG,fg=MUTED,anchor='w').pack(fill='x',padx=24,pady=(8,14))
        self._init_appearance(header)
        self._reserve_footer(area,selection,progressrow,loghead,logframe)
        self.after(180,self._layout_toolbar)
        self.refresh()

    def _monitor_scale_percent(self):
        try:
            import ctypes
            from ctypes import wintypes
            user32=ctypes.WinDLL('user32',use_last_error=True)
            user32.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
            user32.MonitorFromWindow.restype=wintypes.HANDLE
            monitor=user32.MonitorFromWindow(self.winfo_id(),2)
            api=ctypes.WinDLL('shcore',use_last_error=True).GetScaleFactorForMonitor
            api.argtypes=[wintypes.HANDLE,ctypes.POINTER(ctypes.c_int)]
            api.restype=ctypes.c_long
            value=ctypes.c_int(100)
            if api(monitor,ctypes.byref(value))==0 and 100<=value.value<=500:return value.value
        except (OSError,AttributeError):pass
        return None
    def _setup_scale_limit(self):
        self._scale_detected=self._monitor_scale_percent()
        self._scale_seen=self._scale_detected
        self._scale_stable=0
        self._scale_pending=False
        self._scale_notice=False
        actual=self._scale_detected or 100
        self._ui_ratio=min(1.0,250.0/actual)
        natural=float(self.tk.call('tk','scaling'))
        if self._ui_ratio<1.0:self.tk.call('tk','scaling',natural*self._ui_ratio)
    def _px(self,value):
        return max(1,round(value*getattr(self,'_ui_ratio',1.0)))
    def _scale_widget_spacing(self,parent):
        ratio=self._ui_ratio
        if ratio>=0.999:return
        def padding_values(widget,raw):
            if isinstance(raw,(int,float)):
                return (raw,)
            if isinstance(raw,(tuple,list)):
                return tuple(raw)
            if isinstance(raw,(str,bytes,bytearray)):
                return tuple(widget.tk.splitlist(raw))
            return tuple(widget.tk.splitlist(str(raw)))
        for widget in parent.winfo_children():
            if isinstance(widget,tk.Toplevel):continue
            if not getattr(widget,'_spacing_capped',False):
                try:
                    options=widget.keys()
                    for key in ('padx','pady','borderwidth','highlightthickness'):
                        if key in options:
                            try:
                                value=widget.winfo_pixels(widget.cget(key))
                                widget.configure(**{key:max(0,round(value*ratio))})
                            except (ValueError,TypeError,tk.TclError):pass
                    manager=widget.winfo_manager()
                    if manager in ('pack','grid'):
                        data=widget.pack_info() if manager=='pack' else widget.grid_info()
                        changes={}
                        for key in ('padx','pady','ipadx','ipady'):
                            if key not in data:continue
                            try:
                                values=padding_values(widget,data[key])
                                if not values:continue
                                changed=tuple(max(0,round(widget.winfo_pixels(v)*ratio)) for v in values)
                                changes[key]=changed if len(changed)>1 else changed[0]
                            except (ValueError,TypeError,tk.TclError):continue
                        if changes:
                            if manager=='pack':widget.pack_configure(**changes)
                            else:widget.grid_configure(**changes)
                    widget._spacing_capped=True
                except (ValueError,TypeError,tk.TclError):pass
            self._scale_widget_spacing(widget)
    def _reserve_footer(self,area,selection,progressrow,loghead,logframe):
        info_label=next((w for w in self.pack_slaves() if isinstance(w,tk.Label) and str(w.cget('textvariable'))==str(self.info)),None)
        if info_label is None:return
        for widget in (area,selection,self.run,progressrow,loghead,logframe,info_label):widget.pack_forget()
        info_label.pack(side='bottom',fill='x',padx=24,pady=(6,10))
        logframe.pack(side='bottom',fill='x',padx=24)
        loghead.pack(side='bottom',fill='x',padx=24,pady=(4,5))
        progressrow.pack(side='bottom',fill='x',padx=24,pady=(8,6))
        self.run.pack(side='bottom',fill='x',padx=24,ipady=7)
        selection.pack(side='bottom',fill='x',padx=24,pady=8)
        area.pack(side='top',fill='both',expand=True,padx=24)
        self.log.configure(height=4)
        self._scale_widget_spacing(self)
    def _watch_scale_changes(self):
        current=self._monitor_scale_percent()
        if current is not None and self._scale_detected is not None:
            if current==self._scale_seen:self._scale_stable+=1
            else:self._scale_seen=current;self._scale_stable=0
            changed=current!=self._scale_detected and self._scale_stable>=2
            if current==self._scale_detected:
                self._scale_pending=False;self._scale_notice=False
            if changed:
                self._scale_pending=True
                editing=any(isinstance(w,tk.Toplevel) and w.winfo_exists() for w in self.winfo_children())
                if self.busy or editing:
                    if not self._scale_notice:
                        self.emit(tr('log_scale_changed'))
                        self._scale_notice=True
                else:
                    self._restart_after_scale()
                    return
        self.after(1500,self._watch_scale_changes)
    def _restart_after_scale(self):
        try:
            self.save()
            if getattr(sys,'frozen',False):command=[sys.executable,'--scale-restart']
            else:command=[sys.executable,str(Path(__file__).resolve()),'--scale-restart']
            restart_env=os.environ.copy()
            if getattr(sys,'frozen',False):restart_env['PYINSTALLER_RESET_ENVIRONMENT']='1'
            spawn_process(command,cwd=str(Path(sys.executable).parent) if getattr(sys,'frozen',False) else str(Path(__file__).resolve().parent),env=restart_env)
        except (OSError,ValueError) as exc:
            self.emit(tr('log_restart_fail',exc=str(exc)))
            self._scale_detected=self._scale_seen
            self.after(1500,self._watch_scale_changes)
            return
        self.destroy()
    def setup_styles(self):
        s=ttk.Style(self);s.theme_use('clam')
        s.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10))
        s.configure('TFrame',background=BG);s.configure('TLabel',background=BG,foreground=TEXT)
        s.configure('TButton',background=CARD,foreground=TEXT,font=('Segoe UI',10,'bold'),padding=8)
        s.map('TButton',background=[('active',HOVER),('pressed',CARD)],foreground=[('active',TEXT),('disabled',MUTED)])
        s.configure('TEntry',fieldbackground='white',foreground='#111111',insertcolor='#111111')
        s.configure('TCombobox',fieldbackground='white',foreground='#111111',arrowcolor='#111111')
        s.map('TCombobox',fieldbackground=[('readonly','white')],foreground=[('readonly','#111111')],selectforeground=[('readonly','#111111')],selectbackground=[('readonly','#c8d0da')])
        s.configure('TCheckbutton',background=BG,foreground=TEXT)
        s.map('TCheckbutton',background=[('active',BG)],foreground=[('active',TEXT)])
        s.configure('Horizontal.TProgressbar',background=BLUE,troughcolor=CARD,bordercolor=BORDER,lightcolor=BLUE,darkcolor=BLUE,thickness=14,borderwidth=1)
        self.option_add('*TCombobox*Listbox.background','white');self.option_add('*TCombobox*Listbox.foreground','#111111')
        self.option_add('*TCombobox*Listbox.selectBackground','#c8d0da');self.option_add('*TCombobox*Listbox.selectForeground','#111111')
    def button(self,parent,text,cmd,primary=False):
        def colors():
            if primary:
                return (BLUE, HOVER)
            return (CARD, HOVER)
        normal,hover=colors()
        b=tk.Button(parent,text=text,command=cmd,font=('Segoe UI',15 if primary else 10,'bold'),bg=normal,fg=TEXT,activebackground=hover,activeforeground=TEXT,disabledforeground=MUTED,relief='flat',bd=0,padx=12,pady=9,cursor='hand2')
        def enter(event):
            if str(b['state'])!='disabled':b.configure(bg=hover,activebackground=hover)
        def leave(event):b.configure(bg=normal,activebackground=hover)
        b.bind('<Enter>',enter);b.bind('<Leave>',leave)
        return b
    def load_catalog(self):
        if not CONFIG.exists() and (OLD_ROOT/'catalogo.json').exists():
            if messagebox.askyesno(tr('msg_catalog_copy_title'),tr('msg_catalog_copy_question')):
                try:
                    shutil.copy2(OLD_ROOT/'catalogo.json',CONFIG)
                    if (OLD_ROOT/'preferencias.json').exists():shutil.copy2(OLD_ROOT/'preferencias.json',SETTINGS)
                    self.base=configured_root();self.root_text.set('Pasta raiz: '+str(self.base))
                except OSError as exc:messagebox.showerror('Importação',str(exc))
        try:
            if CONFIG.exists():
                data=json.loads(CONFIG.read_text(encoding='utf-8'))
                if not isinstance(data,list) or not all(isinstance(i,dict) and all(k in i for k in ('name','source','action')) for i in data):raise ValueError('Catálogo inválido.')
                self.items=data
        except Exception as exc:
            if CONFIG.exists():shutil.copy2(CONFIG,CONFIG.with_name('catalogo.invalido-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'))
            self.items=[];messagebox.showerror(tr('msg_catalog_error_title'),tr('msg_catalog_invalid',exc=str(exc)))
    def save(self):write_json(CONFIG,self.items)
    def resize_cards(self,event):
        self.canvas.itemconfigure(self.window,width=event.width)
        cols=2 if event.width>=740 else 1
        if cols!=self.columns:self.columns=cols;self.refresh()
    def mousewheel(self,event):
        try:
            widget=self.winfo_containing(event.x_root,event.y_root)
            while widget is not None:
                if widget==self.canvas or widget==self.cards:
                    self.canvas.yview_scroll(-int(event.delta/120),'units');break
                widget=widget.master
        except tk.TclError:pass
    def get_icon(self,item):
        path=item.get('icon','')
        if not path or Image is None:return None
        try:
            stamp=Path(path).stat().st_mtime_ns;key=(path,stamp)
            if key not in self.images:
                with Image.open(path) as im:
                    im=ImageOps.exif_transpose(im).convert('RGBA');im.thumbnail((self._px(48),self._px(48)),Image.Resampling.LANCZOS)
                    self.images[key]=ImageTk.PhotoImage(im,master=self)
            return self.images[key]
        except (OSError,ValueError):return None
    def refresh(self):
        top=self.canvas.yview()[0]
        for w in self.cards.winfo_children():w.destroy()
        self.checks=[];self.card_frames={};self.checkvars={}
        for c in (0,1):self.cards.columnconfigure(c,weight=1 if c<self.columns else 0,uniform='cards')
        if not self.items:
            tk.Label(self.cards,text=tr('catalog_empty'),bg=PANEL,fg=MUTED,font=('Segoe UI',13),pady=50).grid(row=0,column=0,columnspan=self.columns,sticky='ew')
        for n,item in enumerate(self.items):
            active=n==self.active
            frame=tk.Frame(self.cards,bg=CARD,highlightbackground=BLUE if active else BORDER,highlightthickness=2,padx=12,pady=12)
            frame.grid(row=n//self.columns,column=n%self.columns,sticky='nsew',padx=8,pady=7)
            self.card_frames[n]=frame
            frame.columnconfigure(2,weight=1)
            var=tk.BooleanVar(value=bool(item.get('selected')))
            self.checkvars[n]=var
            check=tk.Checkbutton(frame,variable=var,command=lambda k=n,v=var:self.toggle(k,v),bg=CARD,activebackground=CARD,selectcolor=HOVER,fg=TEXT,activeforeground=TEXT,font=('Segoe UI',17),bd=0,cursor='hand2',state='disabled' if self.busy else 'normal')
            check.grid(row=0,column=0,rowspan=3,padx=(0,8));self.checks.append(check)
            icon=self.get_icon(item)
            ext=Path(item['source']).suffix.lower()
            fallback=tr('card_exe') if ext=='.exe' else tr('card_msi') if ext=='.msi' else tr('card_zip')
            pic=tk.Label(frame,image=icon,bg=CARD) if icon else tk.Label(frame,text=fallback,bg=HOVER,fg=TEXT,font=('Segoe UI',11,'bold'),width=4,height=2)
            pic.grid(row=0,column=1,rowspan=2,padx=(0,12))
            wrap=300 if self.columns==2 else 580
            name=tk.Label(frame,text=item['name'],bg=CARD,fg=TEXT,font=('Segoe UI',12,'bold'),anchor='w',justify='left',wraplength=wrap);name.grid(row=0,column=2,sticky='w')
            desc=tk.Label(frame,text=default_description(item),bg=CARD,fg=MUTED,font=('Segoe UI',10),anchor='w',justify='left',wraplength=wrap);desc.grid(row=1,column=2,sticky='w',pady=(4,0))
            status=item.get('status',tr('status_ready_short'));color='#ffbd89' if status==tr('status_error') else MUTED
            state=tk.Label(frame,text=status,bg=CARD,fg=color,font=('Segoe UI',9),anchor='w',wraplength=wrap);state.grid(row=2,column=2,sticky='w',pady=(5,0))
            gear=tk.Button(frame,text='⚙',command=lambda k=n:self.edit_index(k),font=('Segoe UI Symbol',15),bg=CARD,fg=MUTED,activebackground=HOVER,activeforeground=TEXT,relief='flat',bd=0,cursor='hand2',state='disabled' if self.busy else 'normal');gear.grid(row=0,column=3,rowspan=2,padx=(5,0))
            for w in (frame,pic,name,desc,state):
                w.bind('<Button-1>',lambda e,k=n:self.focus_item(k));w.bind('<Double-1>',lambda e,k=n:self.edit_index(k))
        selected=sum(bool(i.get('selected')) for i in self.items)
        self.count.set(tr('selection_info',sel=selected,total=len(self.items)))
        self.allvar.set(bool(self.items) and selected==len(self.items))
        self._scale_widget_spacing(self.cards);self.canvas.update_idletasks();self.canvas.yview_moveto(top)

    def update_selection_count(self):
        selected=sum(bool(i.get('selected')) for i in self.items)
        self.count.set(tr('selection_info',sel=selected,total=len(self.items)))
        self.allvar.set(bool(self.items) and selected==len(self.items))
    def focus_item(self,n):
        if self.busy:return
        old=self.active
        self.active=n
        if old in self.card_frames:
            self.card_frames[old].configure(highlightbackground=BORDER)
        if n in self.card_frames:
            self.card_frames[n].configure(highlightbackground=BLUE)
    def toggle(self,n,var):
        if self.busy:return
        self.items[n]['selected']=var.get()
        self.focus_item(n)
        self.save()
        self.update_selection_count()
    def mark_all(self):
        if self.busy:return
        value=self.allvar.get()
        for n,item in enumerate(self.items):
            item['selected']=value
            if n in self.checkvars:self.checkvars[n].set(value)
        self.save()
        self.update_selection_count()
    def selected(self):
        if self.active is None or not 0<=self.active<len(self.items):messagebox.showinfo(tr('msg_select_item_title'),tr('msg_select_item'));return None
        return self.items[self.active]

    def add(self):
        if self.busy:return
        files=filedialog.askopenfilenames(filetypes=[('Pacotes','*.exe *.msi *.zip *.7z *.rar *.tar *.gz *.bz2 *.xz'),('Todos','*.*')])
        for filename in files:
            p=Path(filename)
            if p.suffix.lower() not in ARCHIVES+('.exe','.msi'):messagebox.showwarning(tr('msg_format_title'),tr('msg_format_unsupported',name=p.name));continue
            self.items.append(dict(name=p.stem,source=str(p),selected=True,action='Extrair' if p.suffix.lower() in ARCHIVES else 'Instalar',dest=str(self.base/p.stem),inner='',args='',silent=False,status=tr('status_ready_short'),portable='',desktop=False,startmenu=False,password='',description='',icon=''))
            self.active=len(self.items)-1
        self.save();self.refresh()

    def backup_catalog(self):
        if self.busy: return
        default_name = f"catalogo-central-backup-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        path = filedialog.asksaveasfilename(
            title="Salvar backup do catálogo",
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("Arquivo JSON", "*.json")]
        )
        if not path:
            return
        try:
            shutil.copy2(CONFIG, path)
            messagebox.showinfo(tr('msg_backup_title'), tr('msg_backup_ok', path=path))
        except Exception as exc:
            messagebox.showerror(tr('msg_backup_error_title'), tr('msg_backup_error', exc=str(exc)))

    def import_catalog(self):
        if self.busy: return
        path = filedialog.askopenfilename(
            title="Selecionar arquivo de backup do catálogo",
            filetypes=[("Arquivo JSON", "*.json")]
        )
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                new_items = json.load(f)
            if not isinstance(new_items, list):
                raise ValueError("O arquivo não contém uma lista de programas válida.")
        except Exception as exc:
            messagebox.showerror(tr('msg_import_error_title'), tr('msg_import_invalid', exc=str(exc)))
            return

        try:
            shutil.copy2(CONFIG, CONFIG.with_suffix('.bak'))
        except Exception:
            pass

        response = messagebox.askyesnocancel(
            tr('msg_import_title'),
            tr('msg_import_question')
        )

        if response is None:
            return

        if response:
            current_names = {item['source'] for item in self.items}
            added_count = 0
            for item in new_items:
                if isinstance(item, dict) and item.get('source') not in current_names:
                    self.items.append(item)
                    added_count += 1
            messagebox.showinfo(tr('msg_import_title'), tr('msg_import_merged', count=added_count))
        else:
            if messagebox.askyesno(tr('msg_import_confirm_title'), tr('msg_import_confirm')):
                self.items = new_items
                messagebox.showinfo(tr('msg_import_title'), tr('msg_import_replaced'))

        self.save()
        self.active = None
        self.refresh()

    def more_menu(self):
        if self.busy:return
        m=tk.Menu(self,tearoff=False,bg=PANEL,fg=TEXT,activebackground=BLUE,activeforeground='white')
        for text,cmd in [
            (tr('menu_backup'), self.backup_catalog),
            (tr('menu_import'), self.import_catalog),
            ('---', None),
            (tr('menu_change_root'), self.choose_root),
            (tr('menu_create_shortcuts'), self.shortcuts),
            (tr('menu_open_catalog'), lambda:os.startfile(ROOT)),
            (tr('menu_remove'), self.remove),
            (tr('menu_about'), open_licenses)
        ]:
            if text == '---':
                m.add_separator()
            else:
                m.add_command(label=text, command=cmd)
        try:m.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:m.grab_release()
    def remove(self):
        if self.busy:return
        i=self.selected()
        if i is not None and messagebox.askyesno(tr('msg_remove_title'),tr('msg_remove_confirm',name=i["name"])):
            self.items.pop(self.active);self.active=None;self.save();self.refresh()
    def open_destination(self):
        i=self.selected()
        if i is None:return
        p=Path(i.get('dest',''))
        if not p.is_dir():return messagebox.showinfo(tr('msg_dest_title'),tr('msg_dest_not_exists'))
        try:os.startfile(p)
        except OSError as exc:messagebox.showerror(tr('msg_dest_title'),str(exc))
    def open_root(self):
        try:self.base.mkdir(parents=True,exist_ok=True);os.startfile(self.base)
        except OSError as exc:messagebox.showerror(tr('msg_root_title'),str(exc))
    def shortcuts(self):
        if self.busy:return
        i=self.selected()
        if i is None:return
        if not(i.get('desktop') or i.get('startmenu')):return messagebox.showinfo(tr('msg_shortcuts_title'),tr('msg_shortcuts_config'))
        if not messagebox.askyesno(tr('msg_shortcuts_title'),tr('msg_shortcuts_confirm',name=i['name'])):return
        try:create_shortcuts(i);messagebox.showinfo(tr('msg_shortcuts_title'),tr('msg_shortcuts_ok'))
        except Exception as exc:messagebox.showerror(tr('msg_shortcuts_title'),str(exc))
    def choose_root(self):
        if self.busy:return
        answer=messagebox.askyesnocancel(tr('msg_root_title'),tr('msg_root_question',path=str(Path.home()/'ProgramasExtraidos'),current=str(self.base)))
        if answer is None:return
        if answer:newbase=Path.home()/'ProgramasExtraidos';settings={'mode':'default'}
        else:
            folder=filedialog.askdirectory(title='Pasta raiz',initialdir=str(self.base if self.base.is_dir() else Path.home()))
            if not folder:return
            newbase=Path(folder).resolve();settings={'mode':'custom','path':str(newbase)}
        oldbase=self.base.resolve()
        try:newbase.mkdir(parents=True,exist_ok=True);write_json(SETTINGS,settings)
        except OSError as exc:return messagebox.showerror(tr('msg_root_title'),str(exc))
        self.base=newbase;self.root_text.set('Pasta raiz: '+str(self.base));affected=[]
        if oldbase!=newbase.resolve():
            for i in self.items:
                try:
                    rel=Path(i.get('dest','')).resolve().relative_to(oldbase)
                    if rel.parts:affected.append((i,rel))
                except (ValueError,OSError):pass
        if affected and messagebox.askyesno(tr('msg_update_dest_title'),tr('msg_update_dest_question',count=len(affected))):
            for i,rel in affected:i['dest']=str(newbase/rel)
            self.save();self.refresh()
    def edit_index(self,n):
        if self.busy:return
        self.focus_item(n)
        self.edit()
    def edit(self):
        if self.busy:return
        item=self.selected()
        if item is None:return
        w=tk.Toplevel(self);w.title(tr('msg_edit_window',name=item['name']));w.geometry('920x760');w.minsize(760,550);w.configure(bg=BG);w.transient(self);w.grab_set()
        tk.Label(w,text=tr('msg_edit_title'),bg=BG,fg=TEXT,font=('Segoe UI',17,'bold')).pack(anchor='w',padx=20,pady=14)
        outer=tk.Frame(w,bg=BG);outer.pack(fill='both',expand=True,padx=15)
        canvas=tk.Canvas(outer,bg=BG,highlightthickness=0);scroll=ttk.Scrollbar(outer,command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        body=tk.Frame(canvas,bg=BG);body.columnconfigure(1,weight=1);window=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        def wheel(e):canvas.yview_scroll(-int(e.delta/120),'units');return 'break'
        w.bind('<MouseWheel>',wheel)
        keys=['name','description','source','action','dest','inner','args','portable','icon']
        v={k:tk.StringVar(value=item.get(k,'')) for k in keys}
        def field(label,key,row):
            ttk.Label(body,text=label).grid(row=row,column=0,padx=8,pady=9,sticky='w')
            entry=ttk.Combobox(body,textvariable=v[key],values=ACTIONS,state='readonly') if key=='action' else ttk.Entry(body,textvariable=v[key])
            entry.grid(row=row,column=1,padx=8,pady=4,sticky='ew');return entry
        for row,(label,key) in enumerate([(tr('field_name'),'name'),(tr('field_description'),'description'),(tr('field_source'),'source'),(tr('field_action'),'action'),(tr('field_dest'),'dest'),(tr('field_inner'),'inner'),(tr('field_args'),'args'),(tr('field_portable'),'portable'),(tr('field_icon'),'icon')]):field(label,key,row)
        def source_pick():
            p=filedialog.askopenfilename(parent=w)
            if p:v['source'].set(p)
        self.button(body,tr('btn_choose'),source_pick).grid(row=2,column=2,padx=5)
        def folder_pick():
            p=filedialog.askdirectory(parent=w)
            if p:v['dest'].set(p)
        self.button(body,tr('btn_choose'),folder_pick).grid(row=4,column=2,padx=5)
        def exe_pick():
            p=filedialog.askopenfilename(parent=w,initialdir=v['dest'].get(),filetypes=[('Executável','*.exe')])
            if not p:return
            try:v['portable'].set(str(Path(p).resolve().relative_to(Path(v['dest'].get()).resolve())))
            except ValueError:messagebox.showerror('Portable',tr('msg_portable_error'),parent=w)
        self.button(body,tr('btn_choose_exe'),exe_pick).grid(row=7,column=2,padx=5)
        def icon_pick():
            if Image is None:return messagebox.showinfo('Imagens',tr('msg_pillow_info'),parent=w)
            p=filedialog.askopenfilename(parent=w,filetypes=[('Imagens','*.png *.jpg *.jpeg')])
            if p:v['icon'].set(p)
        iconbar=tk.Frame(body,bg=BG);iconbar.grid(row=8,column=2,padx=5)
        self.button(iconbar,tr('btn_choose'),icon_pick).pack(side='left');self.button(iconbar,tr('btn_clear'),lambda:v['icon'].set('')).pack(side='left',padx=4)
        password=tk.StringVar(value=item.get('password',''));ttk.Label(body,text=tr('field_password')).grid(row=9,column=0,padx=8,pady=9,sticky='w')
        passwordentry=ttk.Entry(body,textvariable=password,show='*');passwordentry.grid(row=9,column=1,padx=8,sticky='ew')
        show=tk.BooleanVar(value=False);ttk.Checkbutton(body,text=tr('field_show_password'),variable=show,command=lambda:passwordentry.configure(show='' if show.get() else '*')).grid(row=9,column=2)
        silent=tk.BooleanVar(value=item.get('silent',False));desktop=tk.BooleanVar(value=item.get('desktop',False));startmenu=tk.BooleanVar(value=item.get('startmenu',False))
        for row,text,var in [(10,tr('field_silent'),silent),(11,tr('field_desktop'),desktop),(12,tr('field_startmenu'),startmenu)]:ttk.Checkbutton(body,text=text,variable=var).grid(row=row,column=0,columnspan=3,padx=8,pady=7,sticky='w')
        ttk.Label(body,text=tr('field_hint'),wraplength=740).grid(row=13,column=0,columnspan=3,padx=8,pady=15,sticky='w')
        def accept():
            data={k:x.get().strip() for k,x in v.items()}
            try:
                if not data['name'] or not Path(data['source']).is_file():raise ValueError(tr('msg_edit_invalid'))
                if Path(data['source']).suffix.lower() not in ARCHIVES+('.exe','.msi'):raise ValueError(tr('msg_edit_format'))
                if data['action'] not in ACTIONS:raise ValueError(tr('msg_edit_action'))
                if data['action']!='Instalar' and not data['dest']:raise ValueError(tr('msg_edit_dest_required'))
                if data['action']=='Extrair e instalar':internal(data['dest'],data['inner'])
                if desktop.get() or startmenu.get():
                    if data['action']=='Instalar':raise ValueError(tr('msg_edit_shortcut_install'))
                    if internal(data['dest'],data['portable']).suffix.lower()!='.exe':raise ValueError(tr('msg_edit_portable_exe'))
                if data['icon'] and data['icon']!=item.get('icon',''):
                    if Image is None:raise ValueError(tr('msg_edit_pillow'))
                    with Image.open(data['icon']) as im:
                        if im.format not in ('PNG','JPEG'):raise ValueError(tr('msg_edit_image_format'))
                        normalized=ImageOps.exif_transpose(im).convert('RGBA');normalized.thumbnail((256,256),Image.Resampling.LANCZOS)
                        owned=ICONS/(uuid.uuid4().hex+'.png');normalized.save(owned)
                    data['icon']=str(owned)
                data['password']=password.get();item.update(data,silent=silent.get(),desktop=desktop.get(),startmenu=startmenu.get(),status=tr('status_ready_short'))
                self.save();self.refresh();w.destroy()
            except Exception as exc:messagebox.showerror(tr('msg_edit_title_error'),str(exc),parent=w)
        footer=tk.Frame(w,bg=BG);footer.pack(fill='x',padx=20,pady=15)
        self.button(footer,tr('btn_cancel'),w.destroy).pack(side='left');self.button(footer,tr('btn_save'),accept).pack(side='right')

    def start(self):
        if self.busy:return
        jobs=[(n,dict(i)) for n,i in enumerate(self.items) if i.get('selected')]
        if not jobs:return messagebox.showinfo(tr('msg_no_selection_title'),tr('msg_no_selection'))
        summary='\n'.join(i['name']+': '+i['action'] for _,i in jobs)
        if not messagebox.askyesno(tr('msg_confirm_run_title'),summary+'\n\n'+tr('msg_confirm_run')):return
        self.busy=True;self.stop.clear();self.progress['maximum']=len(jobs);self.progress['value']=0
        self.progress_count.set(tr('progress_count',done=0,total=len(jobs)))
        for b in self.controls+[self.run,self.allcheck]:b.configure(state='disabled')
        self.cancel.configure(state='normal');self.refresh();threading.Thread(target=self.worker,args=(jobs,),daemon=True).start()
    def emit(self,text):self.events.put(('log',text))
    def _fit_readable_window(self):
        self.update_idletasks()
        sw=self.winfo_screenwidth();sh=self.winfo_screenheight()
        width=min(self._px(1160),max(480,sw-48))
        height=min(self._px(850),max(400,sh-96))
        self.minsize(min(self._px(760),width),min(self._px(460),height))
        self.geometry(f'{width}x{height}')
        self.log.configure(height=4)
        actual=self._scale_detected
        if actual is None:self.emit(tr('log_scale_none'))
        else:self.emit(tr('log_scale_info',actual=actual,max=min(actual,250)))
    def _queue_layout(self,event):
        if event.widget!=self:return
        if getattr(self,'_layout_job',None):self.after_cancel(self._layout_job)
        self._layout_job=self.after(180,self._layout_toolbar)
    def _layout_toolbar(self):
        self._layout_job=None
        toolbar=getattr(self,'_toolbar',None)
        if toolbar is None:return
        buttons=[w for w in toolbar.winfo_children() if isinstance(w,tk.Button)]
        if not buttons:return
        available=max(260,self.winfo_width()-64)
        signature=(available,tuple(w.winfo_reqwidth() for w in buttons))
        if signature==getattr(self,'_toolbar_signature',None):return
        self._toolbar_signature=signature
        for b in buttons:
            if b.winfo_manager()=='pack':b.pack_forget()
        row=0;column=0;used=0
        for b in buttons:
            width=b.winfo_reqwidth()+7
            if used and used+width>available:row+=1;column=0;used=0
            b.grid(row=row,column=column,padx=(0,7),pady=(0,5),sticky='w')
            used+=width;column+=1
    def _read_msi_text(self,path):
        if path is None:return ''
        try:
            raw=Path(path).read_bytes()
            if raw.startswith((b'\xff\xfe',b'\xfe\xff')):return raw.decode('utf-16',errors='replace')
            if raw[:200].count(b'\x00')>10:return raw.decode('utf-16-le',errors='replace')
            try:return raw.decode('utf-8-sig')
            except UnicodeDecodeError:return raw.decode('cp1252',errors='replace')
        except OSError:return ''
    def _msi_reason(self,result,text):
        import re
        if result==1603 and re.search(r'a newer version of [^\r\n]+ is already installed',text,re.I):
            return 'Instalação bloqueada: o MSI detectou uma versão mais nova. A versão solicitada não foi instalada.' if CURRENT_LANG=='pt' else 'Installation blocked: the MSI detected a newer version. The requested version was not installed.'
        messages={
            1602:'Instalação cancelada.' if CURRENT_LANG=='pt' else 'Installation canceled.',
            1618:'Há outra instalação em andamento. Aguarde e tente novamente.' if CURRENT_LANG=='pt' else 'Another installation is in progress. Wait and try again.',
            1619:'O Windows Installer não conseguiu abrir o pacote. Confira o arquivo e as permissões.' if CURRENT_LANG=='pt' else 'Windows Installer could not open the package. Check the file and permissions.',
            1638:'Outra versão deste produto já está instalada. Consulte o log para verificar a incompatibilidade.' if CURRENT_LANG=='pt' else 'Another version of this product is already installed. Check the log for incompatibility.'
        }
        return messages.get(result,f'Instalação falhou (código {result}). O código sozinho não determina a causa; consulte o log detalhado.' if CURRENT_LANG=='pt' else f'Installation failed (code {result}). The code alone does not determine the cause; check the detailed log.')
    def _watch_installer(self,command,cwd,msi_log=None):
        import time,re
        started=time.monotonic();last_notice=started;last_scan=0;last_action=''
        process=spawn_process(command,cwd=str(cwd),shell=False)
        stages={'CostInitialize':'Calculando requisitos' if CURRENT_LANG=='pt' else 'Calculating requirements','CostFinalize':'Verificando espaço e destinos' if CURRENT_LANG=='pt' else 'Checking space and destinations','InstallValidate':'Validando instalação' if CURRENT_LANG=='pt' else 'Validating installation','InstallFiles':'Copiando arquivos' if CURRENT_LANG=='pt' else 'Copying files','WriteRegistryValues':'Gravando configurações' if CURRENT_LANG=='pt' else 'Writing settings','CreateShortcuts':'Criando atalhos' if CURRENT_LANG=='pt' else 'Creating shortcuts','InstallFinalize':'Finalizando instalação' if CURRENT_LANG=='pt' else 'Finalizing installation','LaunchConditions':'Verificando condições de instalação' if CURRENT_LANG=='pt' else 'Checking install conditions','FindRelatedProducts':'Verificando versões existentes' if CURRENT_LANG=='pt' else 'Checking existing versions'}
        while process.poll() is None:
            now=time.monotonic()
            if msi_log is not None and now-last_scan>=2:
                last_scan=now;text=self._read_msi_text(msi_log)
                actions=re.findall(r'Action start [^\r\n]*?: ([A-Za-z_][A-Za-z_0-9.]*)\.',text)
                if actions and actions[-1]!=last_action:
                    last_action=actions[-1]
                    if last_action in stages:self.emit(tr('install_msi_stage',stage=stages[last_action]))
            if now-last_notice>=8:
                seconds=int(now-started)
                self.emit(tr('install_waiting',s=seconds))
                last_notice=now
            time.sleep(0.35)
        elapsed=time.monotonic()-started
        self.emit(tr('install_finished',s=elapsed,code=process.returncode))
        return process.returncode
    def install(self,p,item):
        if not p.is_file():raise ValueError('Instalador não encontrado: '+str(p))
        ext=p.suffix.lower();extra=item.get('args','');msi_log=None
        if ext=='.msi':
            exe=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/msiexec.exe'
            msi_log=LOGS/('msi-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.log')
            args='/i '+subprocess.list2cmdline([str(p)])+' /norestart /L*v '+subprocess.list2cmdline([str(msi_log)])
            args+=' /quiet' if item.get('silent') else ' /passive';args+=' '+extra
            self.emit(tr('install_msi_silent') if item.get('silent') else tr('install_msi_passive'))
            self.emit(tr('install_msi_log',path=str(msi_log)))
        elif ext=='.exe':
            exe=p;args=extra
            self.emit(tr('install_exe_args') if extra else tr('install_exe_noargs'))
        else:raise ValueError('Instalador precisa ser .exe ou .msi.')
        command=subprocess.list2cmdline([str(exe)])+' '+args
        result=self._watch_installer(command,p.parent,msi_log)
        if result==0:return tr('install_msi_done') if ext=='.msi' else tr('install_exe_done')
        if ext=='.msi':
            if result==3010:return tr('install_msi_reboot_pending')
            if result==1641:self.stop.set();return tr('install_msi_reboot_started')
            raise RuntimeError(self._msi_reason(result,self._read_msi_text(msi_log))+' Log: '+str(msi_log))
        raise RuntimeError(f'EXE retornou {result}. A interpretação depende do fabricante; instalação não confirmada.')
    def worker(self,jobs):
        try:
            for pos,(n,item) in enumerate(jobs,1):
                if self.stop.is_set():break
                self.events.put(('status',n,tr('status_processing')));self.emit(tr('install_starting',name=item['name']))
                try:
                    p=Path(item['source']).resolve();action=item['action']
                    if not p.is_file():raise ValueError('Arquivo de origem não encontrado.')
                    if action not in ACTIONS:raise ValueError('Ação inválida.')
                    if action=='Instalar':state=self.install(p,item)
                    else:
                        if p.suffix.lower() not in ARCHIVES:raise ValueError('Esta ação exige um compactado suportado.')
                        z=find7z();dest=Path(item['dest']).resolve()
                        if action=='Extrair e instalar':
                            installer=internal(dest,item.get('inner',''))
                            if installer.exists():raise ValueError('Instalador interno já existe. Use destino novo para evitar executar arquivo antigo.')
                        dest.mkdir(parents=True,exist_ok=True)
                        password=item.get('password') or '__SEM_SENHA_CONFIGURADA__'
                        command=[z,'x',str(p),'-o'+str(dest),'-aos','-y','-spd','-p'+password]
                        with self.logfile.open('a',encoding='utf-8') as log:
                            log.write('\n--- Saída do 7-Zip (comando/senha não registrados) ---\n');log.flush()
                            result=run_process(command,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW).returncode
                        if result!=0:raise RuntimeError(tr('extract_error',code=result))
                        self.emit(tr('extract_done',path=str(dest)))
                        state=self.install(internal(dest,item['inner']),item) if action=='Extrair e instalar' else 'Extração concluída'
                        if item.get('desktop') or item.get('startmenu'):
                            try:create_shortcuts(item);self.emit(tr('shortcuts_created',name=item['name']))
                            except Exception as exc:state+='; atalho falhou';self.emit(tr('shortcut_failed',exc=str(exc)))
                    self.events.put(('status',n,state));self.emit(item['name']+': '+state)
                except Exception as exc:self.events.put(('status',n,tr('status_error')));self.emit(item['name']+': '+tr('error_prefix',exc=str(exc)))
                self.events.put(('progress',pos))
        finally:self.events.put(('done',))
    def poll(self):
        try:
            while True:
                e=self.events.get_nowait()
                if e[0]=='log':
                    text=datetime.datetime.now().strftime('[%H:%M:%S] ')+e[1]+'\n'
                    with self.logfile.open('a',encoding='utf-8') as f:f.write(text)
                    self.log.configure(state='normal');self.log.insert('end',text);self.log.see('end');self.log.configure(state='disabled')
                elif e[0]=='status':self.items[e[1]]['status']=e[2];self.refresh();self.info.set(self.items[e[1]]['name']+': '+e[2])
                elif e[0]=='progress':
                    self.progress['value']=e[1]
                    self.progress_count.set(tr('progress_count',done=e[1],total=int(self.progress['maximum'])))
                elif e[0]=='done':
                    self.busy=False;self.save()
                    for b in self.controls+[self.run,self.allcheck]:b.configure(state='normal')
                    self.cancel.configure(state='disabled');self.refresh();self.info.set(tr('queue_finished'))
        except queue.Empty:pass
        self.after(100,self.poll)
    def close(self):
        if self.busy:return messagebox.showinfo(tr('msg_processing_title'),tr('msg_processing'))
        self.save();self.destroy()

if __name__=='__main__':
    if sys.platform!='win32':raise SystemExit('Esta versão é destinada ao Windows.')
    if '--self-test' in sys.argv:raise SystemExit(self_test())
    from perfis_instalacao import integrate
    integrate(App, globals())
    App().mainloop()