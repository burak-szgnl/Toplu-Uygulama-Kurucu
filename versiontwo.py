import os
import shutil
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import threading
import sqlite3
import json
import time
import zipfile

try:
    from plyer import notification
except ImportError:
    notification = None

# ------------------- DİLLER -------------------
translations = {
    "en": {"source_label":"Source Folders:","target_label":"Target Folders / USB:","filetype_label":"Select File Types:","all_label":"All","start_button":"Start","reset_button":"Reset","backup_started":"Backup started...","backup_complete":"Backup completed!","invalid_source":"Select at least one source folder.","invalid_target":"Select at least one target folder."},
    "tr": {"source_label":"Kaynak Klasörler:","target_label":"Hedef Klasörler / USB:","filetype_label":"Dosya Türlerini Seç:","all_label":"Hepsi","start_button":"Başlat","reset_button":"Sıfırla","backup_started":"Yedekleme başladı...","backup_complete":"Yedekleme tamamlandı!","invalid_source":"En az bir kaynak klasör seçin.","invalid_target":"En az bir hedef klasör seçin."},
    "de": {"source_label":"Quellordner:","target_label":"Zielordner / USB:","filetype_label":"Dateitypen auswählen:","all_label":"Alle","start_button":"Start","reset_button":"Zurücksetzen","backup_started":"Backup gestartet...","backup_complete":"Backup abgeschlossen!","invalid_source":"Wählen Sie mindestens einen Quellordner aus.","invalid_target":"Wählen Sie mindestens einen Zielordner aus."},
    "zh": {"source_label":"源文件夹:","target_label":"目标文件夹 / USB:","filetype_label":"选择文件类型:","all_label":"全部","start_button":"开始","reset_button":"重置","backup_started":"备份开始...","backup_complete":"备份完成!","invalid_source":"请选择至少一个源文件夹。","invalid_target":"请选择至少一个目标文件夹。"},
    "ja": {"source_label":"ソースフォルダ:","target_label":"ターゲットフォルダ / USB:","filetype_label":"ファイルタイプを選択:","all_label":"全て","start_button":"開始","reset_button":"リセット","backup_started":"バックアップ開始...","backup_complete":"バックアップ完了!","invalid_source":"少なくとも1つのソースフォルダを選択してください。","invalid_target":"少なくとも1つのターゲットフォルダを選択してください。"},
    "ru": {"source_label":"Исходные папки:","target_label":"Папки назначения / USB:","filetype_label":"Выберите типы файлов:","all_label":"Все","start_button":"Старт","reset_button":"Сброс","backup_started":"Резервное копирование начато...","backup_complete":"Резервное копирование завершено!","invalid_source":"Выберите хотя бы одну исходную папку.","invalid_target":"Выберите хотя бы одну папку назначения."}
}

languages = ["English","Türkçe","Deutsch","中文","日本語","Русский"]
lang_map = {"English":"en","Türkçe":"tr","Deutsch":"de","中文":"zh","日本語":"ja","Русский":"ru"}

# ------------------- VERİTABANI -------------------
def init_db():
    conn = sqlite3.connect("backup_log.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, source TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def log_db(source,status):
    try:
        conn = sqlite3.connect("backup_log.db")
        c = conn.cursor()
        zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO log (timestamp, source, status) VALUES (?,?,?)",(zaman,source,status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Log error: {e}")

