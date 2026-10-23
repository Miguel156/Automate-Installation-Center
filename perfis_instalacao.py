"""Perfis e configuração simplificada. Não executa o instalador durante identificação."""
import os,sys,json,re,queue,threading,subprocess,datetime,uuid
from pathlib import Path
from runtime_recursos import resource_path, load_profile_records, run_process
import tkinter as tk
from tkinter import ttk,filedialog,messagebox

LIB=resource_path('perfis_instalacao.json')
WARNING='ATENÇÃO o programa que você colocou possui argumentos de instalação silenciosos mas não pode ser verificado, quer adicionar os argumentos para esse programa?'

def load_profiles():
    data=load_profile_records()
    if not isinstance(data,list):raise ValueError('A biblioteca precisa ser uma lista JSON.')
    ids=set()
    for p in data:
        if not isinstance(p,dict):raise ValueError('Perfil inválido.')
        for key in ('id','name','filename_regex','product_regex','publisher_regex','source','note'):
            if not isinstance(p.get(key),str):raise ValueError('Campo inválido: '+key)
        if p['id'] in ids:raise ValueError('ID duplicado: '+p['id'])
        ids.add(p['id'])
        for key in ('filename_regex','product_regex','publisher_regex'):re.compile(p[key],re.I)
        if p.get('arguments') is not None and not isinstance(p['arguments'],str):raise ValueError('Argumentos inválidos.')
    return data

