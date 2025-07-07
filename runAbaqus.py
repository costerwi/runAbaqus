"""runAbaqus GUI interface to most common Abaqus solver parameters

Carl Osterwisch, July 2025
"""

from __future__ import print_function
from glob import glob
import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import font
from tkinter import filedialog
from tkinter import scrolledtext

__version__ = '0.1.0'

root = tk.Tk()
root.title('Run Abaqus ' + __version__)
style = ttk.Style()
style.configure('command.TButton', background='blue')

process = None # process running the solver

def submit():
    """Collect settings and launch abaqus solver"""
    import subprocess
    from tkinter.messagebox import showerror
    from threading import Thread
    global process
    fullpath = jobVar.get()
    if not fullpath:
        showerror(
            title='Nothing to run',
            message='You must specify an Abaqus job to run',
            )
        return
    if not os.path.isfile(fullpath):
        showerror(
            title='File not found',
            message=os.path.abspath(fullpath),
            )
        return
    if text.index(tk.END) > '3.0':
        text.delete('1.0', tk.END)
    d, fn = os.path.split(fullpath)
    if d and d != os.getcwd():
        text.insert(tk.END, 'cd {}\n'.format(d))
        os.chdir(d)
    job, ext = os.path.splitext(fn)
    cmd = [abaqusVar.get(), 'interactive', 'job=' + job]
    if ext != '.inp':
        cmd.append('input=' + fn)
    oldjob, _ = os.path.splitext(oldjobVar.get())
    if oldjob:
        cmd.append('oldjob=' + oldjob)
    globalmodel, _ = os.path.splitext(globalVar.get())
    if globalmodel:
        cmd.append('global=' + globalmodel)
    user = userVar.get()
    if user:
        cmd.append('user=' + user)
    cpus = cpusVar.get()
    if cpus:
        cmd.append('cpus=' + cpus)
    gpus = gpusVar.get()
    if gpus:
        cmd.append('gpus=' + gpus)
    license = licenseVar.get()
    if 'QXT' in license:
        cmd.append('license_model=LEGACY')
    elif 'SRU' in license:
        cmd.append('license_model=SIMUNIT')
        cmd.append('license_type=TOKEN')
    elif 'SUN' in license:
        cmd.append('license_model=SIMUNIT')
        cmd.append('license_type=CREDIT')

    text.insert(tk.END, ' '.join(cmd) + '\n\n')
    text.yview(tk.END)
    commandButton['text'] = 'Terminate'
    commandButton['command'] = terminate

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
    Thread(target=monitorJob, args=[job], daemon=True).start()  # monitor in a non-blocking Thread


def monitorJob(job):
    """Monitor running process and echo output to scrolledtext"""
    from threading import Thread
    sta = None
    with open(job + '.log', 'w') as logfile:
        text.insert(tk.END, logfile.name + '\n', ('h1',))
        for line in process.stdout:
            text.insert(tk.END, line)
            text.yview(tk.END)
            print(line, file=logfile, flush=True, end='')  # also echo to log file
            if not sta and line.startswith('Run standard'):
                # start real-time sta file monitor for Standard jobs
                sta = Thread(target=monitorSta, args=[job])
                sta.start()
    if sta:
        sta.join()  # wait for monitorSta to complete
    for ext in '.dat', '.msg':  # Files to scan for errors
        fn = job + ext
        if not os.path.isfile(fn):
            continue
        with open(fn) as out:
            heading = None
            previousError = False
            for line in out:
                if line.startswith(' ***ERROR:') or line.startswith('           ') and previousError:
                    if not heading:
                        heading = '\n{} errors\n'.format(fn)
                        text.insert(tk.END, heading, ('h1', 'err'))
                    text.insert(tk.END, line, ('err',))
                    text.yview(tk.END)
                    previousError = True
                else:
                    previousError = False
    commandButton['text'] = 'Run'
    commandButton['command'] = submit


def monitorSta(job):
    """Monitor sta file and echo output to scrolledtext"""
    import time
    fn = job + '.sta'
    while process.poll() is None and not os.path.isfile(fn):
        # waiting for sta file
        time.sleep(5)
    if not os.path.isfile(fn):
        return
    with open(fn) as sta:
        heading = '\n{}\n'.format(fn)
        text.insert(tk.END, heading, ('h1', 'sta'))
        while True:
            line = sta.readline()
            if line:
                text.insert(tk.END, line, ('sta',))
                text.yview(tk.END)
            else:
                if process.poll() != None:
                    break  # process is finished
                time.sleep(2)


