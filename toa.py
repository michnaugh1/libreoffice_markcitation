"""
Table of Authorities - LibreOffice Extension
UNO Protocol Handler entry point.

This file is loaded by LibreOffice as a UNO component (registered in
manifest.xml as application/vnd.sun.star.uno-component;type=Python).

All menu commands dispatched via org.toa.command:* are routed here.
The actual logic lives in pythonpath/toa/ so it can be organized as a
proper Python package without cluttering this entry point.
"""
import sys
import os
import uno
import unohelper

from com.sun.star.frame import XDispatch, XDispatchProvider
from com.sun.star.lang import XInitialization, XServiceInfo

# ── Path setup ────────────────────────────────────────────────────────────────
# LibreOffice loads this file from the extension directory. We add our
# pythonpath/ subdirectory to sys.path so that "import toa.commands" works.
_ext_dir = os.path.dirname(os.path.abspath(__file__))
_pythonpath = os.path.join(_ext_dir, 'pythonpath')
if _pythonpath not in sys.path:
    sys.path.insert(0, _pythonpath)

# ── Constants ─────────────────────────────────────────────────────────────────
PROTOCOL = "org.toa.command:"
IMPL_NAME = "org.toa.ProtocolHandler"
SERVICE_NAMES = ("com.sun.star.frame.ProtocolHandler",)


# ── Protocol Handler ──────────────────────────────────────────────────────────
class TOAHandler(unohelper.Base, XDispatchProvider, XDispatch,
                 XInitialization, XServiceInfo):
    """
    Routes org.toa.command:* URLs to the appropriate command function.

    LibreOffice calls initialize() with the active frame, then calls
    dispatch() when the user clicks a menu item. We look up a matching
    function in toa.commands and call it with (ctx, frame).
    """

    def __init__(self, ctx, *args):
        self.ctx = ctx
        self.frame = None

    # XInitialization ──────────────────────────────────────────────────────────
    def initialize(self, args):
        if args:
            self.frame = args[0]

    # XServiceInfo ─────────────────────────────────────────────────────────────
    def getImplementationName(self):
        return IMPL_NAME

    def supportsService(self, name):
        return name in SERVICE_NAMES

    def getSupportedServiceNames(self):
        return SERVICE_NAMES

    # XDispatchProvider ────────────────────────────────────────────────────────
    def queryDispatch(self, url, target_frame, search_flags):
        if url.Protocol == PROTOCOL:
            return self
        return None

    def queryDispatches(self, requests):
        return [self.queryDispatch(r.FeatureURL, r.FrameName, r.SearchFlags)
                for r in requests]

    # XDispatch ────────────────────────────────────────────────────────────────
    def dispatch(self, url, args):
        """
        Map org.toa.command:SomeCommand → toa.commands.cmd_somecommand().
        Command names are lowercased for the function lookup so the URL
        can use CamelCase (MarkCitation) while functions use snake-y names
        (cmd_markcitation).
        """
        cmd = url.Path
        try:
            from toa import commands
            fn = getattr(commands, f"cmd_{cmd.lower()}", None)
            if fn is not None:
                fn(self.ctx, self.frame)
            else:
                _show_error(self.frame, f"Unknown command: {cmd}")
        except Exception as exc:
            import traceback
            _show_error(self.frame,
                        f"Error in {cmd}:\n\n{traceback.format_exc()}")

    def addStatusListener(self, listener, url):
        pass

    def removeStatusListener(self, listener, url):
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def _show_error(frame, message):
    try:
        from toa.ui import show_message
        show_message(frame, "Table of Authorities — Error", message)
    except Exception:
        pass  # last resort: swallow so LO doesn't crash


# ── UNO registration ──────────────────────────────────────────────────────────
def createInstance(ctx):
    return TOAHandler(ctx)


g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    TOAHandler,
    IMPL_NAME,
    SERVICE_NAMES,
)
