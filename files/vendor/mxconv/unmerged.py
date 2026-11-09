"""Unmerged intensities from XDS_ASCII files and unmerged MTZ files.

Needs numpy and gemmi (any version from 0.6; only the unit cell, space-group
operators and the MTZ reader are used).  Every program's output becomes the same
`Unmerged` object, so the statistics do not depend on who wrote the file.

Supported:
- XDS_ASCII with MERGE=FALSE, from XDS CORRECT or XSCALE.  Observations with a
  negative sigma (rejected by XDS) are left out and counted.
- Unmerged MTZ (with M/ISYM and BATCH), from AIMLESS, DIALS, xia2 or autoPROC;
  the intensity column is I (or IMEAN), the sigma SIGI (or SIGIMEAN).
"""
import re

import numpy as np

KEY_OFFSET = 1024          # indices up to |h| < 1024 encode into one int64 key


def frac_matrix(cell):
    """The fractionalization matrix of a cell (a, b, c, alpha, beta, gamma) as a numpy array;
    h @ frac_matrix is the scattering vector in Cartesian coordinates (works with gemmi 0.6 and 0.7)."""
    import gemmi
    uc = cell if isinstance(cell, gemmi.UnitCell) else gemmi.UnitCell(*cell)
    mat = uc.frac.mat if hasattr(uc, "frac") else uc.fractionalization_matrix
    return np.array(mat.tolist(), dtype=np.float64)


