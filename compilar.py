import argparse,ast,ctypes,hashlib,importlib.metadata,json,os,platform,shutil,struct,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def initial_dpi_awareness():
    try:
        value=ctypes.c_int()
        if ctypes.windll.shcore.GetProcessDpiAwareness(None,ctypes.byref(value))==0:return value.value
    except (OSError,AttributeError):pass
    return 0
INITIAL_DPI=initial_dpi_awareness() if sys.platform=='win32' else 0

def choose_file(title,types):
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw()
    try:value=filedialog.askopenfilename(title=title,filetypes=types)
    finally:root.destroy()
    if not value:raise RuntimeError('Seleção cancelada.')
    return Path(value)

def choose_folder(title):
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw()
    try:value=filedialog.askdirectory(title=title)
    finally:root.destroy()
    if not value:raise RuntimeError('Seleção cancelada.')
    return Path(value)

def pe_machine(path):
    with path.open('rb') as f:
        if f.read(2)!=b'MZ':raise ValueError('Não é um binário PE: '+path.name)
        f.seek(0x3c);offset=struct.unpack('<I',f.read(4))[0];f.seek(offset)
        if f.read(4)!=b'PE\x00\x00':raise ValueError('Cabeçalho PE inválido: '+path.name)
        return struct.unpack('<H',f.read(2))[0]

