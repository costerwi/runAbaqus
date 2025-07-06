from __future__ import print_function

from glob import glob
import os
from os import path
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import font
from tkinter import filedialog
from tkinter import scrolledtext

root = tk.Tk()
root.title('Run Abaqus')

process = None

def submit():
    import subprocess
    from threading import Thread
    global process
    fullpath = jobVar.get()
    if not os.path.isfile(fullpath):
        #TODO Error
        return
    if text.index(tk.END) > '3.0':
        text.delete('1.0', tk.END)
    d, fn = path.split(fullpath)
    if d and d != os.getcwd():
        text.insert(tk.END, 'cd {}\n'.format(d))
        os.chdir(d)
    job, _ = path.splitext(fn)
    cmd = [abaqusVar.get(), 'interactive', 'job=' + job]
    oldjob, _ = path.splitext(oldjobVar.get())
    if oldjob:
        cmd.append('oldjob=' + oldjob)
    globalmodel, _ = path.splitext(globalVar.get())
    if globalmodel:
        cmd.append('global=' + globalmodel)
    user = userVar.get()
    if user:
        cmd.append('user=' + globalmodel)
    cpus = cpusVar.get()
    if cpus:
        cmd.append('cpus=' + cpus)
    license = licenseVar.get()
    if 'QXT' in license:
        cmd.append('license_model=LEGACY')
        cmd.append('license_type=TOKEN')
    elif 'SRU' in license:
        cmd.append('license_model=SIMUNIT')
        cmd.append('license_type=TOKEN')
    elif 'SUN' in license:
        cmd.append('license_model=SIMUNIT')
        cmd.append('license_type=CREDIT')

    text.insert(tk.END, ' '.join(cmd) + '\n\n')
    text.yview(tk.END)
    button['text'] = 'Terminate'
    button['command'] = terminate

    options = {}
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
        text=True,
        start_new_session=True,
        **options)
    Thread(target=readOutput, daemon=True).start()


def readOutput():
    """Monitor running process and echo data to scrolledtext"""
    fullpath = jobVar.get()
    d, fn = path.split(fullpath)
    job, _ = path.splitext(fn)
    with open(job + '.log', 'w') as logfile:
        for line in process.stdout:
            text.insert(tk.END, line)
            text.yview(tk.END)
            print(line, file=logfile, flush=True, end='')  # also echo to log file
    # Process is finished here. Summarize output
    if os.path.isfile(job + '.sta'):
        text.insert(tk.END, '\n')
        with open(job + '.sta') as sta:
            text.insert(tk.END, '\n{}\n'.format(sta.name), ('h1',))
            for line in sta:
                text.insert(tk.END, line)
                text.yview(tk.END)
    for ext in '.msg', '.dat':
        fn = job + ext
        if not os.path.isfile(fn):
            continue
        text.insert(tk.END, '\n')
        with open(fn) as out:
            heading = False
            for line in out:
                if line.startswith(' ***ERROR:') or line.startswith('           ') and previous:
                    if not heading:
                        text.insert(tk.END, '\n{}\n'.format(fn), ('h1',))
                        heading = True
                    text.insert(tk.END, line)
                    text.yview(tk.END)
                    previous = True
                else:
                    previous = False
        if heading:
            break
    button['text'] = 'Submit'
    button['command'] = submit


def terminate():
    """Kill the running process (if any)"""
    from signal import CTRL_BREAK_EVENT
    if hasattr(process, 'terminate'):
        text.insert(tk.END, 'Terminating...')
        text.yview(tk.END)
        if os.name == 'nt':
            process.send_signal(CTRL_BREAK_EVENT)
        process.terminate()


row = 0
def addFileRow(name, desc, command):
    global row
    var = tk.StringVar(name=name)
    ttk.Label(root, text=desc + ':') \
            .grid(column=0, row=row, sticky=tk.W)
    entry = ttk.Entry(root, textvariable=var)
    entry.grid(column=1, row=row, sticky=(tk.W, tk.E))
    ttk.Button(root, text='Browse...', command=command) \
            .grid(column=2, row=row)
    row += 1
    return var

def browseJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[
                ('Abaqus models', '.inp'),
                ('All files', '.*'),
                ])
    if not fullpath:
        return # cancel
    d, fn = path.split(fullpath)
    text.delete('1.0', tk.END)
    text.insert(tk.END, 'cd {}\n'.format(d))
    text.yview(tk.END)
    os.chdir(d)
    jobVar.set(fn)

def browseOldJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[('Abaqus restart files', '.res')])
    if not fullpath:
        return # cancel
    d, fn = path.split(fullpath)
    if d == os.getcwd():
        oldjobVar.set(fn)
    else:
        oldjobVar.set(fullpath)

def browseGlobalJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[('Abaqus output files', '.odb')])
    if not fullpath:
        return # cancel
    d, fn = path.split(fullpath)
    if d == os.getcwd():
        globalVar.set(fn)
    else:
        globalVar.set(fullpath)

def browseUser():
    fullpath = filedialog.askopenfilename(
            filetypes=[
                ('Fortran files', '.f .for'),
                ('c++ files', '.c .cc'),
                ('Compiled files', '.o .obj'),
                ('All files', '.*'),
                ])
    if not fullpath:
        return # cancel
    d, fn = path.split(fullpath)
    if d == os.getcwd():
        userVar.set(fn)
    else:
        userVar.set(fullpath)

jobVar = addFileRow('job', 'Job to run', browseJob)
oldjobVar = addFileRow('oldjob', 'Restart from old job', browseOldJob)
globalVar = addFileRow('global', 'Submodel from global job', browseGlobalJob)
userVar = addFileRow('user', 'User subroutine', browseUser)

cpusVar = tk.StringVar(name='cpus')
cpusVar.set('')  # Use default
ttk.Label(root, text='CPU cores:').grid(column=0, row=row, sticky=tk.W)
ttk.Spinbox(root, from_=1, to=100, textvariable=cpusVar) \
        .grid(column=1, row=row, sticky=(tk.W, tk.E))
row += 1

licenseVar = tk.StringVar(name='license')
ttk.Label(root, text='License:').grid(column=0, row=row, sticky=tk.W)
ttk.Combobox(root,
    textvariable=licenseVar,
    values=['Default', 'Extended token (QXT)', 'SimUnit token (SRU)', 'SimUnit credit (SUN'],
    state='readonly',
    ).grid(column=1, row=row, sticky=(tk.W, tk.E))
row += 1

versions = set()
for p in os.getenv('PATH', '').split(os.pathsep):
    versions.update(glob('abq2*', root_dir=p))

abaqusVar = tk.StringVar(name='abaqus')
abaqusVar.set('abaqus')
ttk.Label(root, text='Version:').grid(column=0, row=row, sticky=tk.W)
ttk.Combobox(root,
    textvariable=abaqusVar,
    values=[os.path.splitext(p)[0] for p in sorted(versions)],
    ).grid(column=1, row=row, sticky=(tk.W, tk.E))
row += 1

button = ttk.Button(text='Submit', command=submit)
button.grid(column=1, row=row, sticky=tk.W)
row += 1

text = scrolledtext.ScrolledText(root)
text.grid(column=1, row=row, sticky=(tk.W, tk.E, tk.N, tk.S))
h1font = font.nametofont('TkTextFont').actual()
h1font['size'] = 14
h1font['weight'] = 'bold'
text.tag_configure('h1', font=h1font)

root.columnconfigure(1, weight=1)
root.rowconfigure(row, weight=1)

root.mainloop()

