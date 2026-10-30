#!/usr/bin/env python3
"""Wine Game Library 2.0: leve, personalizável, para Linux + Wine."""
import json, os, shlex, shutil, subprocess, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, colorchooser, ttk

APP = Path.home()/'.config'/'wine-game-library'
GAMES = APP/'games.json'
PREFS = APP/'settings.json'
DEFAULTS = {'accent':'#657cf2','bg':'#10131c','panel':'#191e2b','maximized':True}

class Launcher:
    def __init__(self, root):
        self.root=root; APP.mkdir(parents=True,exist_ok=True)
        self.prefs=self.read(PREFS,DEFAULTS.copy()); self.games=self.read(GAMES,[])
        self.selected=None; self.photo=None; self.query=tk.StringVar(); self.status=tk.StringVar(value='Pronto para jogar')
        self.root.title('Wine Game Library'); self.root.geometry('1120x740'); self.root.minsize(900,600); self.root.configure(bg=self.prefs['bg'])
        if self.prefs.get('maximized'):
            try: self.root.state('zoomed')
            except tk.TclError: pass
        self.style(); self.ui(); self.refresh()

    def read(self,p,default):
        try: return json.loads(p.read_text(encoding='utf-8'))
        except (OSError,json.JSONDecodeError): return default
    def save(self,p,data):
        APP.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    def style(self):
        s=ttk.Style(); s.theme_use('clam'); p=self.prefs['panel']; bg=self.prefs['bg']
        s.configure('Treeview',background=p,foreground='#e8ecf5',fieldbackground=p,rowheight=36,borderwidth=0,font=('DejaVu Sans',10))
        s.configure('Treeview.Heading',background='#252c3d',foreground='#cdd6f4',font=('DejaVu Sans',9,'bold'),relief='flat')
        s.map('Treeview',background=[('selected',self.prefs['accent'])],foreground=[('selected','#ffffff')])
        s.configure('Vertical.TScrollbar',background='#252c3d',troughcolor=bg,bordercolor=bg,arrowcolor='#cdd6f4')
    def btn(self, parent, text, fn, bg=None, fg='#f1f3fb', **kw):
        options = {
            'text': text,
            'command': fn,
            'bg': bg or '#252c3d',
            'fg': fg,
            'activebackground': bg or '#39435c',
            'activeforeground': fg,
            'relief': 'flat',
            'bd': 0,
            'padx': 12,
            'pady': 8,
            'cursor': 'hand2',
            'font': ('DejaVu Sans', 9),
        }
        options.update(kw)
        return tk.Button(parent, **options)
    def ui(self):
        bg=self.prefs['bg']; panel=self.prefs['panel']; accent=self.prefs['accent']
        h=tk.Frame(self.root,bg=bg); h.pack(fill='x',padx=24,pady=(20,12))
        tk.Label(h,text='WINE GAME LIBRARY',bg=bg,fg='#f0f3ff',font=('DejaVu Sans',21,'bold')).pack(anchor='w')
        tk.Label(h,text='Sua biblioteca de jogos do Windows no Linux',bg=bg,fg='#9aa6c2',font=('DejaVu Sans',10)).pack(anchor='w',pady=(4,0))
        bar=tk.Frame(self.root,bg=bg); bar.pack(fill='x',padx=24,pady=(2,12))
        self.btn(bar,'+ Adicionar jogo',self.add,accent,'#fff').pack(side='left')
        self.btn(bar,'Configurações do jogo',self.edit).pack(side='left',padx=(8,0))
        self.btn(bar,'− Remover',self.remove).pack(side='left',padx=(8,0))
        self.btn(bar,'Personalizar',self.preferences).pack(side='left',padx=(8,0))
        sr=tk.Frame(bar,bg=bg); sr.pack(side='right'); tk.Label(sr,text='BUSCAR',bg=bg,fg='#8996b4',font=('DejaVu Sans',8,'bold')).pack(anchor='w')
        ent=tk.Entry(sr,textvariable=self.query,width=22,bg=panel,fg='#e8ecf5',insertbackground='white',relief='flat',font=('DejaVu Sans',10)); ent.pack(ipady=7,pady=(3,0)); ent.bind('<KeyRelease>',lambda e:self.refresh())
        body=tk.Frame(self.root,bg=bg); body.pack(fill='both',expand=True,padx=24,pady=(0,12))
        left=tk.Frame(body,bg=panel,highlightbackground='#2a3245',highlightthickness=1); left.pack(side='left',fill='both',expand=True)
        tk.Label(left,text='  BIBLIOTECA',bg=panel,fg='#cdd6f4',font=('DejaVu Sans',9,'bold'),anchor='w').pack(fill='x',pady=(9,5))
        self.tree=ttk.Treeview(left,columns=('name','fps','exe'),show='headings',selectmode='browse')
        for col,title in [('name','JOGO'),('fps','FPS'),('exe','EXECUTÁVEL')]: self.tree.heading(col,text=title)
        self.tree.column('name',width=220,minwidth=140); self.tree.column('fps',width=60,minwidth=50,anchor='center'); self.tree.column('exe',width=300,minwidth=130)
        sc=ttk.Scrollbar(left,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=sc.set); self.tree.pack(side='left',fill='both',expand=True,padx=(8,0),pady=(0,8)); sc.pack(side='right',fill='y',padx=(0,8),pady=(0,8))
        self.tree.bind('<<TreeviewSelect>>',self.on_select); self.tree.bind('<Double-1>',lambda e:self.launch())
        right=tk.Frame(body,bg=panel,width=285,highlightbackground='#2a3245',highlightthickness=1); right.pack(side='right',fill='y',padx=(12,0)); right.pack_propagate(False)
        tk.Label(right,text='DETALHES DO JOGO',bg=panel,fg='#cdd6f4',font=('DejaVu Sans',9,'bold')).pack(anchor='w',padx=14,pady=(12,8))
        self.cover=tk.Label(right,text='Sem capa\n\nUse “Escolher capa”',bg='#111520',fg='#7f8aa6',font=('DejaVu Sans',9),height=11); self.cover.pack(fill='x',padx=14,pady=(0,10))
        self.dname=tk.Label(right,text='Nenhum jogo selecionado',bg=panel,fg='#f0f3ff',font=('DejaVu Sans',11,'bold'),wraplength=245,justify='left'); self.dname.pack(anchor='w',padx=14,pady=(0,6))
        self.dpath=tk.Label(right,text='',bg=panel,fg='#9aa6c2',font=('DejaVu Sans',8),wraplength=245,justify='left'); self.dpath.pack(anchor='w',padx=14,pady=(0,8))
        self.dinfo=tk.Label(right,text='',bg=panel,fg='#9aa6c2',font=('DejaVu Sans',9),justify='left',wraplength=245); self.dinfo.pack(anchor='w',padx=14,pady=(0,10))
        self.btn(right,'Escolher capa',self.choose_cover).pack(fill='x',padx=14,pady=(0,8)); self.btn(right,'Abrir pasta do jogo',self.open_folder).pack(fill='x',padx=14)
        foot=tk.Frame(self.root,bg=bg); foot.pack(fill='x',padx=24,pady=(0,14)); tk.Label(foot,textvariable=self.status,bg=bg,fg='#9aa6c2',font=('DejaVu Sans',9)).pack(side='left')
        self.btn(foot,'▶  JOGAR',self.launch,'#78dba9','#101820',font=('DejaVu Sans',11,'bold'),padx=28,pady=11).pack(side='right')
        tk.Label(self.root,text='Dica: dê dois cliques para iniciar • Delete remove o jogo da biblioteca',bg=panel,fg='#8390ad',anchor='w',padx=24,pady=6,font=('DejaVu Sans',8)).pack(fill='x',side='bottom')
        self.root.bind('<Delete>',lambda e:self.remove())
    def idx(self):
        try: return int(self.tree.selection()[0])
        except (IndexError,ValueError): return None
    def refresh(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        q=self.query.get().lower().strip()
        for i,g in enumerate(self.games):
            if q and q not in g.get('name','').lower() and q not in g.get('path','').lower(): continue
            self.tree.insert('','end',iid=str(i),values=(g.get('name','Jogo'),'Ligado' if g.get('fps') else '—',Path(g.get('path','')).name))
        if self.selected is not None and self.selected<len(self.games) and self.tree.exists(str(self.selected)):
            self.tree.selection_set(str(self.selected)); self.on_select()
        self.status.set(f'{len(self.games)} jogo(s) na biblioteca')
    def on_select(self,event=None):
        i=self.idx()
        if i is None or i>=len(self.games): return
        self.selected=i; g=self.games[i]; self.dname.config(text=g.get('name','Jogo')); self.dpath.config(text=g.get('path',''))
        self.dinfo.config(text=f"Prefixo: {g.get('prefix') or 'Padrão do Wine'}\nFPS: {'MangoHud' if g.get('fps') else 'desligado'}\nArgumentos: {g.get('args') or 'nenhum'}")
        cover=g.get('cover','')
        if not cover or not Path(cover).is_file(): self.cover.config(image='',text='Sem capa\n\nUse “Escolher capa”'); self.photo=None; return
        try:
            try:
                from PIL import Image,ImageTk
                im=Image.open(cover); im.thumbnail((245,230)); self.photo=ImageTk.PhotoImage(im)
            except ImportError:
                self.photo=tk.PhotoImage(file=cover); factor=max(1,self.photo.width()//245,self.photo.height()//230)
                if factor>1: self.photo=self.photo.subsample(factor,factor)
            self.cover.config(image=self.photo,text='')
        except Exception: self.cover.config(image='',text='Formato não suportado. Instale python3-pil.'); self.photo=None
    def add(self):
        p=filedialog.askopenfilename(title='Escolha o executável do jogo',filetypes=[('Executáveis Windows','*.exe'),('Todos os arquivos','*.*')])
        if not p:return
        p=str(Path(p).resolve())
        if any(g.get('path')==p for g in self.games): messagebox.showinfo('Já adicionado','Esse executável já está na biblioteca.'); return
        name=simpledialog.askstring('Nome do jogo','Como o jogo deve aparecer?',initialvalue=Path(p).stem)
        if name is None:return
        self.games.append({'name':name.strip() or Path(p).stem,'path':p,'args':'','prefix':'','env':'','fps':False,'cover':''}); self.games.sort(key=lambda x:x.get('name','').casefold()); self.save(GAMES,self.games); self.refresh()
        for i,g in enumerate(self.games):
            if g['path']==p: self.selected=i; self.tree.selection_set(str(i)); self.tree.see(str(i)); self.on_select(); break
        self.status.set(f'Adicionado: {name}')
    def remove(self):
        i=self.idx()
        if i is None: messagebox.showinfo('Selecione um jogo','Escolha um jogo na lista primeiro.'); return
        if not messagebox.askyesno('Remover jogo',f"Remover “{self.games[i]['name']}” da biblioteca?\n\nOs arquivos do jogo não serão apagados."):return
        self.games.pop(i); self.selected=None; self.save(GAMES,self.games); self.refresh(); self.dname.config(text='Nenhum jogo selecionado'); self.dpath.config(text=''); self.dinfo.config(text=''); self.cover.config(image='',text='Sem capa'); self.status.set('Jogo removido da biblioteca')
    def choose_cover(self):
        i=self.idx()
        if i is None: messagebox.showinfo('Selecione um jogo','Escolha um jogo primeiro.'); return
        p=filedialog.askopenfilename(title='Escolher capa',filetypes=[('Imagens','*.png *.gif *.jpg *.jpeg *.webp *.bmp'),('Todos os arquivos','*.*')])
        if p: self.games[i]['cover']=str(Path(p).resolve()); self.save(GAMES,self.games); self.on_select(); self.status.set('Capa atualizada')
    def edit(self):
        i=self.idx()
        if i is None: messagebox.showinfo('Selecione um jogo','Escolha um jogo primeiro.'); return
        g=self.games[i]; w=tk.Toplevel(self.root); w.title('Configurações do jogo'); w.configure(bg=self.prefs['bg']); w.geometry('610x590'); w.minsize(540,520); w.transient(self.root); w.grab_set(); bg=self.prefs['bg']; panel=self.prefs['panel']; fields={}
        tk.Label(w,text=f"Configurações: {g['name']}",bg=bg,fg='#f0f3ff',font=('DejaVu Sans',15,'bold')).pack(anchor='w',padx=20,pady=(18,0))
        def field(label,key,val):
            tk.Label(w,text=label,bg=bg,fg='#dce3f8',font=('DejaVu Sans',9,'bold')).pack(anchor='w',padx=20,pady=(10,3)); e=tk.Entry(w,bg=panel,fg='#f0f3ff',insertbackground='white',relief='flat'); e.pack(fill='x',padx=20,ipady=7); e.insert(0,val or ''); fields[key]=e
        field('Nome exibido','name',g.get('name','')); field('Prefixo Wine (vazio = padrão)','prefix',g.get('prefix','')); field('Argumentos de inicialização','args',g.get('args','')); field('Variáveis de ambiente, uma por linha (ex.: DXVK_HUD=fps)','env',g.get('env',''))
        fps=tk.BooleanVar(value=bool(g.get('fps'))); tk.Checkbutton(w,text='Mostrar FPS com MangoHud (se instalado)',variable=fps,bg=bg,fg='#dce3f8',selectcolor=panel,activebackground=bg).pack(anchor='w',padx=20,pady=(14,4))
        tk.Label(w,text='MangoHud precisa estar instalado e pode não funcionar em todos os jogos.',bg=bg,fg='#9aa6c2',font=('DejaVu Sans',8),wraplength=560).pack(anchor='w',padx=20)
        def browse():
            p=filedialog.askdirectory(title='Pasta do prefixo Wine',parent=w)
            if p: fields['prefix'].delete(0,'end'); fields['prefix'].insert(0,p)
        self.btn(w,'Procurar prefixo…',browse).pack(anchor='w',padx=20,pady=8)
        def save():
            if not fields['name'].get().strip(): messagebox.showerror('Nome obrigatório','Digite um nome.',parent=w); return
            g['name']=fields['name'].get().strip(); g['prefix']=fields['prefix'].get().strip(); g['args']=fields['args'].get().strip(); g['env']=fields['env'].get().strip(); g['fps']=fps.get(); self.games.sort(key=lambda x:x.get('name','').casefold()); self.save(GAMES,self.games); self.selected=next((j for j,x in enumerate(self.games) if x['path']==g['path']),None); self.refresh()
            if self.selected is not None: self.tree.selection_set(str(self.selected)); self.on_select()
            w.destroy(); self.status.set('Configurações salvas')
        self.btn(w,'Salvar configurações',save,self.prefs['accent'],'#fff',font=('DejaVu Sans',10,'bold')).pack(side='bottom',anchor='e',padx=20,pady=18)
    def preferences(self):
        w=tk.Toplevel(self.root); w.title('Personalização'); w.configure(bg=self.prefs['bg']); w.geometry('430x280'); w.resizable(False,False); w.transient(self.root); w.grab_set(); bg=self.prefs['bg']
        tk.Label(w,text='Personalizar o launcher',bg=bg,fg='#f0f3ff',font=('DejaVu Sans',15,'bold')).pack(anchor='w',padx=20,pady=(20,12))
        lab=tk.Label(w,text=f"Cor de destaque: {self.prefs['accent']}",bg=bg,fg='#dce3f8'); lab.pack(anchor='w',padx=20,pady=(0,8))
        def color():
            c=colorchooser.askcolor(color=self.prefs['accent'],parent=w)[1]
            if c:self.prefs['accent']=c; lab.config(text=f'Cor de destaque: {c}')
        self.btn(w,'Escolher cor de destaque',color).pack(anchor='w',padx=20)
        maximized=tk.BooleanVar(value=bool(self.prefs.get('maximized'))); tk.Checkbutton(w,text='Iniciar maximizado',variable=maximized,bg=bg,fg='#dce3f8',selectcolor=self.prefs['panel'],activebackground=bg).pack(anchor='w',padx=20,pady=14)
        def save():
            self.prefs['maximized']=maximized.get(); self.save(PREFS,self.prefs); messagebox.showinfo('Salvo','Preferências salvas. Feche e abra o launcher para aplicar a cor.'); w.destroy()
        self.btn(w,'Salvar',save,self.prefs['accent'],'#fff').pack(side='bottom',anchor='e',padx=20,pady=18)
    def launch(self):
        i=self.idx()
        if i is None: messagebox.showinfo('Selecione um jogo','Escolha um jogo primeiro.'); return
        g=self.games[i]; exe=Path(g.get('path','')).expanduser(); wine=shutil.which('wine')
        if not wine: messagebox.showerror('Wine não encontrado',"Não encontrei o comando 'wine'."); return
        if not exe.is_file(): messagebox.showerror('Arquivo não encontrado',f'Não encontrei:\n{exe}'); return
        env=os.environ.copy(); prefix=g.get('prefix','').strip()
        if prefix: env['WINEPREFIX']=str(Path(prefix).expanduser())
        for line in g.get('env','').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            if '=' not in line: messagebox.showerror('Variável inválida',f'Use NOME=valor:\n{line}'); return
            k,v=line.split('=',1); k=k.strip()
            if not k or not k.replace('_','').isalnum(): messagebox.showerror('Variável inválida',f'Nome inválido: {k}'); return
            env[k]=v.strip()
        cmd=[wine]
        if g.get('fps'):
            mh=shutil.which('mangohud')
            if mh: cmd=[mh,wine]
            else: messagebox.showwarning('MangoHud não encontrado','Instale o MangoHud para mostrar FPS. O jogo será iniciado sem a sobreposição.')
        try: cmd += shlex.split(g.get('args',''))+[str(exe)]
        except ValueError as e: messagebox.showerror('Argumentos inválidos',str(e)); return
        self.status.set(f"Iniciando {g['name']}…")
        def run():
            try:
                subprocess.Popen(cmd,cwd=str(exe.parent),env=env,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                self.root.after(0,lambda:self.status.set(f"Iniciado: {g['name']}"))
            except Exception as e: self.root.after(0,lambda err=str(e):messagebox.showerror('Erro ao iniciar',err))
        threading.Thread(target=run,daemon=True).start()
    def open_folder(self):
        i=self.idx()
        if i is None: messagebox.showinfo('Selecione um jogo','Escolha um jogo primeiro.'); return
        p=str(Path(self.games[i]['path']).expanduser().parent); opener=shutil.which('xdg-open')
        if opener: subprocess.Popen([opener,p],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        else: messagebox.showinfo('Pasta do jogo',p)

if __name__=='__main__':
    root=tk.Tk(); app=Launcher(root); root.mainloop()
