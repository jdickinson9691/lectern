from __future__ import annotations
import sys
import traceback
from pathlib import Path


def _write_import_failure(exc: BaseException) -> Path:
    target = Path.cwd() / "launch_error.txt"
    target.write_text("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)), encoding="utf-8")
    return target


try:
    from app.main import main
except BaseException as exc:
    log_path = _write_import_failure(exc)
    message = f"Lectern could not load its Python dependencies.\n\n{exc}\n\nDetails: {log_path}"
    try:
        import tkinter.messagebox as messagebox
        messagebox.showerror("Lectern Startup Error", message)
    except Exception:
        print(message, file=sys.stderr)
    raise SystemExit(1)

raise SystemExit(main())
