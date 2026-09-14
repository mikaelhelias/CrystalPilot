_META_LOCK = threading.RLock()   # metadata.json is edited from request and stream threads


class ProjectManager:
    """Project operations"""

    @staticmethod
    def _safe_name(name):
        """Validate project name to prevent path traversal."""
        if not isinstance(name, str) or not name.strip() or "/" in name or "\\" in name or name in (".", "..") or "\0" in name:
            raise ValueError(f"Invalid project name: {name!r}")
        # Verify resolved path stays within PROJECTS_DIR
        root = PROJECTS_DIR.resolve()
        resolved = (PROJECTS_DIR / name).resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"Invalid project name: {name!r}")
        return name

    @staticmethod
    def _write_meta(meta_path, metadata):
        """Write metadata.json atomically (temp file + rename) so a crash or a
        concurrent reader never sees a half-written file."""
        tmp = meta_path.with_name(meta_path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        os.replace(str(tmp), str(meta_path))

    @staticmethod
    def create(name, description="", data_path=""):
        name = ProjectManager._safe_name(name)
        project_dir = PROJECTS_DIR / name
        with _META_LOCK:
            if project_dir.exists():
                raise ValueError("Project already exists")
            project_dir.mkdir()
            metadata = {
                "name": name,
                "description": description,
                "data_path": data_path,
                "created_at": datetime.now().isoformat(),
                "completed_steps": []
            }
            ProjectManager._write_meta(project_dir / "metadata.json", metadata)
        return metadata

    @staticmethod
    def list_all():
        """All projects with a readable metadata.json.  A damaged file is
        reported on the console and skipped instead of hiding every project."""
        projects = []
        for p in sorted(PROJECTS_DIR.iterdir()):
            if not p.is_dir():
                continue
            meta = p / "metadata.json"
            if not meta.exists():
                continue
            try:
                with _META_LOCK:
                    with open(meta, encoding="utf-8") as f:
                        data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("name", p.name)
                    projects.append(data)
            except Exception as e:
                try:
                    print(f"[projects] skipping {meta}: {e}")
                except Exception:
                    pass
        return projects

    @staticmethod
    def get(name):
        name = ProjectManager._safe_name(name)
        meta = PROJECTS_DIR / name / "metadata.json"
        if not meta.exists():
            raise FileNotFoundError("Project not found")
        with _META_LOCK:
            with open(meta, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise RuntimeError("Project metadata must contain a JSON object: " + str(meta))
            return data

    @staticmethod
    def invalidate_steps(name, step):
        """A rerun invalidates this step and all outputs that depend on it."""
        invalid = set(XDS_PIPELINE[XDS_PIPELINE.index(step):])
        with _META_LOCK:
            metadata = ProjectManager.get(name)
            completed = metadata.get("completed_steps", [])
            ProjectManager.update(name, {"completed_steps": [s for s in completed if s not in invalid]})

    @staticmethod
    def update(name, data):
        """Merge `data` into metadata.json under a lock (read-modify-write)."""
        name = ProjectManager._safe_name(name)
        meta = PROJECTS_DIR / name / "metadata.json"
        with _META_LOCK:
            with open(meta, encoding="utf-8") as f:
                metadata = json.load(f)
            metadata.update(data)
            metadata["last_modified"] = datetime.now().isoformat()
            ProjectManager._write_meta(meta, metadata)

    @staticmethod
    def delete(name, delete_files=True):
        name = ProjectManager._safe_name(name)
        project_dir = PROJECTS_DIR / name
        with _directory_reservation([project_dir]), _META_LOCK:
            if project_dir.exists():
                if delete_files:
                    shutil.rmtree(project_dir)
                else:
                    # Remove only the metadata file so it disappears from the project list
                    meta = project_dir / "metadata.json"
                    if meta.exists():
                        meta.unlink()

