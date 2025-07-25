# runAbaqus
GUI interface to most common Abaqus solver parameters

## Installation
1. Download and unzip the [latest version](https://github.com/costerwi/runAbaqus/releases/latest). Save runAbaqus.py in a convenient location.
2. Install Python3 if you don't already have it. The latest version at the [Microsoft store](https://apps.microsoft.com/search?query=python&hl=en-US&gl=US) will work fine.
It's possible to use Python3 from Abaqus >=2024 but you'll need to make a shortcut with Target "abaqus python runAbaqus.py" and the Start in set to the folder where runAbaqus.py is located.

## Execution
Double-click <b>runAbaqus.py</b> to start the program.
You may create and use a "shortcut" if you prefer.

Complete the selections as appropriate and then click the <b>Run</b> button to start the Abaqus solver.
The solver will use default values for any unset selections.
The Run button changes to a <b>Stop</b> button while the job is running.
The .log and .sta information will be displayed in the lower portion of the runAbaqus window.
If the job fails to complete then runAbaqus will find and display error messages from the .dat and .msg files.

![image](https://github.com/user-attachments/assets/ca477e6f-2d7d-4bc9-9fd7-2a073dd96155)
