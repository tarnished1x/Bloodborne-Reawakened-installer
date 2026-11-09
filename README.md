[README_EN.txt](https://github.com/user-attachments/files/34563523/README_EN.txt)
BLOODBORNE: REAWAKENED — INSTALLER v1.0
=======================================

WHAT YOU HAVE
-------------
An English Windows GUI installer built on the tested v0.4 patch format:
  - SHA-256 verification of the player's unchanged original files
  - xdelta3 patch application
  - extra-asset copying (from the v0.4 extras section)
  - SHA-256 verification of every installed file
  - safe, separate output folder with temporary staging
  - progress bar, live log and readable errors

IMPORTANT: This download contains the GUI and installer engine ONLY.
Your actual generated patch package is on YOUR PC and is NOT contained here.
The installer cannot install Reawakened until the package has been added.

FOR YOU, THE MOD AUTHOR
-----------------------
1. Extract this ZIP into C:\Reawakened_Installer (or anywhere you like).
2. Copy the CONTENTS of your finished
     C:\Reawakened_Release_Patches_v04_Approved
   into:
     C:\Reawakened_Installer\patch_package
   Make sure the following exists:
     C:\Reawakened_Installer\patch_package\manifest.json
   The subfolders patches\ and extras\ must be preserved.
3. Copy your working Windows xdelta3.exe into C:\Reawakened_Installer\
4. If you have Python with Tkinter installed, double-click START_INSTALLER.bat.
5. To create a standalone Windows executable, double-click BUILD_WINDOWS_EXE.bat
   on your Windows PC with an internet connection. It installs PyInstaller and
   produces RELEASE\Reawakened_Installer.exe. You cannot build a Windows EXE by
   running Linux PyInstaller; this needs to be done on Windows.
6. Before sharing, check permission to redistribute ALL included extras, music,
   images and any other third-party assets. xdelta patches still require review
   for third-party copyrighted content.

FOR PLAYERS
-----------
Your distributable RELEASE folder should look like:
  Reawakened_Installer.exe
  xdelta3.exe
  patch_package\
    manifest.json
    patches\ ...
    extras\ ...

To install:
  1. Run Reawakened_Installer.exe.
  2. Select your clean game folder (the directory containing dvdroot_ps4;
     selecting dvdroot_ps4 itself is also supported).
  3. Confirm the patch_package folder containing manifest.json.
  4. Select a NEW, NON-EXISTING destination folder outside the clean game files.
  5. Select xdelta3.exe. If located next to the EXE, it is preselected.
  6. Click INSTALL REAWAKENED and wait until the success message appears.
  7. Activate the generated dvdroot_ps4 mod directory using Lantern Engine.

The game installation and clean files are never modified by this tool. The output
folder can be used as the contents of a separate Lantern mod. Do NOT select
an existing mod folder for installation. Do NOT put the output inside the clean
originals folder. Keep your backups.

KNOWN LIMITATIONS
-----------------
- The GUI has been tested with synthetic files, NOT with your full real game
  package or as a Windows .exe; a real package test and Windows build remain.
- The installer requires your generated v0.4 manifest, all patches and extras,
  and a working xdelta3.exe.
- Existing target folders are deliberately rejected to prevent overwriting.
- The patched mod output contains only the paths present in the manifest,
  not a full copy of the game. Unchanged game files are read from the originals.
- This is a patcher, not a license or authorization to redistribute other works.
