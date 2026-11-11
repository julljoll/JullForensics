"""Módulos de adquisición forense de evidencias de Android."""

from .base import AcquisitionContext, AcquisitionModule, ModuleResult, ModuleStatus
from .bugreport import BugreportModule
from .content_providers import ContentProvidersModule
from .device_props import DevicePropsModule
from .packages import PackagesModule
from .screenshot import ScreenshotError, capture_forensic_screenshot
from .shared_storage import SharedStorageModule
from .system_dumps import SystemDumpsModule

__all__ = [
    "ModuleStatus",
    "ModuleResult",
    "AcquisitionContext",
    "AcquisitionModule",
    "DevicePropsModule",
    "PackagesModule",
    "SystemDumpsModule",
    "ContentProvidersModule",
    "SharedStorageModule",
    "BugreportModule",
    "capture_forensic_screenshot",
    "ScreenshotError",
]