def terminate():
    """Kill the running process (if any)"""
    from signal import CTRL_BREAK_EVENT
    if hasattr(process, 'terminate'):
        text.insert(tk.END, 'Terminating...')
        text.yview(tk.END)
        if os.name == 'nt':
            process.send_signal(CTRL_BREAK_EVENT)
        process.terminate()


def addFileRow(name, desc, command):
    """Create widgets to allow user to specify a file"""
    tkVar = tk.StringVar(name=name)
    row = ttk.Frame(root)
    ttk.Label(row, text=desc + ':', width=25).pack(side=tk.LEFT)
    ttk.Entry(row, textvariable=tkVar).pack(side=tk.LEFT, fill=tk.X, expand=True)
    ttk.Button(row, text='Browse...', command=command).pack(side=tk.RIGHT)
    row.pack(side=tk.TOP, fill=tk.X)
    return tkVar

def browseJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[
                ('Abaqus models', '.inp'),
                ('All files', '.*'),
                ])
    if not fullpath:
        return # cancelled
    d, fn = os.path.split(fullpath)
    text.delete('1.0', tk.END)
    text.insert(tk.END, 'cd {}\n'.format(d))
    text.yview(tk.END)
    os.chdir(d)
    jobVar.set(fn)

def browseOldJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[('Abaqus restart files', '.res')])
    if not fullpath:
        return # cancelled
    d, fn = os.path.split(fullpath)
    if d == os.getcwd():
        oldjobVar.set(fn)
    else:
        oldjobVar.set(fullpath)

def browseGlobalJob():
    fullpath = filedialog.askopenfilename(
            filetypes=[('Abaqus output files', '.odb')])
    if not fullpath:
        return # cancelled
    d, fn = os.path.split(fullpath)
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
    d, fn = os.path.split(fullpath)
    if d == os.getcwd():
        userVar.set(fn)
    else:
        userVar.set(fullpath)

# Create user interface to collect file names
jobVar = addFileRow('job', 'Job to run', browseJob)
oldjobVar = addFileRow('oldjob', 'Restart from old job', browseOldJob)
globalVar = addFileRow('global', 'Submodel from global job', browseGlobalJob)
userVar = addFileRow('user', 'User subroutine', browseUser)

buttonRow = ttk.Frame(root)

# Create button to submit job
commandButton = ttk.Button(buttonRow, text='Run', command=submit,
                           style='command.TButton')
commandButton.pack(side=tk.RIGHT)

# Allow user to specify CPUs
cpusVar = tk.StringVar(name='cpus')
cpusVar.set('')  # Use default
frame = ttk.Frame(buttonRow)
ttk.Label(frame, text='CPU cores:').pack(side=tk.LEFT)
ttk.Spinbox(frame, from_=1, to=1000, textvariable=cpusVar, width=4).pack()
frame.pack(side=tk.LEFT)

# Allow user to specify GPUs
gpusVar = tk.StringVar(name='gpus')
gpusVar.set('')  # Use default
frame = ttk.Frame(buttonRow)
ttk.Label(frame, text='GPUs:').pack(side=tk.LEFT)
ttk.Spinbox(frame, from_=1, to=100, textvariable=gpusVar, width=4).pack()
frame.pack(side=tk.LEFT)

# Find all abaqus versions available in the PATH
versions = set()
for directory in os.getenv('PATH', '').split(os.pathsep):
    versions.update(glob('abq2*', root_dir=directory))
versions=['abaqus'] + [os.path.splitext(abq)[0] for abq in sorted(versions)]
abaqusVar = tk.StringVar(name='abaqus')
abaqusVar.set(versions[0])
ttk.Combobox(buttonRow,
    textvariable=abaqusVar,
    values=versions,
    state='readonly',
    ).pack(side=tk.LEFT)

# Offer license choices
licenses=['Default license', 'Extended tokens (QXT)', 'SimUnit tokens (SRU)', 'SimUnit credits (SUN)']
licenseVar = tk.StringVar(name='license')
licenseVar.set(licenses[0])
ttk.Combobox(buttonRow,
    textvariable=licenseVar,
    values=licenses,
    state='readonly',
    ).pack(side=tk.LEFT)

def getHelp():
    """Open help in browser"""
    import webbrowser
    webbrowser.open('https://help.3ds.com')
ttk.Button(buttonRow, text='Help...', command=getHelp).pack(side=tk.RIGHT)

buttonRow.pack(fill=tk.X)

# Create text widget to display log
text = scrolledtext.ScrolledText(root)
text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
h1font = font.nametofont('TkTextFont').actual()
h1font['size'] = 14
h1font['weight'] = 'bold'
text.tag_configure('h1', font=h1font)
text.tag_configure('sta', background='lightcyan1')
text.tag_configure('err', background='mistyrose1')


root.mainloop()

