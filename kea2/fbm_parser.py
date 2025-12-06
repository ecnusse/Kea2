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

    def load_model(self, file_path):
        """Load and return ReuseModel root object from a FBM file.

        Returns the model object on success, or None on failure.
        """
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

    def merge(self, file_a, file_b, out_file, merge_mode='sum'):
        """Merge two FBM files into out_file. Returns True on success."""
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

        def _accumulate(entries):
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
                    if merge_mode == 'max':
                        aggregated[ah][activity] = max(aggregated[ah].get(activity, 0), t)
                    else:
                        aggregated[ah][activity] = aggregated[ah].get(activity, 0) + t

        _accumulate(entries_a)
        _accumulate(entries_b)
        total_actions = len(aggregated)
        print(f"Merging: {len(entries_a)} entries from {file_a} + {len(entries_b)} entries from {file_b} -> {total_actions} unique actions")

        # Build new FlatBuffer
        # Use module-level functions from generated files for builder operations
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
        import tempfile
        tmp_path = None
        try:
            # Ensure output path
            if not out_file:
                out_file = os.path.join(self.script_dir, 'fastbot.model.fbm')

            # Finish builder (if not already finished)
            try:
                builder.Finish(root_offset)
            except Exception:
                # If Finish was already called upstream, ignore
                pass

            buf = builder.Output()

            out_dir = os.path.dirname(out_file) or self.script_dir
            os.makedirs(out_dir, exist_ok=True)

            # Create a unique temp file in the target directory to avoid collisions
            fd, tmp_path = tempfile.mkstemp(prefix='.tmp_fbm_', dir=out_dir)
            # Write bytes via file descriptor for best control
            with os.fdopen(fd, 'wb') as f:
                f.write(buf)
                try:
                    f.flush()
                    os.fsync(f.fileno())
                except Exception:
                    # flush/fsync best-effort
                    pass

            # Atomic replace
            try:
                os.replace(tmp_path, out_file)
            except Exception:
                # fallback to os.rename on some platforms
                os.rename(tmp_path, out_file)

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

    # --- New methods: device <-> PC FBM sync helpers ---
    def _pc_fbm_dir(self):
        """Return PC directory to store fbm files.

        Use a repository-local folder under the generated code package: `<script_dir>/fastbotx/merge_fbm`.
        Each package will have its own file `fastbot_{package}.fbm` inside this folder.
        This avoids depending on runtime options and centralizes merged FBM files.
        """
        from pathlib import Path
        base = Path(self.script_dir) / 'fastbotx' / 'merge_fbm'
        return base

    def _remote_fbm_path(self, package_name: str) -> str:
        return f"/sdcard/fastbot_{package_name}.fbm"

    def download_merge_push(self, package_name: str, device: str = None, transport_id: str = None):
        """Pull device FBM for package, merge with PC fbm and push merged back to device.

        Returns True on success, False otherwise. Handles missing files gracefully.
        """
        try:
            from kea2.adbUtils import pull_file, push_file
        except Exception:
            # try relative import
            try:
                from adbUtils import pull_file, push_file  # type: ignore
            except Exception as e:
                print("ADB utilities not available:", e)
                return False

        pc_dir = self._pc_fbm_dir()
        pc_dir.mkdir(parents=True, exist_ok=True)
        pc_file = pc_dir / f"fastbot_{package_name}.fbm"
        pulled_tmp = pc_dir / f"fastbot_{package_name}.from_device.fbm"
        merged_tmp = pc_dir / f"fastbot_{package_name}.merged.fbm"

        remote = self._remote_fbm_path(package_name)
        try:
            print(f"Attempting to pull {remote} to {pulled_tmp}")
            pull_file(remote, str(pulled_tmp), device=device, transport_id=transport_id)
        except Exception as e:
            print(f"pull_file failed for {remote}: {e}")

        # If device fbm not pulled, skip merge but report
        if not pulled_tmp.exists() or pulled_tmp.stat().st_size == 0:
            print(f"No FBM on device for {package_name}, skipping download-merge-push.")
            try:
                if pulled_tmp.exists():
                    pulled_tmp.unlink()
            except Exception:
                pass
            return False

        # Merge
        try:
            if pc_file.exists():
                print(f"Merging PC fbm {pc_file} with device fbm {pulled_tmp}")
                ok = self.merge(str(pc_file), str(pulled_tmp), str(merged_tmp), merge_mode='max')
                if not ok:
                    print("Merge failed; will not push to device.")
                    return False
            else:
                # no PC fbm, use pulled as merged
                import shutil
                shutil.copyfile(str(pulled_tmp), str(merged_tmp))

            # push merged back to device
            try:
                print(f"Pushing merged fbm {merged_tmp} to device:{remote}")
                push_file(str(merged_tmp), remote, device=device, transport_id=transport_id)
            except Exception as e:
                print(f"push_file failed: {e}")
                return False

            # replace pc_file with merged result
            try:
                import shutil
                shutil.copyfile(str(merged_tmp), str(pc_file))
            except Exception:
                pass

            print(f"[FBM] download_merge_push SUCCESS for package '{package_name}': pc='{pc_file}', device='{remote}'")
            return True
        finally:
            # cleanup intermediates
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

        pc_dir = self._pc_fbm_dir()
        pc_dir.mkdir(parents=True, exist_ok=True)
        pc_file = pc_dir / f"fastbot_{package_name}.fbm"
        pulled_tmp = pc_dir / f"fastbot_{package_name}.from_device.fbm"
        merged_tmp = pc_dir / f"fastbot_{package_name}.merged.fbm"

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

        try:
            if pc_file.exists():
                print(f"Merging PC fbm {pc_file} with device fbm {pulled_tmp} -> {merged_tmp}")
                ok = self.merge(str(pc_file), str(pulled_tmp), str(merged_tmp), merge_mode='max')
                if ok:
                    try:
                        merged_tmp.replace(pc_file)
                    except Exception:
                        import shutil
                        shutil.copyfile(str(merged_tmp), str(pc_file))
                else:
                    print("Merge failed; PC fbm not updated.")
                    return False
            else:
                # no PC fbm, just move pulled into pc_file
                try:
                    pulled_tmp.replace(pc_file)
                except Exception:
                    import shutil
                    shutil.copyfile(str(pulled_tmp), str(pc_file))
            print(f"[FBM] pull_and_merge_to_pc SUCCESS for package '{package_name}': pc='{pc_file}', device='{remote}'")
            return True
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
