import webbrowser
import asyncio

def _open_admin_ui():
    """
    Opens the FCC Admin UI in the default browser.
    Safe-to-fail and non-blocking.
    """
    try:
        webbrowser.open("http://localhost:8082/admin")
        print("[FCC] Admin UI opened.")
    except Exception as exc:
        print(f"[FCC] Admin UI failed safely: {exc}")


async def _warm_runtime(settings):
    """
    Placeholder for provider warmup.
    Upstream FCC does not define this, so we keep it minimal.
    """
    try:
        print("[FCC] Warming providers...")
        await asyncio.sleep(0.1)
        print("[FCC] Provider warmup complete.")
    except Exception as exc:
        print(f"[FCC] Warmup failed safely: {exc}")
