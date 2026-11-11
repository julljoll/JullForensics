"""Vistas de la aplicación forense JullForensics."""

from .acquisition_view import AcquisitionView
from .case_view import CaseView
from .custody_view import CustodyView
from .device_view import DeviceView
from .integrity_view import IntegrityView
from .report_view import ReportView
from .screenshot_view import ScreenshotView

__all__ = [
    "CaseView",
    "DeviceView",
    "ScreenshotView",
    "AcquisitionView",
    "IntegrityView",
    "ReportView",
    "CustodyView",
]
