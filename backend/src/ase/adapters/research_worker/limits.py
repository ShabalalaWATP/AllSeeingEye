"""Fail-closed OS memory limits installed before loading document/media parsers."""

from __future__ import annotations

import ctypes
import importlib
import os
from ctypes import wintypes

MEMORY_BYTES = 512 * 1024 * 1024
_job_handle: int | None = None


class ResourceLimitUnavailable(RuntimeError):
    """This platform could not establish the required parser resource boundary."""


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


def _windows_limits() -> None:
    global _job_handle  # noqa: PLW0603
    # Windows-only APIs are absent from POSIX Python/typeshed.
    kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)  # noqa: B009
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateJobObjectW(None, None)
    if not handle:
        raise ResourceLimitUnavailable("Parser resource limits are unavailable.")
    limits = _ExtendedLimits()
    # PROCESS_MEMORY | JOB_MEMORY | KILL_ON_JOB_CLOSE. The aggregate cap also
    # constrains any future OCR/video subprocesses, which inherit job membership.
    limits.BasicLimitInformation.LimitFlags = 0x100 | 0x200 | 0x2000
    limits.ProcessMemoryLimit = MEMORY_BYTES
    limits.JobMemoryLimit = MEMORY_BYTES
    configured = kernel.SetInformationJobObject(
        handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    )
    if not configured or not kernel.AssignProcessToJobObject(handle, kernel.GetCurrentProcess()):
        kernel.CloseHandle(handle)
        raise ResourceLimitUnavailable("Parser resource limits are unavailable.")
    # Keep this non-inheritable handle open for the worker lifetime. Worker exit
    # closes its last handle and terminates every remaining descendant in the job.
    _job_handle = int(handle)


def apply_resource_limits() -> None:
    """Install hard limits in the child only; never invoke this in the API process."""
    try:
        if os.name == "nt":
            _windows_limits()
        elif os.name == "posix":
            resource = importlib.import_module("resource")
            resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        else:
            raise ResourceLimitUnavailable("Parser resource limits are unavailable.")
    except (OSError, ValueError, AttributeError) as error:
        raise ResourceLimitUnavailable("Parser resource limits are unavailable.") from error