class Unmerged(object):
    """Observations of one data set.

    hkl: (n, 3) int array as measured (any setting of the symmetry equivalents)
    i, sigma: float arrays; batch: int array or None
    cell: (a, b, c, alpha, beta, gamma); space_group: gemmi.SpaceGroup
    friedel: True when the program merged Friedel mates (FRIEDEL'S_LAW=TRUE)
    """

    def __init__(self, hkl, i, sigma, cell, space_group, batch=None, friedel=True, source="", n_rejected=0):
        self.hkl = np.asarray(hkl, dtype=np.int64).reshape(-1, 3)
        self.i = np.asarray(i, dtype=np.float64)
        self.sigma = np.asarray(sigma, dtype=np.float64)
        self.batch = None if batch is None else np.asarray(batch, dtype=np.int64)
        self.cell = tuple(float(v) for v in cell)
        self.space_group = space_group
        self.friedel = friedel
        self.source = source
        self.n_rejected = n_rejected
        self._s = None

    def __len__(self):
        return len(self.i)

    def subset(self, mask):
        out = Unmerged(self.hkl[mask], self.i[mask], self.sigma[mask], self.cell, self.space_group,
                       None if self.batch is None else self.batch[mask], self.friedel, self.source)
        return out

    # ── geometry ─────────────────────────────────────────────────────────
    def reciprocal_vectors(self):
        """s = h a* + k b* + l c* in Cartesian coordinates (1/A), one row per observation."""
        if self._s is None:
            self._s = self.hkl.astype(np.float64) @ frac_matrix(self.cell)
        return self._s

    def inv_d2(self):
        s = self.reciprocal_vectors()
        return np.einsum("ij,ij->i", s, s)

    def d(self):
        return 1.0 / np.sqrt(self.inv_d2())

    # ── symmetry ─────────────────────────────────────────────────────────
    def unique_keys(self, anomalous=False):
        """An integer per observation, the same for all symmetry equivalents.

        With anomalous=False Friedel mates count as equivalent; with True they are
        kept apart, except for centric reflections, whose mates are the same
        reflection.  The key is the largest encoded index among the equivalents,
        so it does not depend on the setting the program wrote the index in.
        """
        rotations = [np.array(op.rot, dtype=np.int64) // 24 for op in self.space_group.operations().sym_ops]
        best = None
        signs = (1,) if anomalous else (1, -1)
        for rot in rotations:
            for sign in signs:
                h = sign * (self.hkl @ rot)
                key = ((h[:, 0] + KEY_OFFSET) * 2 * KEY_OFFSET + (h[:, 1] + KEY_OFFSET)) * 2 * KEY_OFFSET + (h[:, 2] + KEY_OFFSET)
                best = key if best is None else np.maximum(best, key)
        return best

    def centric(self):
        ops = self.space_group.operations()
        return np.asarray(ops.centric_flag_array(self.hkl.astype(np.int32)), dtype=bool)


# ── readers ──────────────────────────────────────────────────────────────────
def read(path):
    """An Unmerged object from an XDS_ASCII file or an unmerged MTZ file."""
    path = str(path)
    with open(path, "rb") as fh:
        head = fh.read(4)
    if head == b"MTZ ":
        return read_mtz(path)
    return read_xds_ascii(path)


def _header_value(line, key):
    m = re.search(re.escape(key) + r"=\s*(\S+)", line)
    return m.group(1) if m else None


def read_xds_ascii(path, chunk_lines=200000):
    """XDS_ASCII (MERGE=FALSE) from CORRECT or XSCALE."""
    import gemmi
    items, n_items, sg_number, cell, friedel, merged = {}, None, None, None, True, False
    rows = []
    with open(str(path), "r", errors="replace") as fh:
        for line in fh:
            if not line.startswith("!"):
                break_line = line
                break
            if line.startswith("!FORMAT="):
                merged = (_header_value(line, "MERGE") or "FALSE").upper() == "TRUE"
                friedel = (_header_value(line, "FRIEDEL'S_LAW") or "TRUE").upper() == "TRUE"
            elif line.startswith("!SPACE_GROUP_NUMBER="):
                sg_number = int(line.split("=")[1])
            elif line.startswith("!UNIT_CELL_CONSTANTS="):
                cell = [float(v) for v in line.split("=")[1].split()[:6]]
            elif line.startswith("!NUMBER_OF_ITEMS_IN_EACH_DATA_RECORD="):
                n_items = int(line.split("=")[1])
            elif line.startswith("!ITEM_"):
                name, _, col = line[6:].partition("=")
                items[name.strip()] = int(col) - 1
            elif line.startswith("!END_OF_HEADER"):
                break_line = None
                break
        else:
            break_line = None
        if merged:
            raise ValueError(str(path) + " holds merged data (MERGE=TRUE); unmerged observations are needed")
        if not (n_items and sg_number and cell and {"H", "K", "L", "IOBS", "SIGMA(IOBS)"} <= set(items)):
            raise ValueError(str(path) + " is not an XDS_ASCII file with H, K, L, IOBS and SIGMA(IOBS)")
        pending = [] if break_line is None else [break_line]

        def flush(lines):
            text = "".join(l for l in lines if not l.startswith("!"))
            if text.strip():
                values = np.fromstring(text, dtype=np.float64, sep=" ")
                rows.append(values.reshape(-1, n_items))

        for line in fh:
            pending.append(line)
            if len(pending) >= chunk_lines:
                flush(pending)
                pending = []
        flush(pending)
    data = np.concatenate(rows) if rows else np.zeros((0, n_items))
    sigma = data[:, items["SIGMA(IOBS)"]]
    keep = sigma > 0
    data = data[keep]
    batch = data[:, items["ZD"]] if "ZD" in items else None
    if batch is not None:
        batch = np.ceil(batch).astype(np.int64)
    hkl = data[:, [items["H"], items["K"], items["L"]]].astype(np.int64)
    return Unmerged(hkl, data[:, items["IOBS"]], data[:, items["SIGMA(IOBS)"]], cell,
                    gemmi.find_spacegroup_by_number(sg_number), batch, friedel, "XDS_ASCII",
                    int(np.sum(~keep)))


def read_mtz(path, i_label=None, sigma_label=None):
    """Unmerged MTZ (AIMLESS, DIALS, xia2, autoPROC): indices as measured are restored
    from M/ISYM."""
    import gemmi
    mtz = gemmi.read_mtz_file(str(path))
    labels = mtz.column_labels()
    if "M/ISYM" not in labels:
        raise ValueError(str(path) + " is a merged MTZ file (no M/ISYM column); unmerged observations are needed")
    i_label = i_label or next((l for l in ("I", "IMEAN", "IPR") if l in labels), None)
    sigma_label = sigma_label or {"I": "SIGI", "IMEAN": "SIGIMEAN", "IPR": "SIGIPR"}.get(i_label)
    if not i_label or sigma_label not in labels:
        raise ValueError(str(path) + " has no intensity and sigma columns")
    mtz.switch_to_original_hkl()
    data = np.array(mtz, copy=False)
    col = {l: labels.index(l) for l in labels}
    sigma = data[:, col[sigma_label]].astype(np.float64)
    keep = np.isfinite(sigma) & (sigma > 0) & np.isfinite(data[:, col[i_label]])
    data = data[keep]
    hkl = data[:, [col["H"], col["K"], col["L"]]].astype(np.int64)
    batch = data[:, col["BATCH"]].astype(np.int64) if "BATCH" in col else None
    cell = mtz.cell
    return Unmerged(hkl, data[:, col[i_label]], data[:, col[sigma_label]],
                    (cell.a, cell.b, cell.c, cell.alpha, cell.beta, cell.gamma), mtz.spacegroup, batch,
                    True, "MTZ", int(np.sum(~keep)))