def copy_if_different(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if source.resolve()!=target.resolve():shutil.copy2(source,target)

def prepare_profiles(arg):
    path=Path(arg) if arg else HERE/'perfis_instalacao.json'
    if not path.is_file():path=choose_file('Selecione perfis_instalacao.json atual (NÃO catalogo.json)',[('Biblioteca JSON','*.json')])
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data,list) or not data:raise ValueError('Biblioteca vazia ou inválida.')
    import re
    ids=set()
    for p in data:
        if not isinstance(p,dict) or not all(k in p for k in ('id','name','filename_regex','product_regex','publisher_regex','arguments','source','note')):raise ValueError('O arquivo não é a biblioteca de perfis esperada.')
        if p['id'] in ids:raise ValueError('ID duplicado: '+p['id'])
        ids.add(p['id'])
        for field in ('filename_regex','product_regex','publisher_regex'):re.compile(p[field],re.I)
        if p['arguments'] is not None and not isinstance(p['arguments'],str):raise ValueError('Argumentos inválidos no perfil '+p['id'])
    (HERE/'perfis_instalacao.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(data)

def prepare_engine(arg):
    paths=[Path(arg)] if arg else [Path(os.environ.get(key,'C:/Program Files'))/'7-Zip' for key in ('ProgramFiles','ProgramFiles(x86)')]
    source=next((p for p in paths if (p/'7z.exe').is_file() and (p/'7z.dll').is_file()),None)
    if source is None:source=choose_folder('Selecione a pasta oficial do 7-Zip x64 (7z.exe, 7z.dll, License.txt)')
    for name in ('7z.exe','7z.dll'):
        if not (source/name).is_file():raise FileNotFoundError('Falta '+name)
        if pe_machine(source/name)!=0x8664:raise ValueError('Use motor 7-Zip x64: '+name)
    license_file=next((p for p in source.iterdir() if p.is_file() and p.name.lower()=='license.txt'),None)
    if license_file is None:raise FileNotFoundError('License.txt do 7-Zip não encontrado. Use a distribuição oficial completa.')
    dest=HERE/'vendor/7zip';dest.mkdir(parents=True,exist_ok=True)
    for name in ('7z.exe','7z.dll'):copy_if_different(source/name,dest/name)
    licenses=HERE/'third_party_licenses/7zip';licenses.mkdir(parents=True,exist_ok=True)
    copy_if_different(license_file,licenses/'License.txt')
    for name in ('readme.txt','History.txt'):
        p=source/name
        if p.exists():copy_if_different(p,licenses/name)
    result=subprocess.run([str(dest/'7z.exe'),'i'],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    text=result.stdout.decode('utf-8',errors='replace')
    if result.returncode:raise RuntimeError('Motor 7-Zip copiado não executou corretamente.')
    if 'rar' not in text.lower():raise RuntimeError('O motor não anunciou suporte RAR. Não use 7za.exe.')
    with tempfile.TemporaryDirectory(prefix='central-build-test-') as d:
        base=Path(d);archive=base/'teste.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('teste.txt','Motor integrado funcionando.')
        target=base/'extraido'
        r=subprocess.run([str(dest/'7z.exe'),'x',str(archive),'-o'+str(target),'-y'],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
        if r.returncode or (target/'teste.txt').read_text()!='Motor integrado funcionando.':raise RuntimeError('Autoteste local do motor falhou.')
    header=next((line.strip() for line in text.splitlines() if line.strip().startswith('7-Zip')),'7-Zip — versão não extraída do cabeçalho')
    return header,{name:hashlib.sha256((dest/name).read_bytes()).hexdigest() for name in ('7z.exe','7z.dll')}

def collect_licenses():
    folder=HERE/'third_party_licenses';folder.mkdir(exist_ok=True)
    python_license=next((p for p in (Path(sys.base_prefix)/'LICENSE.txt',Path(sys.base_prefix)/'LICENSE') if p.is_file()),None)
    if python_license:copy_if_different(python_license,folder/'Python/LICENSE.txt')
    for package in ('Pillow','PyInstaller'):
        dist=importlib.metadata.distribution(package)
        for f in dist.files or []:
            if f.name.upper().startswith(('LICENSE','COPYING')):
                source=Path(dist.locate_file(f))
                if source.is_file():copy_if_different(source,folder/package/f.name)

def write_manifest():
    pairs={0:('false','unaware'),1:('true','system'),2:('true/pm','PerMonitorV2,PerMonitor')}
    legacy,modern=pairs.get(INITIAL_DPI,pairs[0])
    text=f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
 <assemblyIdentity type="win32" name="CentralInstalacao" version="0.6.0.0" processorArchitecture="amd64"/>
 <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3"><security><requestedPrivileges>
 <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
 </requestedPrivileges></security></trustInfo>
 <dependency><dependentAssembly><assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/></dependentAssembly></dependency>
 <application xmlns="urn:schemas-microsoft-com:asm.v3"><windowsSettings>
 <dpiAware xmlns="http://schemas.microsoft.com/SMI/2005/WindowsSettings">{legacy}</dpiAware>
 <dpiAwareness xmlns="http://schemas.microsoft.com/SMI/2016/WindowsSettings">{modern}</dpiAwareness>
 </windowsSettings></application>
</assembly>
'''
    (HERE/'central.manifest').write_text(text,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description='Build Windows x64 da Central com motor 7-Zip.')
    parser.add_argument('--profiles');parser.add_argument('--sevenzip');parser.add_argument('--mode',choices=['onefile','onedir'],default='onefile');parser.add_argument('--console',action='store_true')
    args=parser.parse_args()
    if sys.platform!='win32':raise RuntimeError('Gere este executável em Windows x64.')
    if struct.calcsize('P')!=8 or platform.machine().upper() not in ('AMD64','X86_64'):raise RuntimeError('Use Python x64 em Windows x64.')
    for file in ('central_instalacao_visual.py','perfis_instalacao.py','runtime_recursos.py'):ast.parse((HERE/file).read_text(encoding='utf-8'))
    for module in ('Pillow','PyInstaller'):importlib.metadata.version(module)
    count=prepare_profiles(args.profiles);version,hashes=prepare_engine(args.sevenzip);collect_licenses();write_manifest()
    info={'application':'0.6.0-rc1','python':platform.python_version(),'pyinstaller':importlib.metadata.version('PyInstaller'),'pillow':importlib.metadata.version('Pillow'),'profiles':count,'engine':version,'7zip_sha256':hashes,'dpi_awareness_of_build_python':INITIAL_DPI,'mode':args.mode}
    (HERE/'build_manifest.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    notice='''AVISOS DE TERCEIROS — CENTRAL DE INSTALAÇÃO

Este aplicativo inclui partes do programa 7-Zip: 7z.exe e 7z.dll, sem modificações.
7-Zip é de Igor Pavlov e usa GNU LGPL, com componentes BSD e restrição unRAR
conforme os textos originais em third_party_licenses/7zip/License.txt.
Fontes e informações oficiais: https://www.7-zip.org/ e https://www.7-zip.org/download.html
Consulte a versão exata registrada em build_manifest.json e preserve estes avisos
em toda distribuição. Não é permitido usar o código unRAR para recriar um compactador RAR.
A Central chama o motor como processo separado; não modifica os binários.

Python, Pillow e o bootloader PyInstaller são componentes independentes. Os textos
coletados das respectivas instalações acompanham third_party_licenses.
A licença do código da Central é separada e ainda deve ser definida pelo autor.
Instaladores de outros aplicativos e dados pessoais não fazem parte desta distribuição.

'''+version+'\n'
    (HERE/'THIRD_PARTY_NOTICES.txt').write_text(notice,encoding='utf-8')
    root=str(HERE)
    head=f'''from pathlib import Path
root=Path({root!r})
a=Analysis([str(root/'central_instalacao_visual.py')],pathex=[str(root)],
 binaries=[(str(root/'vendor/7zip/7z.exe'),'vendor/7zip'),(str(root/'vendor/7zip/7z.dll'),'vendor/7zip')],
 datas=[(str(root/'perfis_instalacao.json'),'.'),(str(root/'THIRD_PARTY_NOTICES.txt'),'.'),(str(root/'third_party_licenses'),'third_party_licenses'),(str(root/'build_manifest.json'),'.')],
 hiddenimports=['perfis_instalacao','runtime_recursos','PIL.ImageTk','PIL.PngImagePlugin','PIL.JpegImagePlugin'],hookspath=[],runtime_hooks=[],excludes=[])
pyz=PYZ(a.pure)
'''
    if args.mode=='onefile':tail=f"exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='CentralInstalacao',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console={args.console!r},manifest=str(root/'central.manifest'),uac_admin=False)\n"
    else:tail=f"exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='CentralInstalacao',debug=False,strip=False,upx=False,console={args.console!r},manifest=str(root/'central.manifest'),uac_admin=False)\ncoll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='CentralInstalacao')\n"
    spec=HERE/'CentralInstalacao.spec';spec.write_text(head+tail,encoding='utf-8')
    builddir=HERE/'build'/args.mode;dist=HERE/'dist'/args.mode
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--workpath',str(builddir),'--distpath',str(dist),str(spec)]
    print('Perfis:',count,'| Motor:',version,'| Modo:',args.mode)
    subprocess.run(command,cwd=str(HERE),check=True)
    exe=dist/('CentralInstalacao.exe' if args.mode=='onefile' else 'CentralInstalacao/CentralInstalacao.exe')
    if not exe.is_file():raise FileNotFoundError('O executável esperado não foi gerado.')
    legal=dist/'Licencas';shutil.copytree(HERE/'third_party_licenses',legal,dirs_exist_ok=True)
    shutil.copy2(HERE/'THIRD_PARTY_NOTICES.txt',dist/'THIRD_PARTY_NOTICES.txt');shutil.copy2(HERE/'build_manifest.json',dist/'build_manifest.json')
    (dist/'COMO_TESTAR.txt').write_text('Execute CentralInstalacao.exe. Na VM limpa não instale Python, Pillow ou 7-Zip.\nAutoteste: execute o EXE com --self-test. Relatório em %LOCALAPPDATA%/CentralInstalacaoVisual/autoteste_distribuicao.json.\nTeste ZIP/7z/RAR reais, senha, instalações e reinício por escala. Distribua o ZIP com os avisos/licenças acompanhantes.\n',encoding='utf-8')
    release=HERE/('CentralInstalacao-0.6.0-rc1-'+args.mode+'.zip')
    with zipfile.ZipFile(release,'w',zipfile.ZIP_DEFLATED) as z:
        for p in dist.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(dist))
    with zipfile.ZipFile(release) as z:
        if z.testzip() is not None:raise RuntimeError('ZIP final não passou na verificação.')
    print('\nExecutável:',exe,'\nPacote de distribuição:',release,'\nBuild concluído. Teste em VM limpa antes de publicar.')

if __name__=='__main__':
    try:main()
    except Exception as exc:print('\nERRO:',exc,file=sys.stderr);raise SystemExit(1)
