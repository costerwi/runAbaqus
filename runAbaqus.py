#!/bin/env python3
"""runAbaqus GUI interface to most common Abaqus solver parameters

Carl Osterwisch, July 2025
"""

import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText

__version__ = '0.1.0'


class App(tk.Tk):
    """Main App Windows"""
    def __init__(self):
        super().__init__()
        self.title('Run Abaqus ' + __version__)


class Text(ScrolledText):
    """ScrolledText with customized tag styles"""
    def __init__(self, container):
        super().__init__()
        h1font = Font(font='TkTextFont')
        h1font['size'] = 14
        h1font['weight'] = 'bold'
        self.tag_configure('h1', font=h1font)
        self.tag_configure('sta', background='lightcyan1')
        self.tag_configure('err', background='mistyrose1')


class Dialog():
    """Build dialog and respond to its events"""

    def __init__(self, container, text):
        """Create and pack widgets into container"""
        self.container = container
        self.text = text
        self.process = None # process running the solver

        # Create user interface to collect file names
        self.jobVar = self.addFileRow(container, 'job', 'Job to run', self.browseJob)
        self.oldjobVar = self.addFileRow(container, 'oldjob', 'Restart from old job', self.browseOldJob)
        self.globalVar = self.addFileRow(container, 'global', 'Submodel from global job', self.browseGlobalJob)
        self.userVar = self.addFileRow(container, 'user', 'User subroutine', self.browseUser)

        buttonRow = ttk.Frame(container)

        # Create button to submit job
        self.commandButton = ttk.Button(buttonRow, text='Run', command=self.submit,
                                   style='command.TButton')
        self.commandButton.pack(side=tk.RIGHT)

        # Allow user to specify CPUs
        self.cpusVar = tk.StringVar(name='cpus')
        self.cpusVar.set('')  # Use default
        frame = ttk.Frame(buttonRow)
        ttk.Label(frame, text='CPU cores:').pack(side=tk.LEFT)
        ttk.Spinbox(frame, from_=1, to=1000, textvariable=self.cpusVar, width=4).pack()
        frame.pack(side=tk.LEFT)

        # Allow user to specify GPUs
        self.gpusVar = tk.StringVar(name='gpus')
        self.gpusVar.set('')  # Use default
        frame = ttk.Frame(buttonRow)
        ttk.Label(frame, text='GPUs:').pack(side=tk.LEFT)
        ttk.Spinbox(frame, from_=0, to=100, textvariable=self.gpusVar, width=4).pack()
        frame.pack(side=tk.LEFT)

        # Find all abaqus versions available in the PATH
        self.versions = {}
        for directory in os.getenv('PATH', '').split(os.pathsep):
            for cmd in 'abaqus*', 'abq2*':
                for fullpath in Path(directory).glob(cmd):
                    if not fullpath.is_file():
                        continue  # must be a file
                    if os.name == 'nt':
                        if fullpath.suffix != '.bat':
                            continue  # must be a batch file
                    else:
                        if not os.access(fullpath, os.X_OK):
                            continue  # must be executable
                    self.versions[fullpath.stem] = fullpath
        versionList=list(sorted(self.versions))
        self.abaqusVar = tk.StringVar(name='abaqus')
        if len(versionList):
            self.abaqusVar.set(versionList[0])
        ttk.Combobox(buttonRow,
            textvariable=self.abaqusVar,
            values=versionList,
            state='readonly',
            ).pack(side=tk.LEFT)

        # Offer license choices
        licenses=['Default license type', 'Extended tokens (QXT)',
                  'SimUnit tokens (SRU)', 'SimUnit credits (SUN)']
        self.licenseVar = tk.StringVar(name='license')
        self.licenseVar.set(licenses[0])
        ttk.Combobox(buttonRow,
            textvariable=self.licenseVar,
            values=licenses,
            state='readonly',
            ).pack(side=tk.LEFT)

        ttk.Button(buttonRow, text='Help...', command=self.getHelp).pack(side=tk.RIGHT)

        buttonRow.pack(fill=tk.X)

        cmdfont = Font(font='TkButtonFont')
        cmdfont['weight'] = 'bold'
        style = ttk.Style()
        style.configure('command.TButton', font=cmdfont)


    def submit(self):
        """Collect settings and launch abaqus solver"""
        import subprocess
        from tkinter.messagebox import showerror
        from threading import Thread
        inp = self.jobVar.get()
        if not inp:
            showerror(
                title='Nothing to run',
                message='You must specify an Abaqus job to run',
                )
            return
        inpPath = Path(inp)
        if not inpPath.is_file():
            showerror(
                title='File not found',
                message=inpPath.absolute(),
                )
            return
        if self.text.index(tk.END) > '3.0':
            self.text.delete('1.0', tk.END)
        if inpPath.parent != Path('.'):
            self.text.insert(tk.END, 'cd {}\n'.format(inpPath.parent))
            os.chdir(inpPath.parent)
        job = inpPath.stem
        cmd = [self.abaqusVar.get(), 'interactive', 'job=' + job]
        if inpPath.suffix != '.inp':
            cmd.append('input=' + str(inpPath.name))
        oldjob = self.oldjobVar.get().strip()
        if oldjob:
            cmd.append('oldjob=' + os.path.splitext(oldjob)[0])
        globalmodel = self.globalVar.get().strip()
        if globalmodel:
            cmd.append('globalmodel=' + globalmodel)
        user = self.userVar.get().strip()
        if user:
            cmd.append('user=' + user)
        cpus = self.cpusVar.get().strip()
        if cpus:
            cmd.append('cpus=' + cpus)
        gpus = self.gpusVar.get().strip()
        if gpus:
            cmd.append('gpus=' + gpus)
        license = self.licenseVar.get().strip()
        if 'QXT' in license:
            cmd.append('license_model=LEGACY')
        elif 'SRU' in license:
            cmd.append('license_model=SIMUNIT')
            cmd.append('license_type=TOKEN')
        elif 'SUN' in license:
            cmd.append('license_model=SIMUNIT')
            cmd.append('license_type=CREDIT')

        self.text.insert(tk.END, ' '.join(cmd) + '\n\n')
        self.text.yview(tk.END)
        self.commandButton['text'] = 'Stop'
        self.commandButton['command'] = self.terminate

        cmd[0] = self.versions[cmd[0]]  # expand to full path
        options = {}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
            **options)
        Thread(target=self.monitorJob, args=[job], daemon=True).start()  # monitor in a non-blocking Thread


    def monitorJob(self, job):
        """Monitor running process and echo output to scrolledtext"""
        from threading import Thread
        sta = None
        with open(job + '.log', 'w') as logfile:
            self.text.insert(tk.END, logfile.name + '\n', ('h1',))
            for line in self.process.stdout:
                self.text.insert(tk.END, line)
                self.text.yview(tk.END)
                print(line, file=logfile, flush=True, end='')  # also echo to log file
                if not sta and line.startswith('Run standard'):
                    # start real-time sta file monitor for Standard jobs
                    sta = Thread(target=self.monitorSta, args=[job])
                    sta.start()
        if sta:
            sta.join()  # wait for monitorSta to complete
        for ext in '.dat', '.msg':  # Files to scan for errors
            filePath = Path(job).with_suffix(ext)
            if not filePath.is_file():
                continue
            with filePath.open() as out:
                heading = None
                previousError = False
                for line in out:
                    if line.startswith(' ***ERROR:') or line.startswith('           ') and previousError:
                        if not heading:
                            heading = '\n{} errors\n'.format(filePath)
                            self.text.insert(tk.END, heading, ('h1', 'err'))
                        self.text.insert(tk.END, line, ('err',))
                        self.text.yview(tk.END)
                        previousError = True
                    else:
                        previousError = False
        self.commandButton['text'] = 'Run'
        self.commandButton['command'] = self.submit


    def monitorSta(self, job):
        """Monitor sta file and echo output to scrolledtext"""
        import time
        staPath = Path(job).with_suffix('.sta')
        while self.process.poll() is None and not staPath.is_file():
            # waiting for sta file
            time.sleep(5)
        if not staPath.is_file():
            return
        with staPath.open() as sta:
            heading = '\n{}\n'.format(staPath)
            self.text.insert(tk.END, heading, ('h1', 'sta'))
            while True:
                line = sta.readline()
                if line:
                    self.text.insert(tk.END, line, ('sta',))
                    self.text.yview(tk.END)
                else:
                    if self.process.poll() != None:
                        break  # process is finished
                    time.sleep(2)


    def terminate(self):
        """Kill the running process (if any)"""
        import signal
        if self.process.poll() is None:
            self.text.insert(tk.END, 'Stopping...\n', ('err',))
            self.text.yview(tk.END)
            if os.name == 'nt':
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process.terminate()
        else:
            self.text.insert(tk.END, 'Waiting for final log messages...', ('err',))
            self.text.yview(tk.END)


    def addFileRow(self, container, name, desc, command):
        """Create widgets to allow user to specify a file"""
        tkVar = tk.StringVar(name=name)
        row = ttk.Frame(container)
        ttk.Label(row, text=desc + ':', width=25).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=tkVar).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row, text='Browse...', command=command).pack(side=tk.RIGHT)
        row.pack(side=tk.TOP, fill=tk.X)
        return tkVar

    def browseJob(self):
        filename = askopenfilename(
                title='Select Abaqus job to run',
                initialdir=Path(self.oldjobVar.get()).parent,
                filetypes=[
                    ('Abaqus models', '.inp'),
                    ('All files', '.*'),
                    ])
        if not filename:
            return # cancelled
        filePath = Path(filename)
        self.text.delete('1.0', tk.END)
        self.text.insert(tk.END, 'cd {}\n'.format(filePath.parent))
        os.chdir(filePath.parent)
        self.jobVar.set(filePath.name)

    def browseOldJob(self):
        filename = askopenfilename(
                title='Select old job to restart from',
                initialdir=Path(self.oldjobVar.get()).parent,
                filetypes=[('Abaqus restart files', '.res')])
        if not filename:
            return # cancelled
        fullPath = Path(filename)
        if fullPath.parent == Path.cwd():
            self.oldjobVar.set(fullPath.name)
        else:
            self.oldjobVar.set(fullPath)

    def browseGlobalJob(self):
        fileName = askopenfilename(
                title='Select global model results',
                initialdir=Path(self.globalVar.get()).parent,
                filetypes=[('Abaqus results', '.fil .odb .sim')])
        if not fileName:
            return # cancelled
        fullPath = Path(fileName)
        if fullPath.parent == Path.cwd():
            self.globalVar.set(fullPath.name)
        else:
            self.globalVar.set(fullPath)

    def browseUser(self):
        fileName = askopenfilename(
                title='Select custom user subroutine',
                initialdir=Path(self.userVar.get()).parent,
                filetypes=[
                    ('Fortran files', '.f .for .f90 .F90'),
                    ('c++ files', '.c .C .cpp .c++'),
                    ('Compiled files', '.o .obj'),
                    ('All files', '.*'),
                    ])
        if not fileName:
            return # cancel
        fullPath = Path(fileName)
        if fullPath.parent == Path.cwd():
            self.userVar.set(fullPath.name)
        else:
            self.userVar.set(fullPath)


    def getHelp(self):
        """Open help in browser"""
        import webbrowser
        webbrowser.open('https://help.3ds.com')


if __name__ == '__main__':
    app = App()
    text = Text(app)
    text.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)
    Dialog(app, text)
    app.mainloop()

