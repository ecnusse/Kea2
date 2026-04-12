import logging
import functools
from typing import TYPE_CHECKING
from retry import retry


if TYPE_CHECKING:
    from .keaUtils import KeaTestRunner, Options


from .adbUtils import ADBDevice
from .utils import catchException


logger = logging.getLogger(__name__)


class FBMSanapshotCreationError(RuntimeError):
    pass



@catchException("Error creating device FBM snapshots")
@retry(exceptions=FBMSanapshotCreationError, tries=3, delay=3)
def create_device_snapshots(options: "Options") -> None:
    """Create on-device snapshot copies of fastbot fbm files for configured packages.

    Behavior:
    - Only runs when options.merge_fbm is truthy.
    - Uses ADBDevice.shell (no subprocess) and retries cp up to max_retries.
    - Logs errors and never raises to avoid blocking startup.
    """

    for pkg in options.packageNames:
        src = f"/sdcard/fastbot_{pkg}.fbm"
        dst = f"/sdcard/fastbot_{pkg}.snapshot.fbm"

        try:
            # Check src existence
            check_cmd = f'test -f "{src}" && echo OK || echo NO'
            check_src = ADBDevice().shell(check_cmd)
            if not (isinstance(check_src, str) and "OK" in check_src):
                print(f"Source FBM not found on device for package {pkg}: {src}. Skipping snapshot creation.", flush=True)
                continue
        except Exception as e:
            logger.error(f"Failed to verify source FBM existence for {pkg}: {e}. Skipping.")
            continue
        
        ADBDevice().shell(f'cp "{src}" "{dst}"')

        # verify snapshot exists
        verify_cmd = f'test -f "{dst}" && echo OK || echo NO'
        r = ADBDevice().shell(verify_cmd)
        if not "OK" in r:
            raise FBMSanapshotCreationError("Failed to create ")
        logger.info(f"Snapshot created on device for package {pkg}: {dst}")
            


@catchException("Error finalizing and merging FBM deltas")
def finalize_and_merge(options: "Options"):
    """Pull device fbms, compute deltas and merge deltas into PC core fbm.

    Uses kea2.fbm_parser.FBMMerger.pull_and_merge_to_pc for each package.
    """
    from .fbm_parser import FBMMerger

    merger = FBMMerger()
    for pkg in options.packageNames:
        logger.info(f"Finalizing FBM delta for package: {pkg}")
        ok = merger.pull_and_merge_to_pc(pkg, device=options.serial, transport_id=options.transport_id)
        if ok:
            logger.info(f"Delta merge completed for package: {pkg}")
        else:
            logger.error(f"Delta merge reported failure for package: {pkg}")


def merge_fbm(func):
    """Decorator for KeaTestRunner.run: 
    
    Function: Merge FBM in multi-device test run to accelerate fastbot model training.

    The decorator uses `create_device_snapshots` before the run and `finalize_and_merge` after run.
    """
    @functools.wraps(func)
    def wrapper(self: "KeaTestRunner", *args, **kwargs):
        # Pre-run snapshot creation
        if self.options.merge_fbm:
            create_device_snapshots(self.options)

        try:
            return func(self, *args, **kwargs)
        finally:
            # Post-run finalize/merge
            if self.options.merge_fbm:
                finalize_and_merge(self.options)

    return wrapper