def metadata(path):
    env=os.environ.copy();env['CENTRAL_INSPECT_FILE']=str(path)
    script=r"""$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$v=[System.Diagnostics.FileVersionInfo]::GetVersionInfo($env:CENTRAL_INSPECT_FILE)
$status='Unavailable';$signer='';$errorText=''
try {
 $s=Get-AuthenticodeSignature -LiteralPath $env:CENTRAL_INSPECT_FILE
 $status=[string]$s.Status
 if($s.SignerCertificate){$signer=$s.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName,$false)}
} catch {$errorText=$_.Exception.Message}
[pscustomobject]@{product=$v.ProductName;description=$v.FileDescription;company=$v.CompanyName;signature=$status;signer=$signer;error=$errorText} | ConvertTo-Json -Compress
"""
    import base64
    encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    ps=Path(os.environ.get('SystemRoot','C:/Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
        r=run_process([str(ps),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],env=env,capture_output=True,timeout=22,creationflags=flags)
        if r.returncode:raise ValueError('Falha ao consultar metadados/assinatura.')
        data=json.loads(r.stdout.decode('utf-8-sig',errors='replace'))
        return {k:(data.get(k) or '') for k in ('product','description','company','signature','signer','error')}
    except Exception as exc:return dict(product='',description='',company='',signature='Unavailable',signer='',error=str(exc))

def evidence(p,path,m):
    filename=bool(re.fullmatch(p['filename_regex'],Path(path).name,re.I))
    text=' '.join(str(m.get(k) or '') for k in ('product','description'))
    product=bool(re.search(p['product_regex'],text,re.I))
    company=str(m.get('company') or '')
    publisher=bool(re.search(p['publisher_regex'],company,re.I)) if company else False
    meta=product and publisher
    sig=m.get('signature')=='Valid' and bool(re.search(p['publisher_regex'],str(m.get('signer') or ''),re.I))
    conflicts=[]
    if filename and company and not publisher:conflicts.append('Fabricante dos metadados não corresponde ao perfil.')
    status=m.get('signature') or 'Unavailable'
    if status not in ('Valid','NotSigned','Unavailable','UnknownError'):
        conflicts.append('A assinatura não foi validada: '+status)
    if status=='Valid' and not sig:conflicts.append('Assinatura válida, mas o assinante não corresponde ao perfil.')
    return dict(filename=filename,metadata=meta,signature=sig,score=sum((filename,meta,sig)),conflicts=conflicts)

def candidates(profiles,path,m):
    pairs=[(p,evidence(p,path,m)) for p in profiles]
    byname=[x for x in pairs if x[1]['filename']]
    if byname:return byname
    return [x for x in pairs if x[1]['metadata']]

def inspect_dialog(app,path,g):
    previous=app.grab_current()
    w=tk.Toplevel(app);w.title('Identificando instalador');w.configure(bg=g['BG']);w.transient(app);w.grab_set()
    ttk.Label(w,text='Consultando metadados e assinatura, sem executar o instalador…',wraplength=580).pack(padx=22,pady=(22,10))
    ttk.Label(w,text=Path(path).name,wraplength=580).pack(padx=22,pady=8)
    result={};q=queue.Queue()
    def cancel():result['cancelled']=True;w.destroy()
    app.button(w,'Cancelar verificação',cancel).pack(pady=(10,20));w.protocol('WM_DELETE_WINDOW',cancel)
    def work():q.put(metadata(path))
    threading.Thread(target=work,daemon=True).start()
    def poll():
        if not w.winfo_exists():return
        try:result.update(q.get_nowait());w.destroy()
        except queue.Empty:w.after(100,poll)
    w.after(100,poll);app.wait_window(w)
    if previous is not None and previous.winfo_exists():previous.grab_set()
    return result

def choose_candidate(app,pairs,g):
    if len(pairs)==1:return pairs[0]
    previous=app.grab_current()
    w=tk.Toplevel(app);w.title('Identificação ambígua');w.configure(bg=g['BG']);w.transient(app);w.grab_set()
    ttk.Label(w,text='Mais de um perfil é possível. Escolha um para revisar ou continue manualmente.',wraplength=580).pack(padx=20,pady=15)
    var=tk.StringVar(value='Manual — não aplicar perfil')
    choices=['Manual — não aplicar perfil']+[p['name'] for p,e in pairs]
    ttk.Combobox(w,textvariable=var,values=choices,state='readonly',width=52).pack(padx=20,pady=10)
    result=[]
    def done():
        if var.get() in choices[1:]:result.append(pairs[choices.index(var.get())-1])
        w.destroy()
    app.button(w,'Continuar',done).pack(pady=15);app.wait_window(w)
    if previous is not None and previous.winfo_exists():previous.grab_set()
    return result[0] if result else None

def suggest(app,item,g):
    try:profiles=load_profiles()
    except Exception as exc:messagebox.showerror('Biblioteca de perfis',str(exc),parent=app);return 'manual'
    m=inspect_dialog(app,item['source'],g)
    if m.get('cancelled'):return 'cancel'
    found=candidates(profiles,item['source'],m)
    if not found:
        item['profile_note']='Nenhum perfil compatível encontrado. Argumentos manuais.'
        return 'manual'
    ambiguous=len(found)>1
    chosen=choose_candidate(app,found,g)
    if chosen is None:return 'manual'
    p,e=chosen
    item['profile_id']=p['id'];item['profile_name']=p['name'];item['profile_source']=p['source']
    item['profile_evidence']={**e,'signature_status':m.get('signature'),'signer':m.get('signer'),'product':m.get('product'),'company':m.get('company')}
    item['profile_note']=p['note']
    if p['arguments'] is None:
        messagebox.showinfo('Perfil sem comando confirmado',p['name']+'\n\n'+p['note']+'\n\nO programa pode ser cadastrado, mas os argumentos ficam manuais.',parent=app)
        return 'manual'
    details='\n\nPerfil: '+p['name']+'\nArquivo: '+Path(item['source']).name+'\nArgumentos: '+p['arguments']
    details+='\n\nNome: '+('compatível' if e['filename'] else 'não confirmado')
    details+='\nMetadados: '+('compatíveis' if e['metadata'] else 'não confirmados')
    details+='\nAssinatura: '+str(m.get('signature') or 'indisponível')+' — '+str(m.get('signer') or 'sem assinante confirmado')
    if e['conflicts']:details+='\n\nDivergências:\n'+'\n'.join(e['conflicts'])
    verified=e['score']==3 and not e['conflicts'] and not ambiguous
    if not verified:
        details+='\n\nOs argumentos pertencem ao perfil sugerido; a compatibilidade com este arquivo não foi confirmada.\nSim: adicionar argumentos. Não: continuar manualmente. Cancelar: cancelar esta ação.\nIsso não executa o arquivo nem comprova sua segurança.'
        decision=messagebox.askyesnocancel('Confirmar argumentos sugeridos',WARNING+details,parent=app)
        if decision is None:return 'cancel'
        if not decision:return 'manual'
    item['args']=p['arguments'];item['profile_applied']=True
    item['profile_note']=('3/3 verificações compatíveis. ' if verified else 'Sugestão aceita pelo usuário. ')+p['note']
    return 'applied'

def integrate(App,g):
    if getattr(App,'_profiles_integrated',False):return
    original_edit=App.edit;original_watch=getattr(App,'_watch_scale_changes',None)
    def editor(app,new=False):
        if app.busy:return False
        item=app.selected()
        if item is None:return False
        if Path(item['source']).suffix.lower() not in ('.exe','.msi'):
            before=set(app.winfo_children());saved=[False];save=app.save
            def track_save():save();saved[0]=True
            app.save=track_save
            try:
                original_edit(app)
                windows=[w for w in app.winfo_children() if w not in before and isinstance(w,tk.Toplevel)]
                if windows:app.wait_window(windows[-1])
            finally:app.save=save
            return saved[0]
        msi=Path(item['source']).suffix.lower()=='.msi'
        w=tk.Toplevel(app);w.title('Configurar instalador — '+item['name']);w.configure(bg=g['BG']);w.transient(app);w.grab_set()
        width=min(930,max(600,app.winfo_screenwidth()-60));height=min(670,max(460,app.winfo_screenheight()-100));w.geometry(f'{width}x{height}')
        ttk.Label(w,text='Instalador MSI' if msi else 'Instalador EXE',font=('Segoe UI',17,'bold')).pack(anchor='w',padx=20,pady=14)
        footer=tk.Frame(w,bg=g['BG']);footer.pack(side='bottom',fill='x',padx=20,pady=14)
        holder=tk.Frame(w,bg=g['BG']);holder.pack(fill='both',expand=True,padx=14)
        canvas=tk.Canvas(holder,bg=g['BG'],highlightthickness=0);scroll=ttk.Scrollbar(holder,command=canvas.yview);canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        body=tk.Frame(canvas,bg=g['BG']);body.columnconfigure(1,weight=1);win=canvas.create_window((0,0),window=body,anchor='nw')
        body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        def wheel(e):canvas.yview_scroll(-int(e.delta/120),'units');return 'break'
        w.bind('<MouseWheel>',wheel)
        variables={k:tk.StringVar(value=item.get(k,'')) for k in ('name','description','icon','args')}
        def field(label,key,row):
            ttk.Label(body,text=label).grid(row=row,column=0,padx=8,pady=9,sticky='w')
            ttk.Entry(body,textvariable=variables[key]).grid(row=row,column=1,padx=8,sticky='ew')
        field('Nome','name',0);field('Descrição (opcional)','description',1);field('Ícone PNG/JPG (opcional)','icon',2)
        def icon_pick():
            if g.get('Image') is None:return messagebox.showinfo('Imagens','Instale Pillow pelo Preparar_imagens.bat e reabra o programa.',parent=w)
            path=filedialog.askopenfilename(parent=w,filetypes=[('Imagens','*.png *.jpg *.jpeg')])
            if path:variables['icon'].set(path)
        app.button(body,'Escolher',icon_pick).grid(row=2,column=2,padx=5)
        app.button(body,'Limpar ícone',lambda:variables['icon'].set('')).grid(row=3,column=1,sticky='w',padx=8,pady=4)
        ttk.Label(body,text='Arquivo de origem').grid(row=4,column=0,padx=8,pady=9,sticky='w')
        ttk.Label(body,text=item['source'],wraplength=max(320,width-280)).grid(row=4,column=1,columnspan=2,padx=8,sticky='w')
        field('Propriedades MSI adicionais' if msi else 'Argumentos de instalação', 'args',5)
        silent=tk.BooleanVar(value=item.get('silent',True if msi else False))
        if msi:ttk.Checkbutton(body,text='Instalação silenciosa (desmarcada = modo passivo)',variable=silent).grid(row=6,column=0,columnspan=3,padx=8,pady=9,sticky='w')
        profile_updates={}
        report=tk.StringVar(value=('MSI: modo silencioso padronizado; sem perfil EXE.' if msi else item.get('profile_name','Manual')+'\n'+item.get('profile_note','Argumentos não configurados automaticamente.')))
        ttk.Label(body,textvariable=report,wraplength=max(440,width-70)).grid(row=7,column=0,columnspan=3,padx=8,pady=10,sticky='w')
        if not msi:
            def recheck():
                if variables['args'].get().strip() and not messagebox.askyesno('Reavaliar','Se aceitar uma nova sugestão, os argumentos atuais serão substituídos. Continuar?',parent=w):return
                draft=dict(item);outcome=suggest(app,draft,g)
                if outcome=='applied':
                    variables['args'].set(draft['args'])
                    for k in ('profile_id','profile_name','profile_source','profile_evidence','profile_note','profile_applied'):
                        if k in draft:profile_updates[k]=draft[k]
                    report.set(draft.get('profile_name','Manual')+'\n'+draft.get('profile_note',''))
            app.button(body,'Identificar / sugerir argumentos',recheck).grid(row=8,column=0,columnspan=3,padx=8,pady=8,sticky='w')
        note='MSI: o aplicativo já acrescenta /quiet ou /passive, /norestart e log. Não repita essas opções.' if msi else 'Os argumentos variam por instalador. Campo vazio abre o assistente normal.\nIdentificação não é uma verificação antivírus; o arquivo só executa na fila confirmada.'
        ttk.Label(body,text=note,wraplength=max(440,width-70)).grid(row=9,column=0,columnspan=3,padx=8,pady=14,sticky='w')
        saved=[False]
        def accept():
            try:
                data={k:v.get().strip() for k,v in variables.items()}
                if not data['name'] or not Path(item['source']).is_file():raise ValueError('Confira o nome e o arquivo de origem.')
                icon=data['icon']
                if icon and icon!=item.get('icon',''):
                    Image=g.get('Image');ImageOps=g.get('ImageOps')
                    if Image is None:raise ValueError('Instale Pillow para usar ícones.')
                    with Image.open(icon) as im:
                        if im.format not in ('PNG','JPEG'):raise ValueError('Escolha uma imagem PNG/JPG.')
                        image=ImageOps.exif_transpose(im).convert('RGBA');image.thumbnail((256,256),Image.Resampling.LANCZOS)
                        target=g['ICONS']/(uuid.uuid4().hex+'.png');image.save(target);data['icon']=str(target)
                if data['args']!=item.get('args',''):data['arguments_edited']=True
                item.update(profile_updates)
                item.update(data,action='Instalar',silent=silent.get() if msi else False,status='Pronto')
                app.save();app.refresh();saved[0]=True;w.destroy()
            except Exception as exc:messagebox.showerror('Configuração',str(exc),parent=w)
        app.button(footer,'Cancelar',w.destroy).pack(side='left');app.button(footer,'Salvar e continuar' if new else 'Salvar configuração',accept).pack(side='right')
        if hasattr(app,'_scale_widget_spacing'):app._scale_widget_spacing(body)
        app.wait_window(w);return saved[0]
    def add(app):
        if app.busy or getattr(app,'_profiles_adding',False):return
        files=filedialog.askopenfilenames(filetypes=[('Pacotes','*.exe *.msi *.zip *.7z *.rar *.tar *.gz *.bz2 *.xz'),('Todos','*.*')])
        if not files:return
        app._profiles_adding=True
        try:
            for pos,filename in enumerate(files,1):
                p=Path(filename);ext=p.suffix.lower()
                if ext not in g['ARCHIVES']+('.exe','.msi'):
                    messagebox.showwarning('Formato','Formato não suportado: '+p.name,parent=app);continue
                if ext=='.msi' and not messagebox.askyesno('Confirmar instalador MSI','Arquivo: '+p.name+'\n\nO modo silencioso ficará ativo por padrão. Quando executado, o MSI poderá modificar o sistema.\nVocê reconhece a origem e deseja adicionar este instalador?\n\nAdicionar não inicia a instalação.',parent=app):continue
                item=dict(name=p.stem,source=str(p),selected=True,action='Extrair' if ext in g['ARCHIVES'] else 'Instalar',dest=str(app.base/p.stem),inner='',args='',silent=ext=='.msi',status='Pronto',portable='',desktop=False,startmenu=False,password='',description='',icon='')
                if ext=='.exe':
                    outcome=suggest(app,item,g)
                    if outcome=='cancel':
                        if pos<len(files) and messagebox.askyesno('Restantes','Cancelar também os arquivos restantes?',parent=app):break
                        continue
                app.items.append(item);app.active=len(app.items)-1;app.refresh()
                app.info.set(f'Configurando arquivo {pos} de {len(files)}: {p.name}')
                accepted=editor(app,new=True)
                if not accepted:
                    app.items.pop(app.active);app.active=None;app.refresh()
                    if pos<len(files) and messagebox.askyesno('Cadastro cancelado','Ignorar este arquivo e cancelar também os restantes?',parent=app):break
            app.save();app.info.set('Cadastro encerrado. Nenhum instalador foi executado.')
        finally:app._profiles_adding=False
    def edit(app):return editor(app,new=False)
    App.add=add;App.edit=edit
    if original_watch:
        def watch(app):
            if getattr(app,'_profiles_adding',False):app.after(1500,app._watch_scale_changes);return
            return original_watch(app)
        App._watch_scale_changes=watch
    App._profiles_integrated=True
