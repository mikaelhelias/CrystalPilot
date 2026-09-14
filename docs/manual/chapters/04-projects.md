# Projects

**Goal:** one folder per data set that holds the input files you edit, the results, and the memory of where things ran.

## Create a project

1. In the sidebar, type a name in **Project name** (spaces are allowed; no `/` or `\`). Optionally add a description and the data path of the frames.
2. Click **＋ Create Project**. The project opens at once and appears in the **Projects** list.

![New project: name and description filled in, the Create button.](images/04-01-create-project.png)

## Open, switch, delete

- Click a project in the **Projects** list to make it the active one. Drag a project up or down to change the order of the list (the order is remembered by the browser); **↻ Refresh** re-reads the folder. Every tab (parameters, runs, results, XSCALE, POINTLESS, …) works on the active project; its name is shown in the header.
- **✕** removes a project from the list only: its folder and results stay on disk (the entry can be recreated by making a project with the same name).
- **🗑** deletes the folder with everything in it. There is no undo.

![An open project: the list on the left, the name in the header, the Data Processing tab.](images/04-02-project-open.png)

## Where the files are

Every project is a folder under the projects folder (chosen at installation; `~/crystalpilot/projects` on Linux, inside the Linux runtime on Windows).

- **Input files you edit** live in the project folder: `XDS.INP`, `XSCALE.INP`, `XDSCONV.INP`.
- **Results** live in the *folder where the program last ran*: the project folder itself, a run folder you typed (it may be anywhere, for example next to the frames), or a numbered sub-folder. CrystalPilot remembers that folder per program in `metadata.json`, and every viewer, comparison and downstream step reads from there. You never have to tell the LP viewer or POINTLESS where CORRECT ran.
- Previous CORRECT, IDXREF and XSCALE logs are kept as `.prev1` … `.prev4` next to the current one, which is what *Run History* compares.

The status line under the run-folder field shows the current output folder (on Windows also as `P:\Projects\...` or `\\wsl.localhost\...`). **Open folder** next to the project name and **Open** next to the run folder open the corresponding folder in your file manager.

![Open folder next to the project name and the output-folder status line.](images/04-03-open-folder.png)

> On Windows the projects also appear as the drive letter chosen at installation (`P:\Projects\` by default), as the *CrystalPilot Projects* desktop shortcut and as a Quick Access entry in Explorer. Copy your frames into a project folder from there when you want the fastest processing.

## What the project remembers

`metadata.json` in the project folder keeps the description and data path, the completed steps, the last XDS, XSCALE and XDSCONV run folders, and the last image opened in the frame viewer. It is safe to copy a project folder elsewhere; the run-folder memory is rewritten at the next run.

## Packing a project into one file

**⤓ Export (.zip)** next to the project name packs the whole result into one archive: the input files, every program log, the parsed reports, the figures, the refined geometry and the reflection files, taken from the project folder and from every run folder the project has written to, with a `README.txt` naming the program, the project and the day.

It leaves out what a reader does not need and what makes a project folder large: the frames, the `*-CORRECTIONS.cbf` images XDS rewrites on every run, `SPOT.XDS`, and the rotated copies of older logs. If only the numbers need to travel, the message links a second pass without the reflection files.

The archive is written next to the project, so it is also there in Explorer, and the message offers it as a download.
