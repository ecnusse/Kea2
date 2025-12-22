#!/usr/bin/env python3
"""
FBM merger tool

This script provides a single responsibility: merge two FBM files into a new FBM file
that preserves the original FlatBuffers schema generated under the `fastbotx` package.

Usage:
  python fbm_parser.py --merge a.fbm b.fbm -o out.fbm

Notes:
- Requires the `flatbuffers` runtime and generated Python modules under `fastbotx/`.
- The merger concatenates ReuseEntry objects from the first file then the second.
"""

import os
import threading
import uuid
from .fs_lock import FileLock, LockTimeoutError

STORAGE_PREFIX = "/sdcard/fastbot_"

# Ensure working directory is the script directory so relative imports for generated code work
script_dir = os.path.dirname(os.path.abspath(__file__))


class FBMMerger:
    """Class encapsulating FBM merge functionality.

    Public methods:
    - merge(file_a, file_b, out_file): merge two FBM files into out_file.
    """

    def __init__(self):
        self.script_dir = script_dir
        # internal map: action_hash (int) -> { activity_str: times }
        self._reuse_model_lock = threading.Lock()
        self._reuse_model = {}  # dict: int -> dict(activity->times)
        self._model_save_path = ""
        self._default_model_save_path = ""

        # Prepare PC-side FBM directory under project configs/merge_fbm (or cwd fallback)
        try:
            from pathlib import Path
            pc_dir = self._pc_fbm_dir()
            # ensure Path object
            pc_dir = Path(pc_dir)
            pc_dir.mkdir(parents=True, exist_ok=True)
            self._pc_dir = pc_dir
        except Exception:
            # best-effort: if directory creation fails, keep attribute None
            self._pc_dir = None

    def check_dependencies(self):
        try:
            import flatbuffers  # noqa: F401
            return True
        except Exception:
            print("Error: 'flatbuffers' runtime not installed. Run: pip install flatbuffers")
            return False

    def check_generated_code(self):
        """Check that the expected generated modules exist under fastbotx/"""
        required = [
            os.path.join(self.script_dir, "fastbotx", "__init__.py"),
            os.path.join(self.script_dir, "fastbotx", "ReuseModel.py"),
            os.path.join(self.script_dir, "fastbotx", "ReuseEntry.py"),
            os.path.join(self.script_dir, "fastbotx", "ActivityTimes.py"),
        ]
        missing = [p for p in required if not os.path.exists(p)]
        if missing:
            print("Error: Missing generated FlatBuffers Python files:")
            for p in missing:
                print("  - ", p)
            return False
        return True

    def _ensure_fbm_suffix(self, path: str, param_name: str = 'file') -> bool:
        """Ensure the path ends with .fbm (case-insensitive). Print error and return False otherwise."""
        if not path:
            print(f"Error: {param_name} path is empty")
            return False
        if not str(path).lower().endswith('.fbm'):
            print(f"Error: expected .fbm file for {param_name}: '{path}'")
            return False
        return True

    def load_model(self, file_path):
        """Load and return ReuseModel root object from a FBM file.

        Returns the model object on success, or None on failure.
        """
        # suffix check
        if not self._ensure_fbm_suffix(file_path, 'file_path'):
            return None

        try:
            from .fastbotx.ReuseModel import ReuseModel
        except Exception as e:
            print("Error importing fastbotx.ReuseModel:", e)
            return None

        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            model = ReuseModel.GetRootAs(data, 0)
            return model
        except Exception as e:
            print(f"Error reading/parsing FBM file {file_path}: {e}")
            return None

    def load_reuse_model(self, package_name: str):
        """Load a FBM file according to package name and populate internal reuse map.

        Behavior follows the C++ example: compute path STORAGE_PREFIX + package + ".fbm",
        set internal default paths, read binary, parse ReuseModel and convert into
        self._reuse_model as a mapping actionHash -> {activity: times}.
        """
        if not package_name:
            print("Error: package_name required")
            return False

        model_file_path = STORAGE_PREFIX + package_name + ".fbm"
        self._model_save_path = model_file_path
        if self._model_save_path:
            self._default_model_save_path = STORAGE_PREFIX + package_name + ".tmp.fbm"

        print(f"Begin load model: {model_file_path}")

        if not os.path.exists(model_file_path):
            print(f"Read model file {model_file_path} failed, check if file exists!")
            return False

        try:
            with open(model_file_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            print(f"Failed to read file {model_file_path}: {e}")
            return False

        # parse using generated ReuseModel
        try:
            import importlib
            ReuseModel_mod = importlib.import_module('kea2.fastbotx.ReuseModel')
            ReuseEntry_mod = importlib.import_module('kea2.fastbotx.ReuseEntry')
            ActivityTimes_mod = importlib.import_module('kea2.fastbotx.ActivityTimes')
        except Exception as e:
            print("Error importing fastbotx generated modules:", e)
            return False

        try:
            reuse_fb_model = ReuseModel_mod.ReuseModel.GetRootAs(data, 0)
        except Exception as e:
            print("Error parsing FBM data:", e)
            return False

        # build map
        new_map = {}
        total = 0
        try:
            length = reuse_fb_model.ModelLength()
        except Exception:
            length = 0

        for i in range(length):
            entry = reuse_fb_model.Model(i)
            if not entry:
                continue
            action_hash = entry.Action()
            tcount = 0
            try:
                tcount = entry.TargetsLength()
            except Exception:
                tcount = 0

            entry_dict = {}
            for j in range(tcount):
                target = entry.Targets(j)
                if not target:
                    continue
                try:
                    activity = target.Activity()
                except Exception:
                    activity = None
                try:
                    times = int(target.Times())
                except Exception:
                    times = 0
                if activity:
                    # convert to native str
                    entry_dict[activity] = times

            if entry_dict:
                new_map[int(action_hash)] = entry_dict
                total += 1

        # atomically replace internal map under lock
        with self._reuse_model_lock:
            self._reuse_model.clear()
            self._reuse_model.update(new_map)

        print(f"Loaded model contains actions: {len(self._reuse_model)} (entries processed: {total})")
        return True

    def extract_entries(self, model):
        """Extract entries from a ReuseModel into Python structures: list of (action_hash, [(activity, times), ...])"""
        entries = []
        try:
            count = model.ModelLength()
        except Exception:
            # If the model API differs, return empty
            return entries

        for i in range(count):
            entry = model.Model(i)
            if not entry:
                continue
            action = entry.Action()
            targets = []
            try:
                tcount = entry.TargetsLength()
            except Exception:
                tcount = 0
            for j in range(tcount):
                t = entry.Targets(j)
                if not t:
                    continue
                try:
                    activity = t.Activity()
                except Exception:
                    activity = None
                try:
                    times = t.Times()
                except Exception:
                    times = 0
                targets.append((activity, times))
            entries.append((action, targets))
        return entries

    def merge(self, file_a, file_b, out_file, merge_mode='sum', debug=False):
        """Merge two FBM files into out_file. Returns True on success."""
        # suffix checks
        if not self._ensure_fbm_suffix(file_a, 'file_a'):
            return False
        if not self._ensure_fbm_suffix(file_b, 'file_b'):
            return False
        if out_file and not self._ensure_fbm_suffix(out_file, 'out_file'):
            return False

        if not os.path.exists(file_a):
            print(f"Error: file not found: {file_a}")
            return False
        if not os.path.exists(file_b):
            print(f"Error: file not found: {file_b}")
            return False

        if not self.check_dependencies():
            return False
        if not self.check_generated_code():
            return False

        # Load models
        model_a = self.load_model(file_a)
        if model_a is None:
            print(f"Failed to load model from {file_a}")
            return False
        model_b = self.load_model(file_b)
        if model_b is None:
            print(f"Failed to load model from {file_b}")
            return False

        # Extract entries from both models
        entries_a = self.extract_entries(model_a)
        entries_b = self.extract_entries(model_b)

        # Aggregate by action hash. For each action, merge targets by activity summing times.
        aggregated = {}  # action_hash -> { activity_str -> total_times }

        # use refactored accumulate helper; honor debug flag
        self._accumulate_entries(entries_a, aggregated, merge_mode=merge_mode, debug=debug)
        self._accumulate_entries(entries_b, aggregated, merge_mode=merge_mode, debug=debug)
        total_actions = len(aggregated)
        print(f"Merging: {len(entries_a)} entries from {file_a} + {len(entries_b)} entries from {file_b} -> {total_actions} unique actions")

        # Build new FlatBuffer and save
        return self._write_aggregated_to_file(aggregated, out_file)

    def _accumulate_entries(self, entries, aggregated, merge_mode='sum', debug=False):
        """Accumulate entries into aggregated map.

        entries: iterable of (action_hash, [(activity, times), ...])
        aggregated: dict to update
        merge_mode: 'sum' or 'max'
        debug: if True, print detailed per-action logs
        """
        for action_hash, targets in entries:
            ah = int(action_hash)
            if ah not in aggregated:
                aggregated[ah] = {}
            for activity, times in targets:
                if not activity:
                    continue
                try:
                    t = int(times)
                except Exception:
                    t = 0
                old = aggregated[ah].get(activity, 0)
                if merge_mode == 'max':
                    new = max(old, t)
                else:
                    new = old + t
                aggregated[ah][activity] = new
                if debug:
                    print(f"FBM_ACCUM DEBUG action={ah} activity='{activity}' old={old} add={t} new={new}")

    def _write_aggregated_to_file(self, aggregated, out_file):
        """Construct a FlatBuffer from aggregated map and save to out_file.

        aggregated: dict[action_hash]->{activity: times}
        out_file: path to write (if None, default path under pc_dir)
        """
        try:
            import flatbuffers
            import importlib
            ReuseModel_mod = importlib.import_module('kea2.fastbotx.ReuseModel')
            ReuseEntry_mod = importlib.import_module('kea2.fastbotx.ReuseEntry')
            ActivityTimes_mod = importlib.import_module('kea2.fastbotx.ActivityTimes')
        except Exception as e:
            print("Error importing required generated modules:", e)
            return False

        builder = flatbuffers.Builder(1024)
        str_cache = {}

        def cache_string(s):
            if s is None:
                return 0
            if s in str_cache:
                return str_cache[s]
            off = builder.CreateString(s)
            str_cache[s] = off
            return off

        entry_offsets = []

        # Ensure module objects (in case import returned a class due to package-level imports)
        import inspect
        import importlib as _importlib

        def _ensure_mod(obj):
            # if someone passed the class object (ActivityTimes), load the module that defines it
            if inspect.isclass(obj):
                return _importlib.import_module(obj.__module__)
            return obj

        ReuseEntry_mod = _ensure_mod(ReuseEntry_mod)
        ActivityTimes_mod = _ensure_mod(ActivityTimes_mod)
        ReuseModel_mod = _ensure_mod(ReuseModel_mod)

        # Build entries from aggregated map. Sort actions for deterministic output.
        for action_hash in sorted(aggregated.keys()):
            targets_map = aggregated[action_hash]
            # Build ActivityTimes offsets for each activity. Sort activities for determinism.
            target_offsets = []
            for activity in sorted(targets_map.keys()):
                times = targets_map[activity]
                act_off = cache_string(activity)
                # Compatibility: prefer module-level helper names but support both deprecated and new names
                if hasattr(ActivityTimes_mod, 'ActivityTimesStart'):
                    ActivityTimes_mod.ActivityTimesStart(builder)
                elif hasattr(ActivityTimes_mod, 'Start'):
                    ActivityTimes_mod.Start(builder)
                else:
                    raise RuntimeError('ActivityTimes builder start function not found')

                if act_off:
                    if hasattr(ActivityTimes_mod, 'ActivityTimesAddActivity'):
                        ActivityTimes_mod.ActivityTimesAddActivity(builder, act_off)
                    elif hasattr(ActivityTimes_mod, 'AddActivity'):
                        ActivityTimes_mod.AddActivity(builder, act_off)
                    else:
                        raise RuntimeError('ActivityTimes add activity function not found')

                if hasattr(ActivityTimes_mod, 'ActivityTimesAddTimes'):
                    ActivityTimes_mod.ActivityTimesAddTimes(builder, int(times))
                elif hasattr(ActivityTimes_mod, 'AddTimes'):
                    ActivityTimes_mod.AddTimes(builder, int(times))
                else:
                    raise RuntimeError('ActivityTimes add times function not found')

                if hasattr(ActivityTimes_mod, 'ActivityTimesEnd'):
                    toff = ActivityTimes_mod.ActivityTimesEnd(builder)
                elif hasattr(ActivityTimes_mod, 'End'):
                    toff = ActivityTimes_mod.End(builder)
                else:
                    raise RuntimeError('ActivityTimes end function not found')

                target_offsets.append(toff)

            # create vector of targets
            if target_offsets:
                if hasattr(ReuseEntry_mod, 'ReuseEntryStartTargetsVector'):
                    ReuseEntry_mod.ReuseEntryStartTargetsVector(builder, len(target_offsets))
                elif hasattr(ReuseEntry_mod, 'StartTargetsVector'):
                    ReuseEntry_mod.StartTargetsVector(builder, len(target_offsets))
                else:
                    raise RuntimeError('ReuseEntry start targets vector function not found')
                for toff in reversed(target_offsets):
                    builder.PrependUOffsetTRelative(toff)
                targets_vec = builder.EndVector()
            else:
                targets_vec = 0

            # create entry using module helpers
            if hasattr(ReuseEntry_mod, 'ReuseEntryStart'):
                ReuseEntry_mod.ReuseEntryStart(builder)
            elif hasattr(ReuseEntry_mod, 'Start'):
                ReuseEntry_mod.Start(builder)
            else:
                raise RuntimeError('ReuseEntry start function not found')
            try:
                if hasattr(ReuseEntry_mod, 'ReuseEntryAddAction'):
                    ReuseEntry_mod.ReuseEntryAddAction(builder, action_hash)
                elif hasattr(ReuseEntry_mod, 'AddAction'):
                    ReuseEntry_mod.AddAction(builder, action_hash)
            except Exception:
                pass
            if targets_vec:
                try:
                    if hasattr(ReuseEntry_mod, 'ReuseEntryAddTargets'):
                        ReuseEntry_mod.ReuseEntryAddTargets(builder, targets_vec)
                    elif hasattr(ReuseEntry_mod, 'AddTargets'):
                        ReuseEntry_mod.AddTargets(builder, targets_vec)
                except Exception:
                    pass
            if hasattr(ReuseEntry_mod, 'ReuseEntryEnd'):
                entry_off = ReuseEntry_mod.ReuseEntryEnd(builder)
            elif hasattr(ReuseEntry_mod, 'End'):
                entry_off = ReuseEntry_mod.End(builder)
            else:
                raise RuntimeError('ReuseEntry end function not found')
            entry_offsets.append(entry_off)

        # model vector
        if entry_offsets:
            ReuseModel_mod.ReuseModelStartModelVector(builder, len(entry_offsets))
            for eoff in reversed(entry_offsets):
                builder.PrependUOffsetTRelative(eoff)
            model_vec = builder.EndVector()
        else:
            model_vec = 0

        ReuseModel_mod.ReuseModelStart(builder)
        if model_vec:
            try:
                ReuseModel_mod.ReuseModelAddModel(builder, model_vec)
            except Exception:
                try:
                    ReuseModel_mod.AddModel(builder, model_vec)
                except Exception:
                    pass
        root = ReuseModel_mod.ReuseModelEnd(builder)
        # Use helper to finish builder and save atomically
        return self._save_builder_to_file(builder, root, out_file)

    def _save_builder_to_file(self, builder, root_offset, out_file):
        """Finish the FlatBuffer builder and save bytes to out_file atomically.

        Behavior mirrors the provided C++ example: finish the builder, write to a temporary
        file and then move/replace into the final path. If out_file is empty, use a
        default path under the script directory.
        """
        import os
        import tempfile
        tmp_path = None
        try:
            # Ensure output path
            if not out_file:
                out_file = os.path.join(self._pc_dir, 'fastbot.model.fbm')

            # Finish builder (if not already finished)
            try:
                builder.Finish(root_offset)
            except Exception:
                # If Finish was already called upstream, ignore
                pass

            buf = builder.Output()

            out_dir = os.path.dirname(out_file) or self._pc_dir
            os.makedirs(out_dir, exist_ok=True)

            # Write to a unique temporary file in the target directory and atomically replace
            fd, tmp_path = tempfile.mkstemp(prefix='.tmp_fbm_', dir=out_dir)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(buf)
                    try:
                        f.flush()
                        os.fsync(f.fileno())
                    except Exception:
                        # flush/fsync best-effort
                        pass

                # Atomic replace; try os.replace first, then os.rename as fallback
                try:
                    os.replace(tmp_path, out_file)
                except Exception:
                    try:
                        os.rename(tmp_path, out_file)
                    except Exception:
                        # last-resort: write directly to out_file
                        try:
                            with open(out_file, 'wb') as f:
                                f.write(buf)
                        except Exception:
                            # if even that fails, attempt to cleanup tmp_path below
                            pass
            finally:
                # best-effort cleanup of tmp_path if it still exists
                try:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

            # Set file permissions to 644
            try:
                # Check if it's Windows system
                if os.name == 'nt':
                    # Directly use icacls command to set permissions on Windows
                    import subprocess
                    # First disable inheritance and copy existing permissions, then set new permissions
                    subprocess.run(["icacls", out_file, "/inheritance:d", "/grant", "Everyone:R", "/grant", "Administrators:F"], 
                                  capture_output=True, text=True, check=True)
                    print(f"Set Windows file permissions to simulate 644 for: {out_file}")
                else:
                    # Set permissions directly on Unix/Linux systems
                    os.chmod(out_file, 0o644)
                    print(f"Set file permissions to 644 for: {out_file}")
            except Exception as e:
                print(f"Warning: Failed to set file permissions for {out_file}: {e}")
            
            print(f"Merged FBM written to: {out_file} (size {len(buf)} bytes)")
            return True
        except Exception as e:
            print("Error writing merged FBM:", e)
            # cleanup tmp if exists
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _pc_fbm_dir(self):
        """Return PC directory to store fbm files.
        """
        from pathlib import Path
        try:
            from .utils import getProjectRoot
            proj_root = getProjectRoot()
        except Exception:
            proj_root = None

        if proj_root:
            return Path(proj_root) / 'configs' / 'merge_fbm'
        else:
            return Path.cwd() / 'configs' / 'merge_fbm'

    def _remote_fbm_path(self, package_name: str) -> str:
        return f"/sdcard/fastbot_{package_name}.fbm"


    def pull_and_merge_to_pc(self, package_name: str, device: str = None, transport_id: str = None):
        """Pull device FBM for package and merge it into PC fbm (PC file will be updated).

        Returns True on success (or if nothing to do), False on failure.
        """
        try:
            from kea2.adbUtils import pull_file
        except Exception:
            try:
                from adbUtils import pull_file  # type: ignore
            except Exception as e:
                print("ADB utilities not available:", e)
                return False

        pc_dir = self._pc_dir
        pc_dir.mkdir(parents=True, exist_ok=True)
        pc_file = pc_dir / f"fastbot_{package_name}.fbm"
        # generate a short random suffix for all intermediate files to avoid clashes between processes
        rand = uuid.uuid4().hex[:8]
        pulled_tmp = pc_dir / f"fastbot_{package_name}.from_device.{rand}.fbm"
        merged_tmp = pc_dir / f"fastbot_{package_name}.merged.{rand}.fbm"

        remote = self._remote_fbm_path(package_name)
        try:
            print(f"Attempting to pull {remote} to {pulled_tmp}")
            pull_file(remote, str(pulled_tmp), device=device, transport_id=transport_id)
        except Exception as e:
            print(f"pull_file failed for {remote}: {e}")

        if not pulled_tmp.exists() or pulled_tmp.stat().st_size == 0:
            print(f"No FBM on device for {package_name}, nothing merged to PC.")
            try:
                if pulled_tmp.exists():
                    pulled_tmp.unlink()
            except Exception:
                pass
            return False

        # --- Try snapshot/delta workflow first ---
        snapshot_remote = f"/sdcard/fastbot_{package_name}.snapshot.fbm"
        pulled_snap_tmp = pc_dir / f"fastbot_{package_name}.snapshot.from_device.{rand}.fbm"
        delta_tmp = pc_dir / f"fastbot_{package_name}.delta.{rand}.fbm"
        try:
            # attempt to pull snapshot (may fail silently)
            try:
                pull_file(snapshot_remote, str(pulled_snap_tmp), device=device, transport_id=transport_id)
            except Exception:
                # snapshot may not exist on device; ignore error and proceed (treat as empty)
                pass

            # Compute delta using snapshot if it exists, otherwise treat snapshot as empty (delta == current)
            snapshot_path = str(pulled_snap_tmp) if pulled_snap_tmp.exists() and pulled_snap_tmp.stat().st_size > 0 else None
            if snapshot_path:
                print(f"Snapshot found on device for {package_name}, computing delta -> {delta_tmp}")
            else:
                print(f"No snapshot on device for {package_name}; treating snapshot as empty -> computing delta -> {delta_tmp}")

            ok = self.compute_delta(snapshot_path, str(pulled_tmp), str(delta_tmp))
            if not ok:
                print("Delta computation failed; not performing merge.")
                return False

            print(f"Applying delta to PC core fbm: {delta_tmp} -> {pc_file}")
            # apply_delta_to_pc will perform necessary locking around pc_file operations
            applied = self.apply_delta_to_pc(str(pc_file), str(delta_tmp))
            if applied:
                print(f"[FBM] delta applied to PC for package '{package_name}'")
                return True
            else:
                print("Applying delta failed; not performing merge.")
                return False
        finally:
            # cleanup
            try:
                if pulled_tmp.exists():
                    pulled_tmp.unlink()
            except Exception:
                pass
            try:
                if merged_tmp.exists():
                    merged_tmp.unlink()
            except Exception:
                pass
            try:
                if pulled_snap_tmp.exists():
                    pulled_snap_tmp.unlink()
            except Exception:
                pass
            try:
                if delta_tmp.exists():
                    delta_tmp.unlink()
            except Exception:
                pass

    # --- New workflow helpers ---
    def create_device_snapshot(self, package_name: str, snapshot_remote: str = None, device: str = None, transport_id: str = None) -> bool:
        """Create an on-device snapshot (copy) of the fbm file.

        Attempts `adb shell cp <src> <dst>` first, falls back to pull/push if cp is not available.
        Returns True on success.
        """
        src = self._remote_fbm_path(package_name)
        dst = snapshot_remote or f"/sdcard/fastbot_{package_name}.snapshot.fbm"
        try:
            from kea2.adbUtils import adb_shell, pull_file, push_file
        except Exception:
            try:
                from adbUtils import adb_shell, pull_file, push_file  # type: ignore
            except Exception as e:
                print("ADB utilities not available:", e)
                return False

        try:
            print(f"Creating device snapshot: cp {src} {dst}")
            adb_shell(["cp", src, dst], device=device, transport_id=transport_id)
            return True
        except Exception as e:
            print(f"adb shell cp failed ({e}), trying pull/push fallback")
            # fallback: pull then push to dst
            try:
                pc_tmp = os.path.join(self._pc_dir, f"fastbot_{package_name}.snapshot.from_device.fbm")
                pull_file(src, pc_tmp, device=device, transport_id=transport_id)
                push_file(pc_tmp, dst, device=device, transport_id=transport_id)
                try:
                    os.remove(pc_tmp)
                except Exception:
                    pass
                return True
            except Exception as e2:
                print(f"Snapshot fallback failed: {e2}")
                return False

    def compute_delta(self, snapshot_file: str, current_file: str, out_delta_file: str, merge_mode: str = 'increment') -> bool:
        """Compute delta between snapshot FBM and current FBM and write a delta FBM containing only positive increments.

        merge_mode ignored except for compatibility; behavior: delta = max(0, current - snapshot)
        """
        # Allow missing snapshot: only validate snapshot suffix when a path is provided and exists.
        if snapshot_file and os.path.exists(snapshot_file):
            if not self._ensure_fbm_suffix(snapshot_file, 'snapshot_file'):
                return False
        else:
            # no snapshot available on device; treat as empty snapshot
            snapshot_file = None

        # Validate current and output paths
        if not self._ensure_fbm_suffix(current_file, 'current_file'):
            return False
        if out_delta_file and not self._ensure_fbm_suffix(out_delta_file, 'out_delta_file'):
            return False

        # Load snapshot model if provided; if loading fails, log warning and treat as empty
        model_snap = None
        if snapshot_file:
            model_snap = self.load_model(snapshot_file)
            if model_snap is None:
                print(f"Warning: failed to load snapshot model from {snapshot_file}; treating snapshot as empty")
                model_snap = None
        model_cur = self.load_model(current_file)
        if model_cur is None:
            print(f"Failed to load current model from {current_file}")
            return False

        entries_snap = self.extract_entries(model_snap)
        entries_cur = self.extract_entries(model_cur)

        # convert snapshot to map for fast lookup (action_hash -> {activity: times})
        # NOTE: aggregate duplicate activity entries by summing, same as we do for current entries
        snap_map = {}
        for action_hash, targets in entries_snap:
            ah = int(action_hash)
            snap_map.setdefault(ah, {})
            for activity, times in targets:
                if not activity:
                    continue
                try:
                    t = int(times)
                except Exception:
                    t = 0
                snap_map[ah][activity] = snap_map[ah].get(activity, 0) + t

        # convert current entries into a consolidated map, summing duplicate activity entries if any
        cur_map = {}
        for action_hash, targets in entries_cur:
            ah = int(action_hash)
            cur_map.setdefault(ah, {})
            for activity, times in targets:
                if not activity:
                    continue
                try:
                    t = int(times)
                except Exception:
                    t = 0
                cur_map[ah][activity] = cur_map[ah].get(activity, 0) + t

        # compute deltas: for each action/activity, delta = cur_total - snapshot_total
        delta_map = {}
        for ah, activities in cur_map.items():
            for activity, cur_t in activities.items():
                snap_t = snap_map.get(ah, {}).get(activity, 0)
                inc = cur_t - snap_t
                if inc > 0:
                    delta_map.setdefault(ah, {})
                    delta_map[ah][activity] = inc

        if not delta_map:
            # produce an empty fbm file (deterministic) or skip writing — choose to write an empty FBM so callers can rely on its existence
            print("No positive deltas found; writing empty delta FBM")
            return self._write_aggregated_to_file({}, out_delta_file)

        return self._write_aggregated_to_file(delta_map, out_delta_file)

    def apply_delta_to_pc(self, pc_fbm: str, delta_fbm: str, out_fbm: str = None) -> bool:
        """Apply a delta FBM (containing increments) into the PC core FBM.

        If out_fbm is None, overwrite pc_fbm atomically; otherwise write to out_fbm.
        """
        if not self._ensure_fbm_suffix(pc_fbm, 'pc_fbm'):
            return False
        if not self._ensure_fbm_suffix(delta_fbm, 'delta_fbm'):
            return False
        if out_fbm and not self._ensure_fbm_suffix(out_fbm, 'out_fbm'):
            return False

        # Perform the entire PC file operation (read/merge/replace) under a single FileLock
        # Ensure temporary target file has a .fbm suffix so merge(...) accepts it.
        from pathlib import Path
        if out_fbm:
            target = out_fbm
        else:
            try:
                target = str(Path(pc_fbm).with_suffix('.updated.fbm'))
            except Exception:
                # fallback: append .updated.fbm
                target = pc_fbm + '.updated.fbm'

        try:
            with FileLock(str(pc_fbm), timeout=60.0):
                # If pc_fbm doesn't exist, just copy delta into pc (delta assumed to be absolute increments over empty)
                if not os.path.exists(pc_fbm):
                    try:
                        import shutil
                        if out_fbm:
                            shutil.copyfile(delta_fbm, out_fbm)
                            target_path = out_fbm
                        else:
                            shutil.copyfile(delta_fbm, pc_fbm)
                            target_path = pc_fbm
                        
                        # Set file permissions to 644
                        try:
                            # Check if it's Windows system
                            if os.name == 'nt':
                                # Directly use icacls command to set permissions on Windows
                                import subprocess
                                # First disable inheritance and copy existing permissions, then set new permissions
                                subprocess.run(["icacls", target_path, "/inheritance:d", "/grant", "Everyone:R", "/grant", "Administrators:F"], 
                                              capture_output=True, text=True, check=True)
                                print(f"Set Windows file permissions to simulate 644 for: {target_path}")
                            else:
                                # Set permissions directly on Unix/Linux systems
                                os.chmod(target_path, 0o644)
                                print(f"Set file permissions to 644 for: {target_path}")
                        except Exception as e:
                            print(f"Warning: Failed to set file permissions for {target_path}: {e}")
                        
                        return True
                    except Exception as e:
                        print(f"Failed to copy delta to pc_fbm: {e}")
                        return False

                # Merge pc_fbm and delta_fbm using sum mode into target
                ok = self.merge(pc_fbm, delta_fbm, target, merge_mode='sum')
                if not ok:
                    print("Failed to merge delta into pc_fbm")
                    return False

                # If out_fbm was not provided, replace pc_fbm atomically by moving target
                if not out_fbm:
                    try:
                        os.replace(target, pc_fbm)
                    except Exception:
                        import shutil
                        try:
                            shutil.copyfile(target, pc_fbm)
                            os.remove(target)
                        except Exception:
                            pass
                return True
        except LockTimeoutError:
            print(f"Timeout acquiring lock to merge/apply delta into {pc_fbm}")
            return False





