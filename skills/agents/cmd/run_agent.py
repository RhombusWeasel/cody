import asyncio
import os
import subprocess
import sys

from utils.cmd_loader import CommandBase
from utils.cfg_man import cfg
from components.utils.input_modal import preview_then_append_chat_message


class RunAgentSlashCommand(CommandBase):
  description = "Run a sub-agent by name with a task (preview, then add to chat)"

  async def execute(self, app, args: list[str]):
    try:
      if len(args) < 2:
        await preview_then_append_chat_message(
          app,
          "run_agent",
          "Usage: /run_agent <name> <task description…>",
        )
        return
      name = args[0]
      task = " ".join(args[1:])
      wd = cfg.get("session.working_directory", os.getcwd())
      script = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "scripts", "run_agent.py"))

      def run_subprocess() -> str:
        proc = subprocess.run(
          [sys.executable, script, "--name", name, "--task", task, "--working-directory", wd],
          capture_output=True,
          text=True,
          timeout=600,
          cwd=wd,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        parts = []
        if out:
          parts.append(out)
        if err:
          parts.append(err)
        text = "\n".join(parts) if parts else ""
        if proc.returncode != 0 and not text:
          text = f"(process exited with code {proc.returncode})"
        elif proc.returncode != 0:
          text = f"{text}\n\n(exit code {proc.returncode})"
        return text

      body = await asyncio.to_thread(run_subprocess)
      await preview_then_append_chat_message(app, f"Agent: {name}", body, role="assistant")
    except subprocess.TimeoutExpired:
      await preview_then_append_chat_message(
        app,
        "run_agent",
        "Error: agent run timed out (10 minute limit).",
      )
    except Exception as e:
      print(f"run_agent command failed: {e}")
