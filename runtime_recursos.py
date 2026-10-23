"""Recursos e subprocessos da distribuição Windows."""
import os,sys,json,threading,subprocess,ctypes,tempfile,zipfile,hashlib
from pathlib import Path

BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'CentralInstalacaoVisual'
_DLL_LOCK=threading.RLock()

def resource_path(name):return BASE/name

def load_profile_records():
    default=json.loads(resource_path('perfis_instalacao.json').read_text(encoding='utf-8'))
    if not isinstance(default,list):raise ValueError('Biblioteca de perfis inválida.')
    custom=DATA/'perfis_instalacao_personalizados.json'
    if not custom.exists():return default
    updates=json.loads(custom.read_text(encoding='utf-8'))
    if not isinstance(updates,list):raise ValueError('Perfis personalizados precisam ser uma lista JSON.')
    merged={p['id']:dict(p) for p in default}
    for p in updates:
        if not isinstance(p,dict) or not isinstance(p.get('id'),str):raise ValueError('Perfil personalizado sem ID válido.')
        merged[p['id']]={**merged.get(p['id'],{}),**p}
    return list(merged.values())

def find_7zip():
    folder=resource_path('vendor/7zip')
    exe=folder/'7z.exe';dll=folder/'7z.dll'
    if exe.is_file() and dll.is_file():return str(exe)
    if getattr(sys,'frozen',False):raise FileNotFoundError('O motor 7-Zip integrado está ausente ou incompleto. Reextraia a distribuição ou gere novamente o executável.')
    import shutil
    choices=[shutil.which('7z')]
    for key in ('ProgramFiles','ProgramFiles(x86)'):choices.append(str(Path(os.environ.get(key,'C:/Program Files'))/'7-Zip/7z.exe'))
    for p in choices:
        if p and Path(p).is_file():return p
    raise FileNotFoundError('Prepare vendor/7zip com 7z.exe e 7z.dll, ou instale o 7-Zip para executar pelo Python.')

def spawn_process(*args,**kwargs):
    # SetDllDirectory afeta os processos filhos no Windows/PyInstaller.
    if sys.platform!='win32' or not getattr(sys,'frozen',False):return subprocess.Popen(*args,**kwargs)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetDllDirectoryW.argtypes=[ctypes.c_uint32,ctypes.c_wchar_p];kernel.GetDllDirectoryW.restype=ctypes.c_uint32
    kernel.SetDllDirectoryW.argtypes=[ctypes.c_wchar_p];kernel.SetDllDirectoryW.restype=ctypes.c_int
    with _DLL_LOCK:
        size=kernel.GetDllDirectoryW(0,None)
        buffer=ctypes.create_unicode_buffer(size+1)
        kernel.GetDllDirectoryW(len(buffer),buffer)
        previous=buffer.value or None
        if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
        try:return subprocess.Popen(*args,**kwargs)
        finally:kernel.SetDllDirectoryW(previous)

def run_process(*args,input=None,capture_output=False,timeout=None,check=False,**kwargs):
    if input is not None:
        if kwargs.get('stdin') is not None:raise ValueError('stdin e input não podem ser usados juntos.')
        kwargs['stdin']=subprocess.PIPE
    if capture_output:
        if kwargs.get('stdout') is not None or kwargs.get('stderr') is not None:raise ValueError('capture_output não pode ser combinado com stdout/stderr.')
        kwargs['stdout']=subprocess.PIPE;kwargs['stderr']=subprocess.PIPE
    with spawn_process(*args,**kwargs) as process:
        try:stdout,stderr=process.communicate(input,timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            process.kill();stdout,stderr=process.communicate()
            exc.output=stdout;exc.stderr=stderr;raise
        except BaseException:process.kill();process.wait();raise
        result=process.poll()
        if check and result:raise subprocess.CalledProcessError(result,process.args,output=stdout,stderr=stderr)
    return subprocess.CompletedProcess(process.args,result,stdout,stderr)

def open_licenses():
    path=resource_path('THIRD_PARTY_NOTICES.txt')
    if not path.is_file():raise FileNotFoundError('Avisos de terceiros não encontrados.')
    # Copiar para localização persistente: o temporário do onefile some ao sair.
    DATA.mkdir(parents=True,exist_ok=True)
    target=DATA/'LICENCAS_DA_DISTRIBUICAO.txt'
    text=path.read_text(encoding='utf-8')
    folder=resource_path('third_party_licenses')
    for p in sorted(folder.rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.txt','.md',''):
            text+='\n\n===== '+str(p.relative_to(folder))+' =====\n'+p.read_text(encoding='utf-8',errors='replace')
    target.write_text(text,encoding='utf-8');os.startfile(target)

def self_test():
    DATA.mkdir(parents=True,exist_ok=True)
    report=DATA/'autoteste_distribuicao.json'
    details={'frozen':bool(getattr(sys,'frozen',False)),'executable':sys.executable}
    try:
        from PIL import Image, __version__ as pillow_version
        import tkinter
        import perfis_instalacao
        details['profiles']=len(perfis_instalacao.load_profiles());details['tk']=tkinter.TkVersion;details['pillow']=pillow_version
        exe=find_7zip();details['7zip']=exe
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        with tempfile.TemporaryDirectory(prefix='central-teste-') as d:
            base=Path(d);payload=base/'arquivo-com-acentos.txt';payload.write_text('Teste da Central: extração correta.',encoding='utf-8')
            archive=base/'protegido.zip'
            r=run_process([exe,'a','-tzip',str(archive),str(payload),'-pcentral-autoteste','-y'],capture_output=True,creationflags=flags,timeout=30)
            if r.returncode:raise RuntimeError('Falha criando ZIP de teste: '+str(r.returncode))
            dest=base/'extraido'
            r=run_process([exe,'x',str(archive),'-o'+str(dest),'-pcentral-autoteste','-y'],capture_output=True,creationflags=flags,timeout=30)
            if r.returncode or (dest/payload.name).read_bytes()!=payload.read_bytes():raise RuntimeError('Falha na extração integrada com senha.')
            details['zip_password_extraction']='OK'
        manifest=resource_path('build_manifest.json')
        if manifest.exists():
            data=json.loads(manifest.read_text(encoding='utf-8'))
            for name,digest in data.get('7zip_sha256',{}).items():
                actual=hashlib.sha256(resource_path('vendor/7zip') .joinpath(name).read_bytes()).hexdigest()
                if actual!=digest:raise RuntimeError('Hash divergente do motor: '+name)
            details['7zip_hashes']='OK'
        details['status']='OK';return_code=0
    except Exception as exc:details['status']='ERRO';details['error']=str(exc);return_code=1
    report.write_text(json.dumps(details,ensure_ascii=False,indent=2),encoding='utf-8')
    if sys.stdout is not None:print(json.dumps(details,ensure_ascii=False,indent=2))
    else:
        from tkinter import messagebox
        messagebox.showinfo('Autoteste da distribuição',details['status']+'\nRelatório: '+str(report))
    return return_code
