from __future__ import print_function

from glob import glob
import os
from os import path
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import scrolledtext

root = tk.Tk()
root.title('Run Abaqus')

process = None

def submit():
    from subprocess import Popen, PIPE, STDOUT
    from threading import Thread
    global process
    cmd = [abaqusVar.get(), 'interactive']
    fullpath = jobVar.get()
    if not os.path.isfile(fullpath):
        #TODO Error
        return
    d, fn = path.split(jobVar.get())
    if d and d != os.getcwd():
        text.insert(tk.END, 'cd {}\n'.format(d))
        os.chdir(d)
    job, _ = path.splitext(fn)
    cmd.extend(['job=' + job])
    oldjob, _ = path.splitext(oldjobVar.get())
    if oldjob:
        cmd.extend(['oldjob=' + oldjob])
    globalmodel, _ = path.splitext(globalVar.get())
    if globalmodel:
        cmd.extend(['global=' + globalmodel])
    user = userVar.get()
    if user:
        cmd.extend(['user=' + globalmodel])
    cpus = cpusVar.get()
    if cpus:
        cmd.extend(['cpus=' + cpus])
    text.insert(tk.END, ' '.join(cmd) + '\n')
    button['text'] = 'Terminate'
    button['command'] = terminate
    process = Popen(cmd, stdout=PIPE, stderr=STDOUT, shell=True, text=True)
    Thread(target=readOutput, daemon=True).start()


def readOutput():
    for line in process.stdout:
        text.insert(tk.END, line)
    # TODO catch errors
    button['text'] = 'Submit'
    button['command'] = submit


def terminate():
    button['text'] = 'Submit'
    button['command'] = submit
    if hasattr(process, 'terminate'):
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

root.columnconfigure(1, weight=1)
root.rowconfigure(row, weight=1)

root.mainloop()

