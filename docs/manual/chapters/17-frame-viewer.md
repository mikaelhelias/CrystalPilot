# Looking at the frames

**Goal:** see the diffraction images themselves, check the beam centre and resolution, find ice rings or shadows, and confirm that the spots XDS found are where you expect them.

## Load a frame

1. Open the **Frame Viewer** tab.
2. Type a path in the field and click **🔍 Load Frame**, browse with the folder button, or click **⟳ From XDS.INP** to take the template of the active project. Accepted: single frames (CBF, SMV/IMG, OSC, MarCCD, TIFF), an XDS template, and for Eiger data the `_master.h5`, a `_data_*.h5` chunk or the template; multi-chunk Eiger sets are navigated as one series.
3. The last path is remembered per project; **Recent** lists the last five.

![A frame loaded from the Eiger master file; the path field, From XDS.INP and Recent are marked.](images/17-01-frame-load.png)

## Navigate and adjust

- **−100 −10 −1 +1 +10 +100**, the slider, and the jump field step through the series.
- **Contrast**: the *lo%* and *hi%* percentile sliders; lower *hi%* to see weak spots, raise it to tame hot pixels. Colour maps: Grey (inverted, the default), Grey, Heat, Blues.
- **Zoom** 0.25×–8× with the slider; **🔍 Mag** opens a draggable, resizable **magnifier** inset at 0.5×, 2×, 4× or 8× (✕ closes it).

## Overlays

![Resolution rings and ice rings on the frame; the Rings, Ice, Spots and Save buttons.](images/17-02-frame-rings.png)

- **◎ Rings**: resolution rings from the geometry (wavelength, distance, pixel size, beam centre). The geometry comes from the frame header, from the project's `XDS.INP` (**↻ From Project**), from any XDS.INP (**📂 Locate XDS.INP…**, then **⚡ Read XDS.INP Geometry**) or from the px / dist / bcx / bcy fields, which you can edit. The rings tell you at a glance where your data ends.
- **❄ Ice**: dashed rings at the hexagonal ice spacings (3.90, 3.67, 3.44, 2.67, 2.25, 2.07, 1.95, 1.92, 1.88, 1.72 Å). Spots or powder rings on them mean ice in the loop; exclude those shells (EXCLUDE_RESOLUTION_RANGE) if the statistics show it.
- **⊕ Spots**: the `SPOT.XDS` overlay from the current output folder for frames inside SPOT_RANGE: indexed spots are circles, spots that were not indexed are crosses (the colours change with the colour map so that they stay visible). Many crosses in one region point to a second lattice, a shadow or ice.
- **⤓ Save**: PNG (lossless) or JPEG of the current view with the overlays, at 1× (native detector resolution), 0.5×, 0.25× or 2×, for a report.

## Header information

Below the image the **Frame header** lists the geometry read from the file: wavelength, distance, pixel size, beam centre, image size and detector name. *Generate from images* reads the same values (and, with its own reader, the oscillation and for Eiger files the count-rate cut-off and the sensor thickness); if a value here is wrong, correct it in `XDS.INP`.

![The frame header panel with the values read from the file.](images/17-03-frame-header.png)

## XDS diagnostic images (Advanced)

The *XDS diagnostics* row loads two images XDS writes into the output folder: **SHOW_SPOT** (`SHOW_SPOT.cbf` from COLSPOT: the frame at SHOW_IMAGE_NUMBER with every strong pixel marked, to check that the spot search found real reflections and not noise or ice) and **SHOW_HKL** (`SHOW_HKL.cbf` from INTEGRATE: the predicted integration regions drawn on the frame, to check that predictions sit on the spots). The other diagnostic files (BKGINIT.cbf, BLANK.cbf, GAIN.cbf, ABS.cbf, BKGPIX.cbf) can be opened like any CBF frame by typing their path.

## If it goes wrong

| Symptom | What to do |
|---|---|
| "Missing Python dependencies" banner | click **Install automatically**, or install numpy, matplotlib, h5py, hdf5plugin, fabio into the CrystalPilot Python environment |
| HDF5 frame will not load | hdf5plugin missing, or master and data files not in the same folder |
| Rings not shown | the geometry is incomplete: **From Project** or type QX, distance, wavelength, ORGX/ORGY into the override fields |
| Very slow on Windows | frames on a Windows drive are read through the WSL bridge; copy the data set into the projects folder |
