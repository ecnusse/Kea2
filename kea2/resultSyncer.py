import threading

from pathlib import Path

from .adbUtils import ADBDevice
from .utils import getLogger, catchException, timer

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .keaUtils import Options

logger = getLogger(__name__)


class ResultSyncer:

    def __init__(self, device_output_dir, options: "Options"):
        self.device_output_dir = device_output_dir
        self.output_dir = options.output_dir / Path(device_output_dir).name
        self.running = False
        self.thread = None
        self.sync_event = threading.Event()

        ADBDevice.setDevice(serial=options.serial, transport_id=options.transport_id)
        self.dev = ADBDevice()

    def run(self):
        """Start a background thread to sync device data when triggered"""
        self.running = True
        self.thread = threading.Thread(target=self._sync_thread, daemon=True)
        self.thread.start()

    def _sync_thread(self):
        """Thread function that waits for sync event and then syncs data"""
        while self.running:
            # Wait for sync event with a timeout to periodically check if still running
            if self.sync_event.wait(timeout=1):
                self._sync_device_data()
                self.sync_event.clear()

    @timer("Data Sync cost %cost_time seconds")
    def close(self):
        self.running = False
        self.sync_event.set()
        if self.thread and self.thread.is_alive():
            logger.info("Syncing result data from device. Please wait...")
            self.thread.join(timeout=10)
        self._sync_device_data()
        try:
            logger.debug(f"Removing device output directory: {self.device_output_dir}")
            remove_device_dir = ["rm", "-rf", self.device_output_dir]
            self.dev.shell(remove_device_dir)
        except Exception as e:
            logger.error(f"Error removing device output directory: {e}", flush=True)

    @catchException("Error during device data sync.")    
    def _sync_device_data(self):
        """
        Sync the device data to the local directory.
        """
        logger.info(f"Syncing data: pulling from {self.device_output_dir} to {self.output_dir}")
        self.dev.sync.pull_dir(self.device_output_dir, self.output_dir, exist_ok=True)

        logger.info(f"Cleaning up pulled screenshots from device directory: {self.device_output_dir}")
        remove_pulled_screenshots = ["find", self.device_output_dir, "-name", '"*.png"', "-delete"]
        self.dev.shell(remove_pulled_screenshots)
