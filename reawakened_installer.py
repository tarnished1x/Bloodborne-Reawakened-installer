"""Bloodborne: Reawakened GUI installer, English-only, Python standard-library UI."""
from __future__ import annotations

import os
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from installer_core import install_package


def app_directory() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Bloodborne: Reawakened — Installer')
        self.geometry('790x660')
        self.minsize(700, 590)
        self.configure(bg='#101017')
        self.queue = queue.Queue()
        self.running = False
        base = app_directory()
        self.clean_var = tk.StringVar()
        self.package_var = tk.StringVar(value=str(base / 'patch_package') if (base / 'patch_package' / 'manifest.json').is_file() else '')
        self.output_var = tk.StringVar(value=str(Path.home() / 'Documents' / 'Bloodborne Reawakened'))
        candidate = base / ('xdelta3.exe' if os.name == 'nt' else 'xdelta3')
        self.xdelta_var = tk.StringVar(value=str(candidate) if candidate.is_file() else '')
        self.status_var = tk.StringVar(value='Ready — select your original game files.')
        self.counter_var = tk.StringVar(value='0%')
        self._style()
        self._layout()
        self.after(100, self._drain)

    def _style(self):
        style = ttk.Style(self)
        try: style.theme_use('clam')
        except tk.TclError: pass
        style.configure('Install.Horizontal.TProgressbar', troughcolor='#252532', background='#a85b6e', bordercolor='#252532', lightcolor='#a85b6e', darkcolor='#a85b6e')

    def _layout(self):
        frame = tk.Frame(self, bg='#101017', padx=28, pady=20)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text='BLOODBORNE: REAWAKENED', fg='#e8e5eb', bg='#101017', font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        tk.Label(frame, text='THE HUNT BEGINS ANEW   •   PATCH INSTALLER', fg='#c67a91', bg='#101017', font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(0, 15))
        tk.Label(frame, text='Creates a separate, verified Lantern-compatible mod. Your original game files are never overwritten.',
                 fg='#bdb7c5', bg='#101017', font=('Segoe UI', 10), wraplength=720, justify='left').pack(anchor='w', pady=(0, 16))
        self._field(frame, 'ORIGINAL BLOODBORNE FOLDER', self.clean_var, 'folder',
                    'Select the folder containing dvdroot_ps4 (or dvdroot_ps4 itself).')
        self._field(frame, 'REAWAKENED PATCH PACKAGE', self.package_var, 'folder',
                    'Choose the folder containing manifest.json, patches/ and extras/.')
        self._field(frame, 'INSTALL TO NEW MOD FOLDER', self.output_var, 'output',
                    'This destination must not exist yet. Choose a separate folder.')
        self._field(frame, 'XDELTA3 EXECUTABLE', self.xdelta_var, 'file',
                    'Select xdelta3.exe (the Windows version).')
        self.pbar = ttk.Progressbar(frame, style='Install.Horizontal.TProgressbar', mode='determinate', maximum=100)
        self.pbar.pack(fill='x', pady=(9, 2))
        row = tk.Frame(frame, bg='#101017')
        row.pack(fill='x')
        tk.Label(row, textvariable=self.status_var, fg='#e1ccd5', bg='#101017', anchor='w', font=('Segoe UI', 9)).pack(side='left')
        tk.Label(row, textvariable=self.counter_var, fg='#e1ccd5', bg='#101017', anchor='e', font=('Segoe UI', 9)).pack(side='right')
        self.install_button = tk.Button(frame, text='INSTALL REAWAKENED', font=('Segoe UI', 12, 'bold'), bg='#8a3e58', fg='white',
                      activebackground='#ad526e', activeforeground='white', relief='flat', cursor='hand2', padx=14, pady=12,
                      command=self._start)
        self.install_button.pack(fill='x', pady=(12, 12))
        tk.Label(frame, text='INSTALLATION LOG', fg='#beb7c7', bg='#101017', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        logframe = tk.Frame(frame, bg='#1b1b26')
        logframe.pack(fill='both', expand=True, pady=(5, 0))
        self.log = tk.Text(logframe, bg='#1b1b26', fg='#d5d1df', insertbackground='white', font=('Consolas', 9), relief='flat',
                           height=7, padx=10, pady=8, wrap='word', state='disabled')
        self.log.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(logframe, command=self.log.yview)
        scroll.pack(side='right', fill='y')
        self.log.configure(yscrollcommand=scroll.set)
        self._log('Ready. Select the four paths above, then click Install Reawakened.')

    def _field(self, parent, title, variable, mode, desc):
        tk.Label(parent, text=title, fg='#e3dde4', bg='#101017', font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        row = tk.Frame(parent, bg='#101017')
        row.pack(fill='x', pady=(4, 1))
        ent = tk.Entry(row, textvariable=variable, fg='#eae7ef', bg='#262634', insertbackground='white',
                       relief='flat', font=('Segoe UI', 10))
        ent.pack(side='left', fill='x', expand=True, ipady=7)
        tk.Button(row, text='Browse...', command=lambda: self._browse(variable, mode), font=('Segoe UI', 9),
                  fg='#fff', bg='#4a4050', activebackground='#655468', activeforeground='#fff', relief='flat',
                  cursor='hand2', padx=12, pady=5).pack(side='right', padx=(8, 0))
        tk.Label(parent, text=desc, fg='#9c95a5', bg='#101017', font=('Segoe UI', 8), anchor='w').pack(anchor='w', pady=(0, 9))

    def _browse(self, variable, mode):
        if self.running: return
        if mode == 'file':
            choice = filedialog.askopenfilename(title='Choose xdelta3.exe', filetypes=[('Executable', '*.exe'), ('All files', '*.*')])
        elif mode == 'output':
            parent = filedialog.askdirectory(title='Choose destination parent folder')
            choice = str(Path(parent) / 'Bloodborne Reawakened') if parent else ''
        else:
            choice = filedialog.askdirectory(title='Select folder')
        if choice: variable.set(choice)

    def _log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _start(self):
        if self.running: return
        paths = [x.get().strip().strip('"') for x in (self.clean_var, self.package_var, self.output_var, self.xdelta_var)]
        if not all(paths):
            messagebox.showerror('Missing information', 'Please select all four paths before installing.')
            return
        if not messagebox.askyesno('Install Reawakened', 'Install to this NEW folder?\n\n' + paths[2] + '\n\nOriginal game files will not be changed.'):
            return
        self.running = True
        self.install_button.configure(state='disabled', text='INSTALLING AND VERIFYING...')
        self.status_var.set('Starting file verification...')
        self.counter_var.set('0%')
        self.pbar.configure(value=0)
        threading.Thread(target=self._worker, args=(paths,), daemon=True).start()

    def _worker(self, paths):
        try:
            result = install_package(*paths,
                progress=lambda done, total, label: self.queue.put(('progress', done, total, label)),
                log=lambda line: self.queue.put(('log', line)))
        except Exception as exc:
            self.queue.put(('error', str(exc)))
        else:
            self.queue.put(('success', result))

    def _drain(self):
        try:
            while True:
                event = self.queue.get_nowait()
                if event[0] == 'log': self._log(event[1])
                elif event[0] == 'progress':
                    _, done, total, label = event
                    pct = round(done / total * 100)
                    self.pbar.configure(value=pct)
                    self.counter_var.set(f'{pct}%')
                    self.status_var.set(f'{label} ({done}/{total})')
                elif event[0] == 'error':
                    self._log('ERROR: ' + event[1])
                    self.status_var.set('Installation failed — see log.')
                    self._finish()
                    messagebox.showerror('Installation failed', event[1])
                elif event[0] == 'success':
                    result = event[1]
                    self.pbar.configure(value=100)
                    self.counter_var.set('100%')
                    self.status_var.set('Installation complete — SHA-256 verified.')
                    self._log('SUCCESS: ' + str(result))
                    self._finish()
                    messagebox.showinfo('Installation complete',
                        f'Bloodborne: Reawakened is ready!\n\n{result["verified_files"]} files verified.\n\n'
                        f'Your new mod folder:\n{result["output"]}\n\n'
                        'Activate this folder in Lantern Engine. Your original files were not changed.')
        except queue.Empty:
            pass
        self.after(100, self._drain)

    def _finish(self):
        self.running = False
        self.install_button.configure(state='normal', text='INSTALL REAWAKENED')


def main():
    Installer().mainloop()


if __name__ == '__main__':
    main()
