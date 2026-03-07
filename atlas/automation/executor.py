"""Safe command executor for automation tasks."""

import asyncio
import os
import re
import shlex
import time
from pathlib import Path
from typing import Optional, Callable, AsyncIterator

from .models import CommandResult, CommandRisk


# Patterns that indicate dangerous commands
DANGEROUS_PATTERNS = [
    (r'\brm\s+-rf\s+[/~]', CommandRisk.CRITICAL, "Recursive delete from root/home"),
    (r'\brm\s+-rf\s+\*', CommandRisk.CRITICAL, "Recursive delete with wildcard"),
    (r'\bsudo\s+rm', CommandRisk.CRITICAL, "Sudo remove"),
    (r'\bdd\s+.*of=/dev/', CommandRisk.CRITICAL, "Direct disk write"),
    (r'\bmkfs\.', CommandRisk.CRITICAL, "Filesystem format"),
    (r'\b:\(\)\{.*\}', CommandRisk.CRITICAL, "Fork bomb"),
    (r'\bchmod\s+-R\s+777', CommandRisk.HIGH, "World-writable permissions"),
    (r'\bcurl.*\|\s*(ba)?sh', CommandRisk.HIGH, "Pipe curl to shell"),
    (r'\bwget.*\|\s*(ba)?sh', CommandRisk.HIGH, "Pipe wget to shell"),
    (r'\beval\s+', CommandRisk.HIGH, "Eval command"),
    (r'\bexec\s+', CommandRisk.HIGH, "Exec command"),
    (r'>\s*/etc/', CommandRisk.HIGH, "Write to /etc"),
    (r'\bsudo\b', CommandRisk.HIGH, "Sudo command"),
    (r'\bgit\s+push\s+.*--force', CommandRisk.HIGH, "Force push"),
    (r'\bgit\s+reset\s+--hard', CommandRisk.MEDIUM, "Hard reset"),
    (r'\bnpm\s+publish', CommandRisk.HIGH, "NPM publish"),
    (r'\bpip\s+install\b', CommandRisk.MEDIUM, "Pip install"),
    (r'\bnpm\s+install\b', CommandRisk.MEDIUM, "NPM install"),
    (r'\bdocker\s+push', CommandRisk.HIGH, "Docker push"),
    (r'\bkubectl\s+delete', CommandRisk.HIGH, "Kubectl delete"),
]

# Safe commands that don't need approval
SAFE_COMMANDS = [
    r'^ls\b',
    r'^pwd$',
    r'^echo\b',
    r'^cat\b',
    r'^head\b',
    r'^tail\b',
    r'^grep\b',
    r'^find\b',
    r'^which\b',
    r'^git\s+status',
    r'^git\s+log',
    r'^git\s+diff',
    r'^git\s+branch',
    r'^python\s+--version',
    r'^node\s+--version',
    r'^npm\s+--version',
]


class CommandExecutor:
    """Executes commands safely with risk assessment."""

    def __init__(
        self,
        working_dir: Optional[str] = None,
        env_vars: Optional[dict] = None,
        timeout: int = 300,  # 5 minutes default
    ):
        """Initialize executor.

        Args:
            working_dir: Working directory for commands
            env_vars: Additional environment variables
            timeout: Command timeout in seconds
        """
        self.working_dir = working_dir or os.getcwd()
        self.env_vars = env_vars or {}
        self.timeout = timeout

    def assess_risk(self, command: str) -> tuple[CommandRisk, Optional[str]]:
        """Assess the risk level of a command.

        Args:
            command: Command to assess

        Returns:
            Tuple of (risk_level, reason)
        """
        # Check for dangerous patterns
        for pattern, risk, reason in DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return risk, reason

        # Check if it's a safe command
        for pattern in SAFE_COMMANDS:
            if re.match(pattern, command.strip()):
                return CommandRisk.LOW, "Safe read-only command"

        # Default to medium risk
        return CommandRisk.MEDIUM, None

    def is_safe(self, command: str) -> bool:
        """Check if command is safe to run without approval."""
        risk, _ = self.assess_risk(command)
        return risk == CommandRisk.LOW

    async def execute(
        self,
        command: str,
        on_output: Optional[Callable[[str], None]] = None,
    ) -> CommandResult:
        """Execute a command.

        Args:
            command: Command to execute
            on_output: Callback for streaming output

        Returns:
            CommandResult with exit code, output, etc.
        """
        start_time = time.time()

        # Prepare environment
        env = os.environ.copy()
        env.update(self.env_vars)

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir,
                env=env,
            )

            stdout_parts = []
            stderr_parts = []

            # Read output streams
            async def read_stream(stream, parts, is_stderr=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace')
                    parts.append(decoded)
                    if on_output:
                        on_output(decoded)

            # Wait for completion with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, stdout_parts),
                        read_stream(process.stderr, stderr_parts, True),
                    ),
                    timeout=self.timeout,
                )
                await process.wait()
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    command=command,
                    exit_code=-1,
                    stdout="".join(stdout_parts),
                    stderr="Command timed out",
                    duration_ms=int((time.time() - start_time) * 1000),
                    success=False,
                )

            duration_ms = int((time.time() - start_time) * 1000)

            return CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout="".join(stdout_parts),
                stderr="".join(stderr_parts),
                duration_ms=duration_ms,
                success=process.returncode == 0,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                duration_ms=duration_ms,
                success=False,
            )

    async def execute_stream(
        self,
        command: str,
    ) -> AsyncIterator[str]:
        """Execute a command and stream output.

        Args:
            command: Command to execute

        Yields:
            Output lines as they become available
        """
        env = os.environ.copy()
        env.update(self.env_vars)

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.working_dir,
            env=env,
        )

        async for line in process.stdout:
            yield line.decode('utf-8', errors='replace')

        await process.wait()

    def validate_working_dir(self) -> bool:
        """Check if working directory exists and is accessible."""
        path = Path(self.working_dir)
        return path.exists() and path.is_dir()
