"""
Phase 7.4: Dynamic Profiling with sys.setprofile
Capture function call events during test execution to build dynamic call traces.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class CallEvent:
    """Represents a function call event."""
    event_type: str  # "call" or "return"
    function_name: str
    module_name: str
    line_number: int
    depth: int  # Call stack depth
    arg_types: List[str] = field(default_factory=list)  # Types of arguments
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CallTrace:
    """Represents a sequence of call/return events."""
    events: List[CallEvent] = field(default_factory=list)
    call_pairs: List[tuple] = field(default_factory=list)  # (caller, callee) pairs
    call_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def add_event(self, event: CallEvent):
        """Add an event to the trace."""
        self.events.append(event)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "events": [e.to_dict() for e in self.events],
            "call_pairs": list(set(self.call_pairs)),  # Deduplicate
            "call_counts": dict(self.call_counts)
        }


class DynamicProfiler:
    """
    Captures dynamic function call traces during test execution.
    Uses subprocess to run pytest and injected profiler hook.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the dynamic profiler.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.trace = CallTrace()
        self.call_stack = []  # Stack to track nested calls
        self.file_filters = set()  # Files to profile
        self._initialize_file_filters()
        
        logger.info(f"[PHASE 7.4] DynamicProfiler initialized for {repo_path}")
    
    def _initialize_file_filters(self):
        """
        Initialize filters to only profile files in the repository.
        """
        for root, dirs, files in os.walk(self.repo_path):
            # Skip certain directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    self.file_filters.add(os.path.normpath(full_path))
        
        logger.info(f"[PHASE 7.4] Initialized filters for {len(self.file_filters)} Python files")
    
    def run_profiling(self) -> Dict[str, Any]:
        """
        Run pytest with profiling to capture dynamic call traces.
        
        Returns:
            Summary of profiling results
        """
        logger.info("[PHASE 7.4] Starting dynamic profiling with subprocess injection")
        
        try:
            # Create profiler hook script
            hook_script = self._create_profiler_hook()
            
            # Run pytest with profiler hook
            cmd = [
                sys.executable,
                "-c",
                hook_script
            ]
            
            logger.info(f"[PHASE 7.4] Running profiler hook for repository: {self.repo_path}")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=self.repo_path
                )
                
                logger.info(f"[PHASE 7.4] Profiling exit code: {result.returncode}")
                
                # Parse the profiler output
                trace_data = self._parse_profiler_output(result.stdout, result.stderr)
                
                return self._process_trace_data(trace_data)
                
            except subprocess.TimeoutExpired:
                logger.error("[PHASE 7.4] Profiling timeout (300 seconds)")
                raise RuntimeError("Profiling timeout exceeded")
            
        except Exception as e:
            logger.error(f"[PHASE 7.4] Error during profiling: {str(e)}")
            raise
    
    def _create_profiler_hook(self) -> str:
        """
        Create a Python script that runs pytest with profiling.
        
        Returns:
            Python code as a string
        """
        hook_code = '''
import sys
import json
import subprocess
from collections import defaultdict

# Profiler state
events = []
call_stack = []
call_counts = defaultdict(int)
repo_path = sys.argv[1] if len(sys.argv) > 1 else "."

# Get Python files to filter
import os
repo_files = set()
for root, dirs, files in os.walk(repo_path):
    dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__']]
    for f in files:
        if f.endswith('.py'):
            repo_files.add(os.path.normpath(os.path.join(root, f)))

def profile_callback(frame, event, arg):
    """Callback for sys.setprofile"""
    global events, call_stack
    
    try:
        # Filter to repository files
        file_path = frame.f_code.co_filename
        normalized = os.path.normpath(file_path)
        
        is_in_repo = any(
            normalized.startswith(f) or normalized.endswith(os.path.basename(f))
            for f in repo_files
        )
        
        if not (is_in_repo or 'test' in normalized.lower()):
            return None
        
        func_name = frame.f_code.co_name
        module_name = frame.f_globals.get('__name__', '<unknown>')
        line_no = frame.f_lineno
        
        if event == "call":
            # Get argument types with enhanced type info
            arg_types = []
            try:
                # Get function code object to determine argument names
                code = frame.f_code
                num_args = code.co_argcount
                arg_names = code.co_varnames[:num_args]
                
                # Collect types for actual arguments (in order)
                for arg_name in arg_names:
                    if arg_name in frame.f_locals:
                        arg_val = frame.f_locals[arg_name]
                        type_name = type(arg_val).__name__
                        arg_types.append(type_name)
            except:
                # Fallback: collect all non-private locals
                try:
                    for arg_name, arg_val in frame.f_locals.items():
                        if not arg_name.startswith('_'):
                            arg_types.append(type(arg_val).__name__)
                except:
                    pass
            
            events.append({
                "event": "call",
                "func": func_name,
                "module": module_name,
                "line": line_no,
                "depth": len(call_stack),
                "arg_types": arg_types
            })
            call_stack.append(func_name)
            
        elif event == "return":
            events.append({
                "event": "return",
                "func": func_name,
                "module": module_name,
                "line": line_no,
                "depth": len(call_stack) - 1
            })
            
            if call_stack:
                call_stack.pop()
                if call_stack:
                    caller = call_stack[-1]
                    pair = f"{caller}->{func_name}"
                    call_counts[pair] += 1
    except:
        pass
    
    return profile_callback

# Set profiler
sys.setprofile(profile_callback)

# Run pytest
import pytest
exit_code = pytest.main([
    sys.argv[1] if len(sys.argv) > 1 else ".",
    "-v", "--tb=short", "-q"
])

# Disable profiler
sys.setprofile(None)

# Output results
output = {
    "events": events,
    "call_counts": dict(call_counts),
    "exit_code": exit_code
}
print(json.dumps(output))
'''
        
        return hook_code
    
    def _parse_profiler_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """
        Parse profiler output from subprocess.
        
        Args:
            stdout: Standard output from subprocess
            stderr: Standard error from subprocess
            
        Returns:
            Parsed trace data
        """
        logger.info("[PHASE 7.4] Parsing profiler output")
        
        try:
            # Find JSON in output
            lines = stdout.split('\n')
            for line in reversed(lines):
                if line.strip().startswith('{'):
                    trace_data = json.loads(line)
                    logger.info(f"[PHASE 7.4] Parsed {len(trace_data.get('events', []))} events")
                    return trace_data
            
            logger.warning("[PHASE 7.4] No trace data found in output")
            return {"events": [], "call_counts": {}}
            
        except json.JSONDecodeError as e:
            logger.error(f"[PHASE 7.4] Failed to parse JSON: {str(e)}")
            return {"events": [], "call_counts": {}}
    
    def _process_trace_data(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw trace data into structured format.
        
        Args:
            trace_data: Raw trace data from profiler
            
        Returns:
            Processed results
        """
        logger.info("[PHASE 7.4] Processing trace data")
        
        events = trace_data.get('events', [])
        call_counts = trace_data.get('call_counts', {})
        
        # Build call graph
        call_graph = defaultdict(set)
        for pair_str, count in call_counts.items():
            if '->' in pair_str:
                caller, callee = pair_str.split('->')
                call_graph[caller].add(callee)
        
        # Calculate statistics
        call_events = sum(1 for e in events if e.get('event') == 'call')
        return_events = sum(1 for e in events if e.get('event') == 'return')
        max_depth = max((e.get('depth', 0) for e in events), default=0)
        
        return {
            "phase": "7.4",
            "title": "Dynamic Profiling",
            "status": "success",
            "summary": {
                "total_events": len(events),
                "call_events": call_events,
                "return_events": return_events,
                "unique_call_pairs": len(call_counts),
                "max_call_depth": max_depth
            },
            "call_graph": {caller: list(callees) for caller, callees in call_graph.items()},
            "call_counts": call_counts,
            "trace": {
                "events": events,
                "call_pairs": list(call_counts.keys()),
                "call_counts": call_counts
            }
        }


def run_dynamic_profiling(
    repo_path: str
) -> Dict[str, Any]:
    """
    Run dynamic profiling on a repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Profiling results
    """
    profiler = DynamicProfiler(repo_path)
    return profiler.run_profiling()
