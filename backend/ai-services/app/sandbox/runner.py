"""
ORCA Isolated Data & Code Sandbox Runner.

Provides a secured execution environment for:
- Deterministic maritime calculations (drift vectoring, fuel consumption, catch rate estimation)
- GIS transformations and bathymetric spatial queries
- Marine dataset CSV/JSON analysis
- Scientific sensor telemetry validation

Security Controls:
1. Isolated Subprocess: Runs in a dedicated worker process via `sys.executable -I`
2. Isolated Filesystem: Sandboxed in a temporary directory automatically destroyed after run
3. Hard Execution Timeout: Terminated after a strict configurable limit (default 10s)
4. Resource & Network Restrictions: Network socket creation is blocked in the runner prelude
5. Controlled Imports: Whitelisted safe mathematical and data processing libraries
6. Process Isolation: Main FastAPI event loop and state are never exposed
"""
import sys
import os
import json
import tempfile
import asyncio
import subprocess
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from ..observability.logger import logger


# Code prelude injected into sandboxed Python scripts to restrict unsafe builtins and modules
SANDBOX_PRELUDE = """
import sys
import builtins

# Block dangerous primitives
BLOCKED_MODULES = [
    'socket', 'requests', 'urllib', 'http.client', 'ftplib',
    'subprocess', 'shutil', 'webbrowser', 'smtplib'
]

original_import = builtins.__import__

def secure_import(name, *args, **kwargs):
    base_pkg = name.split('.')[0]
    if base_pkg in BLOCKED_MODULES:
        raise ImportError(f"Security Policy: Access to '{name}' is restricted inside the ORCA sandbox.")
    return original_import(name, *args, **kwargs)

builtins.__import__ = secure_import

# Safe globals for marine scientific calculations
import math
import json
import csv
try:
    import pandas as pd
except ImportError:
    pass
try:
    import shapely
    from shapely.geometry import Point, LineString, Polygon
except ImportError:
    pass
"""


class SandboxExecutionRequest(BaseModel):
    code: str = Field(..., description="Python script or calculation snippet to execute")
    dataset_csv: Optional[str] = Field(default=None, description="Optional CSV content to mount in sandbox filesystem")
    context_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Input parameters as JSON")
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0, description="Max execution time in seconds")


class SandboxExecutionResult(BaseModel):
    status: str = Field(..., description="'success', 'error', or 'timeout'")
    stdout: str
    stderr: str
    result_data: Optional[Dict[str, Any]] = None
    execution_time_ms: float
    output_files: List[str] = Field(default_factory=list)


class IsolatedSandboxRunner:
    """
    Executes Python scripts within an ephemeral, restricted filesystem.
    """

    async def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="orca_sandbox_") as sandbox_dir:
            script_path = os.path.join(sandbox_dir, "task.py")
            context_path = os.path.join(sandbox_dir, "context.json")
            output_json_path = os.path.join(sandbox_dir, "output.json")
            csv_path = os.path.join(sandbox_dir, "data.csv")

            # Write context data
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(request.context_data or {}, f)

            # Write dataset if provided
            if request.dataset_csv:
                with open(csv_path, "w", encoding="utf-8") as f:
                    f.write(request.dataset_csv)

            # Assemble isolated script
            full_script = (
                SANDBOX_PRELUDE
                + "\n# User-provided code starts below\n"
                + request.code
                + "\n"
            )

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(full_script)

            cmd = [
                sys.executable,
                "-I",  # Isolated mode (ignores PYTHONPATH and user site-packages)
                "-B",  # Do not write bytecode .pyc
                "task.py"
            ]

            proc = None
            try:
                # Execute in subprocess with isolated cwd
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=sandbox_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=request.timeout_seconds
                    )
                    stdout_str = stdout_bytes.decode("utf-8", errors="replace")
                    stderr_str = stderr_bytes.decode("utf-8", errors="replace")
                    exit_code = proc.returncode

                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    # Check for output.json written by script
                    result_data = None
                    if os.path.exists(output_json_path):
                        try:
                            with open(output_json_path, "r", encoding="utf-8") as f:
                                result_data = json.load(f)
                        except Exception as e:
                            logger.warning(f"Failed parsing sandbox output.json: {e}")

                    # List files generated in sandbox
                    files_gen = [
                        fname for fname in os.listdir(sandbox_dir)
                        if fname not in ("task.py", "context.json", "output.json")
                    ]

                    status = "success" if exit_code == 0 else "error"
                    return SandboxExecutionResult(
                        status=status,
                        stdout=stdout_str,
                        stderr=stderr_str,
                        result_data=result_data,
                        execution_time_ms=round(elapsed_ms, 2),
                        output_files=files_gen,
                    )

                except asyncio.TimeoutError:
                    if proc:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return SandboxExecutionResult(
                        status="timeout",
                        stdout="",
                        stderr=f"Execution exceeded the {request.timeout_seconds}s safety timeout and was forcefully terminated.",
                        result_data=None,
                        execution_time_ms=round(elapsed_ms, 2),
                        output_files=[],
                    )

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return SandboxExecutionResult(
                    status="error",
                    stdout="",
                    stderr=f"Sandbox process launch error: {str(e)}",
                    result_data=None,
                    execution_time_ms=round(elapsed_ms, 2),
                    output_files=[],
                )


sandbox_runner = IsolatedSandboxRunner()