# ------------------- UYGULAMA -------------------
class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Backup Tool")
        self.root.geometry("850x700")
        self.root.configure(bg="#f2f2f2")
        self.settings = self.load_settings()
        self.profiles = self.settings.get("profiles",{})
        self.current_profile = None

        # Başlangıçta profil seçim frame'i
        self.profile_frame = tk.Frame(root,bg="#f2f2f2")
        self.profile_frame.pack(padx=20,pady=20)

        tk.Label(self.profile_frame,text="Select Profile:",bg="#f2f2f2").grid(row=0,column=0,sticky="w")
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(self.profile_frame,textvariable=self.profile_var,state="readonly",values=list(self.profiles.keys()))
        self.profile_combo.grid(row=0,column=1,sticky="w")

        self.add_profile_btn = tk.Button(self.profile_frame,text="Add",command=self.add_profile,width=8)
        self.add_profile_btn.grid(row=0,column=2,padx=5)
        self.delete_profile_btn = tk.Button(self.profile_frame,text="Delete",command=self.delete_profile,width=8)
        self.delete_profile_btn.grid(row=0,column=3,padx=5)
        self.select_profile_btn = tk.Button(self.profile_frame,text="Select",command=self.select_profile,width=8)
        self.select_profile_btn.grid(row=0,column=4,padx=5)

        # Ana frame gizli
        self.main_frame = tk.Frame(root,bg="#f2f2f2")
        self.main_frame.pack(padx=10,pady=10,fill=tk.BOTH,expand=True)
        self.main_frame.pack_forget()

        self.current_lang = tk.StringVar(value="English")
        self.kaynak_list = []
        self.hedef_list = []
        self.file_types = [".txt",".jpg",".png",".pdf",".docx"]
        self.file_type_vars = {}
        self.all_var = tk.BooleanVar()
        self.zip_var = tk.BooleanVar()  # ZIP checkbox için

        self.setup_main_ui()
        init_db()

    # ------------------- PROFİL FONKSİYONLARI -------------------
    def add_profile(self):
        name = simpledialog.askstring("New Profile","Enter profile name:")
        if name and name not in self.profiles:
            self.profiles[name] = {"source_folder_list":[],"target_folder_list":[],"file_types":self.file_types,"language":"English"}
            self.profile_combo['values'] = list(self.profiles.keys())
            self.save_settings()

    def delete_profile(self):
        profile = self.profile_var.get()
        if profile in self.profiles:
            if messagebox.askyesno("Delete","Delete profile?"):
                del self.profiles[profile]
                self.profile_combo['values'] = list(self.profiles.keys())
                self.save_settings()

    def select_profile(self):
        profile = self.profile_var.get()
        if profile:
            self.current_profile = profile
            data = self.profiles.get(profile,{})
            self.kaynak_list = data.get("source_folder_list",[])
            self.hedef_list = data.get("target_folder_list",[])
            self.current_lang.set(data.get("language","English"))
            self.profile_frame.pack_forget()
            self.main_frame.pack(padx=10,pady=10,fill=tk.BOTH,expand=True)
            self.update_labels()

    # ------------------- ANA PANEL UI -------------------
    def setup_main_ui(self):
        # Kaynak listesi
        self.source_label = tk.Label(self.main_frame,text="",bg="#f2f2f2")
        self.source_label.grid(row=0,column=0,sticky="w")
        self.source_listbox = tk.Listbox(self.main_frame,height=5,width=40)
        self.source_listbox.grid(row=0,column=1)
        tk.Button(self.main_frame,text="Add Source",command=self.kaynak_ekle).grid(row=0,column=2,padx=5)

        # Hedef listesi
        self.target_label = tk.Label(self.main_frame,text="",bg="#f2f2f2")
        self.target_label.grid(row=1,column=0,sticky="w")
        self.target_listbox = tk.Listbox(self.main_frame,height=5,width=40)
        self.target_listbox.grid(row=1,column=1)
        tk.Button(self.main_frame,text="Add Target",command=self.hedef_ekle).grid(row=1,column=2,padx=5)

        # Dosya türleri
        frame = tk.Frame(self.main_frame,bg="#f2f2f2")
        frame.grid(row=2,column=0,columnspan=3,pady=5)
        self.all_cb = tk.Checkbutton(frame,text="All",variable=self.all_var,command=self.toggle_all,bg="#f2f2f2")
        self.all_cb.pack(side=tk.LEFT,padx=5)
        for ext in self.file_types:
            var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(frame,text=ext,variable=var,bg="#f2f2f2")
            cb.pack(side=tk.LEFT,padx=5)
            self.file_type_vars[ext] = var

        # ZIP yedekleme checkbox
        self.zip_cb = tk.Checkbutton(self.main_frame, text="Backup as ZIP", variable=self.zip_var, bg="#f2f2f2")
        self.zip_cb.grid(row=2, column=3, padx=5)

        # Dil seçimi
        tk.Label(self.main_frame,text="Language:",bg="#f2f2f2").grid(row=3,column=0,sticky="w",pady=(5,0))
        self.lang_combo = ttk.Combobox(self.main_frame,values=languages,textvariable=self.current_lang,state="readonly",width=12)
        self.lang_combo.grid(row=3,column=1,sticky="w",pady=(5,0))
        self.lang_combo.bind("<<ComboboxSelected>>",self.update_labels)

        # Başlat / Sıfırla
        self.start_btn = tk.Button(self.main_frame,text="",command=self.start_backup_thread,width=15,bg="#b3b3b3")
        self.reset_btn = tk.Button(self.main_frame,text="",command=self.reset_all,width=15,bg="#b3b3b3")
        self.start_btn.grid(row=4,column=0,pady=10)
        self.reset_btn.grid(row=4,column=1,pady=10)

        # Log ve durum
        self.durum_label = tk.Label(self.main_frame,text="",fg="blue",bg="#f2f2f2")
        self.durum_label.grid(row=5,column=0,columnspan=3,sticky="w")
        self.log_text = tk.Text(self.main_frame,height=10)
        self.log_text.grid(row=6,column=0,columnspan=3,pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame,orient=tk.HORIZONTAL,length=750,mode="determinate")
        self.progress.grid(row=7,column=0,columnspan=3,pady=5)

    # ------------------- FONKSİYONLAR -------------------
    def update_labels(self,event=None):
        code = lang_map[self.current_lang.get()]
        self.source_label.config(text=translations[code]["source_label"])
        self.target_label.config(text=translations[code]["target_label"])
        self.start_btn.config(text=translations[code]["start_button"])
        self.reset_btn.config(text=translations[code]["reset_button"])
        self.all_cb.config(text=translations[code]["all_label"])

        self.source_listbox.delete(0,tk.END)
        for k in self.kaynak_list: self.source_listbox.insert(tk.END,k)
        self.target_listbox.delete(0,tk.END)
        for h in self.hedef_list: self.target_listbox.insert(tk.END,h)

    def toggle_all(self):
        val = self.all_var.get()
        for var in self.file_type_vars.values(): var.set(val)

    def kaynak_ekle(self):
        klasor = filedialog.askdirectory()
        if klasor and klasor not in self.kaynak_list:
            self.kaynak_list.append(klasor)
            self.update_labels()
            self.save_settings()

    def hedef_ekle(self):
        klasor = filedialog.askdirectory()
        if klasor and klasor not in self.hedef_list:
            self.hedef_list.append(klasor)
            self.update_labels()
            self.save_settings()

    def reset_all(self):
        self.kaynak_list.clear()
        self.hedef_list.clear()
        for var in self.file_type_vars.values(): var.set(False)
        self.all_var.set(False)
        self.zip_var.set(False)
        self.current_lang.set("English")
        self.update_labels()
        self.save_settings()

    def save_settings(self):
        if self.current_profile:
            self.profiles[self.current_profile] = {"source_folder_list":self.kaynak_list,"target_folder_list":self.hedef_list,"file_types":self.file_types,"language":self.current_lang.get()}
        data = {"profiles":self.profiles}
        with open("settings.json","w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=4)

    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json","r",encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ------------------- Yedekleme -------------------
    def start_backup_thread(self):
        threading.Thread(target=self.run_backup).start()

    def run_backup(self):
        code = lang_map[self.current_lang.get()]
        if not self.kaynak_list: messagebox.showerror("Error",translations[code]["invalid_source"]); return
        if not self.hedef_list: messagebox.showerror("Error",translations[code]["invalid_target"]); return
        self.durum_label.config(text=translations[code]["backup_started"])
        self.progress['value'] = 0
        files = []

        # Dosya toplama
        for src in self.kaynak_list:
            for root, dirs, fns in os.walk(src):
                for f in fns:
                    if self.all_var.get() or any(f.endswith(ext) for ext, var in self.file_type_vars.items() if var.get()):
                        files.append((src, os.path.join(root, f)))

        total = len(files)
        if total == 0:
            messagebox.showinfo("Info", "No files")
            return

        # ZIP seçeneği varsa
        if self.zip_var.get():
            for tgt in self.hedef_list:
                zip_name = os.path.join(tgt, f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for idx, (src, f) in enumerate(files, 1):
                        rel_path = os.path.relpath(f, src)
                        zipf.write(f, arcname=rel_path)
                        log_db(f, f"Success->ZIP:{zip_name}")
                        self.log_text.insert(tk.END, f"{f} -> ZIP:{zip_name} OK\n")
                        self.progress['value'] = idx / total * 100
                        self.root.update_idletasks()
        else:
            # Normal kopyalama
            for idx, (src, f) in enumerate(files, 1):
                rel = os.path.relpath(f, src)
                for tgt in self.hedef_list:
                    dst = os.path.join(tgt, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    try:
                        shutil.copy2(f, dst)
                        log_db(f, f"Success->{tgt}")
                        self.log_text.insert(tk.END, f"{f} -> {tgt} OK\n")
                    except Exception as e:
                        log_db(f, f"Error->{tgt}:{e}")
                        self.log_text.insert(tk.END, f"{f} -> {tgt} ERROR:{e}\n")
                self.progress['value'] = idx / total * 100
                self.root.update_idletasks()

        self.durum_label.config(text=translations[code]["backup_complete"])
        if notification:
            notification.notify(title="Backup",message=translations[code]["backup_complete"],timeout=5)

if __name__ == "__main__":
    root = tk.Tk()
    app = BackupApp(root)
    root.mainloop()
