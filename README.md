I wanted a more minimal and simplified mod swapper for Genshin Impact's 3dmigoto, so I created one.

![image](https://github.com/watanguy/ModManager/assets/30172340/f2dec927-ce35-43fc-91cf-129086dcde5c)

Installation:
You can run from anywhere, but if you put it inside the 3dmigoto main folder it will auto detect folders. 

How it works:
This software actually moves the entire selected mod out to a seperate folder when disabling that will be found here \3dmigoto\disabledMods. Re-enabling moves the mod back to the regular mod folder. I prefer this method to avoid clutter and messing with content of the files.

This only works if you have all mods in the mods folder directly. Having multiple subfolders are currently not supported. 

For this project I used: Python, PyQt5 & PyInstaller...
This website and your pc might find the file suspicious and therefore mark it as virus. False positives from antivirus software like Avast are frustrating when distributing Python applications compiled to executables. These issues often arise because PyInstaller packages the Python scripts along with a Python interpreter and all necessary libraries into a single executable, which can sometimes look suspicious to antivirus programs.
^ I'll try to fix this antivirus issue with another compiler, but for now it is what it is.
