from dataclasses import asdict
from typing import Any, Dict, Optional

from kea2.keaUtils import Options
from .errors import EngineIntegrationError
from .runtime import EngineRuntime


class Kea2PropertyEngine:
    """
    Simplified third-party integration facade.

    Public API:
      - init_kea2(config)
      - execute_property(ui_xml)
      - stop_kea2()
      - get_result()
    """

    def __init__(self):
        self._runtime: Optional[EngineRuntime] = None

    def init_kea2(self, config: Options) -> None:
        self._runtime = EngineRuntime(config)
        self._runtime.initialize()

    def execute_property(self, ui_xml: Optional[str] = None) -> Dict[str, Any]:
        runtime = self._require_runtime()
        return asdict(runtime.execute_property(ui_xml=ui_xml))

    def stop_kea2(self) -> None:
        runtime = self._require_runtime()
        runtime.stop()

    def get_result(self) -> Dict[str, Any]:
        runtime = self._require_runtime()
        return asdict(runtime.get_result())

    def _require_runtime(self) -> EngineRuntime:
        if self._runtime is None:
            raise EngineIntegrationError("NOT_INITIALIZED", "Please call init_kea2(config) first")
        return self._runtime
