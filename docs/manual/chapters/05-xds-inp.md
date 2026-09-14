# Setting up XDS.INP

**Goal:** a complete, correct `XDS.INP` for your data set in the project folder, in a few minutes.

`XDS.INP` tells XDS where the frames are, how the detector and the beam are set up, and how to process. CrystalPilot can write most of it from the frame headers; you then review and adjust in a form or in the raw text.

## Way 1: generate it from the images (recommended)

1. Open the **Data Processing** tab, sub-tab **Key Parameters**.
2. In **NAME_TEMPLATE_OF_DATA_FRAMES** type the path of the frames as an XDS template, for example `/data/lyso/lyso_1_??????.h5`, or click the folder button next to it and pick **any frame** of the series: the name is converted to the template for you. For Eiger data you can pick the `_master.h5`, a `_data_000001.h5` chunk or the template; CrystalPilot resolves all three to the master file.

![The Key Parameters form; the template field and its browse button are marked.](images/05-01-key-parameters.png)

3. Click **⚡ Generate from images**. The frame header is read (CBF mini-header, HDF5/NeXus, SMV, R-AXIS): detector type and size, pixel size, beam centre, distance, wavelength, oscillation, frame count. For Eiger files the count-rate cut-off becomes `OVERLOAD=`, the sensor thickness is written, and the `LIB=` line pointing at the neggia reader is added automatically. The generated file is saved to the project immediately and the form is filled from it.

![Generate from images writes a complete XDS.INP from the headers.](images/05-02-generate.png)

4. Check the warnings printed at the top of the generated file (also shown as a message): a missing wavelength or oscillation range must be typed by hand; the beam centre defaults to the detector centre when the header has none.

## Way 2: import an existing XDS.INP

- **⟳ Load from XDS.INP** reads the file already in the project into the form.
- **📂 Load from other XDS.INP…** imports the parameters of any XDS.INP, for example from a beamline auto-processing run. This fills the form only; press **💾 Save Parameters** to write them to the project.

## Way 3: the form

Type or change values in the groups (experiment, detector, indexing, corrections, reporting). Two things to know:

- **Active / Commented toggles.** SPACE_GROUP_NUMBER, UNIT_CELL_CONSTANTS, SIGNAL_PIXEL, EXCLUDE_DATA_RANGE and several correction keywords have a toggle. *Commented* writes the line with a leading `!`: the value is kept in the file but XDS ignores it. Leave the space group commented (or 0) to let XDS decide the symmetry in CORRECT; set it once you know it.
- **⟲ Cell & space group from IDXREF** opens the lattice table of the latest IDXREF run so you can pick a Bravais lattice with one click (chapter 6).

![Toggles next to the space group and cell fields, and the button that fills them from IDXREF.](images/05-03-toggles.png)

Click **💾 Save Parameters** to write the form to `XDS.INP`. Only the keywords you changed are rewritten: lines that carry several keywords (`NX= 4150 NY= 4371 QX= 0.075 QY= 0.075`, common in beamline files) keep the others, trailing comments stay, and the geometry keywords (ROTATION_AXIS, INCIDENT_BEAM_DIRECTION, DIRECTION_OF_DETECTOR_X/Y-AXIS, polarization) are never touched by the form.

![Save Parameters, Load from XDS.INP and Load from other XDS.INP.](images/05-04-save.png)

## The raw file

The **Full Input File** sub-tab shows the text of `XDS.INP`. **⟳ Load / Refresh** reads it from disk, edit freely, **💾 Save File** writes it back. This is where you change keywords the form does not expose (ROTATION_AXIS for a beamline with an inverted spindle, VALUE_RANGE_FOR_TRUSTED_DETECTOR_PIXELS, UNTRUSTED_RECTANGLE, …).

![The Full Input File editor.](images/05-05-full-file.png)

## What to check before the first run

| Keyword | Typical value | Note |
|---|---|---|
| NAME_TEMPLATE_OF_DATA_FRAMES | `/path/prefix_??????.h5` or `_????.cbf` | as many `?` as digits in the frame numbers |
| DATA_RANGE, SPOT_RANGE, BACKGROUND_RANGE | `1 1800`, a wedge or two, `1 10` | SPOT_RANGE of 5–10° per wedge is enough for indexing |
| OSCILLATION_RANGE, X-RAY_WAVELENGTH, DETECTOR_DISTANCE | from the header | check them against the beamline log if the header is incomplete |
| ORGX, ORGY | beam centre in pixels | a wrong beam centre is the first suspect when indexing fails |
| ROTATION_AXIS | `1 0 0` or `-1 0 0` | beamline convention; only editable in the raw file |
| LIB | path to `dectris-neggia.so` | Eiger data only |

## If it goes wrong

- *"Wavelength not found in image header"*: type it in the form and save.
- Generated OSCILLATION_RANGE is empty: some HDF5 writers omit it; take it from the beamline log.
- The Eiger template gives an error about the master file: the `_master.h5` and all `_data_*.h5` files must be in the same folder; on Windows keep them in the projects folder for speed.
