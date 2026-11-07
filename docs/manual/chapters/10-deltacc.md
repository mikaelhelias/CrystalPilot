# Frame quality with ΔCC½ (XDSCC12)

**Goal:** find frames or batches that harm the merged data (radiation damage, ice, crystal movement) and exclude them with one click. The tab is shown at the **Expert** work mode.

`xdscc12` (Assmann, Brehm & Diederichs 2016) recomputes CC½ with each frame or batch left out. A strongly negative ΔCC½ means the data set is better without that batch.

## Get the program

The tab checks for the `xdscc12` binary. If it is missing, **⬇ Download automatically** fetches the Linux or macOS build from the University of Konstanz into your user folder and verifies that it runs. (On Windows this happens inside the Linux runtime.)

## Run

1. Open the **ΔCC½** tab after a CORRECT run.
2. Set the *batch width* (degrees of rotation per batch; 1 for a fine view, 5–10 for long data sets), the number of resolution bins and the *high resolution* limit. The limit starts at the project's cut-off (the Cutoff Preference, the same value XSCALE is filled with); beyond it, noisy shells make most frames look negative and hide the ones that really hurt. Empty the field to read every reflection. Tick the *detection strategies* to combine: **Radiation damage tail** (a progressive decline at the end of the data set), **Negative blocks** (contiguous frames with ΔCC½ below zero), **2-MAD outliers** (runs of three or more frames below median − 2 MAD) and **3-MAD severe** (adjacent pairs below median − 3 MAD).
3. Click **▶ Run ΔCC½ Analysis**. The log is kept as `XDSCC12.LP` next to the XDS output (**📄 View XDSCC12.LP** shows it); results are reloaded when you return.

![The ΔCC½ tab: binary status, options, run button and the chart with suggested exclusions.](images/10-01-deltacc.png)

## Read and apply

- The chart shows ΔCC½ per frame or batch; what the strategies found is listed under **Suggested Exclusions** with tick boxes (**Select all** / **none**).
- **Add selected to EXCLUDE_DATA_RANGE** writes the ticked suggestions as `EXCLUDE_DATA_RANGE` lines to `XDS.INP`. **Apply selected & Re-run CORRECT** does that and runs CORRECT at once, so you can compare the shell table before and after (Run History, chapter 8). Because excluded frames are removed at the CORRECT stage, no re-integration is needed.
- A range of your own: click and drag on the chart; it appears under **Selected Range** with **Add to EXCLUDE_DATA_RANGE** (writes it, no re-run) and **Clear selection**.

## What to watch

- A gentle decline of ΔCC½ towards the end is radiation damage; excluding the last batches often raises CC½ in the outer shells.
- Isolated very negative frames are usually ice, a shutter problem or a crystal jump: look at those frames in the viewer (chapter 17).
- Do not exclude more than necessary: completeness falls with every frame removed. Check completeness in the CORRECT table after applying.
- Suggestions stop at 20% of the batches, worst ranges first, and a warning appears above 10%. Ranges over the limit are named under the list: apply the others first, then run the analysis again. A suggested range can have a mean ΔCC½ above 0: it stands out from the rest of the data but still raises CC½, so untick it unless the frames themselves look wrong. AutoPilot excludes only ranges with a mean below 0.
