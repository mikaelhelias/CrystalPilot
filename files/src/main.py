def main():
    """Start the server"""
    global PROJECTS_DIR, XDS_PATH, PORT, HOST, RESTRICT_BROWSE

    parser = argparse.ArgumentParser(
        description="CrystalPilot v0.6.6 — XDS GUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Environment variables XDS_GUI_PORT, XDS_GUI_HOST, XDS_GUI_PROJECTS, "
               "XDS_GUI_XDS_PATH are also respected (CLI args take priority)."
    )
    parser.add_argument("--version", action="version", version="CrystalPilot v0.6.6")
    parser.add_argument("--port", type=int, default=None,
                        help=f"Port to listen on (default: {PORT})")
    parser.add_argument("--host", default=None,
                        help=f"Host/IP to bind to (default: {HOST})")
    parser.add_argument("--projects-dir", default=None,
                        help=f"Projects directory (default: {PROJECTS_DIR})")
    parser.add_argument("--xds-path", default=None,
                        help=f"Path to XDS executables directory (default: {XDS_PATH})")
    parser.add_argument("--restrict-browse", action="store_true", default=False,
                        help="Restrict file browser to the projects directory tree")
    args = parser.parse_args()

    # CLI args override env vars (which already set the defaults above)
    if args.port is not None:
        PORT = args.port
    if args.host is not None:
        HOST = args.host
    if args.projects_dir is not None:
        PROJECTS_DIR = Path(args.projects_dir)
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.xds_path is not None:
        XDS_PATH = Path(args.xds_path)
    if args.restrict_browse:
        RESTRICT_BROWSE = True

    # From here on, everything printed is also written to the log file (the
    # projects folder may only now be known, so this waits for the arguments).
    _log_path = _start_logging()

    # Update xds_runner with possibly-changed XDS_PATH
    xds_runner.xds_path = XDS_PATH

    server = ThreadingHTTPServer((HOST, PORT), XDSGUIHandler)

    # Graceful shutdown on SIGTERM (e.g. systemd, docker stop, the Windows
    # launcher's Stop script).  server.shutdown() blocks until serve_forever()
    # returns, and the signal handler runs on the very thread that is inside
    # serve_forever() - calling it directly deadlocks (the process then has to
    # be SIGKILLed).  Run it from a helper thread instead.
    def _shutdown_handler(signum, frame):
        print("\n\nReceived signal, shutting down...")
        try:
            _kill_all_procs()      # every running program, with its children, before the interpreter exits
        except Exception:
            pass
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, _shutdown_handler)

    display_host = "localhost" if HOST in ("0.0.0.0", "::") else HOST
    print(f"""
╔══════════════════════════════════════════════════╗
║          CrystalPilot v0.6.6 · XDS GUI           ║
║                  Mikael Elias                    ║
╚══════════════════════════════════════════════════╝
Free software under the GNU GPL v3, without any warranty.

Server running on: http://{display_host}:{PORT}

Open this URL in your browser to use the GUI.
Press Ctrl+C to stop the server.

Projects directory: {PROJECTS_DIR}
XDS path: {XDS_PATH}
Log file: {_log_path if _log_path else "(off)"}
API token: {API_TOKEN}   (only needed by scripts: header X-CrystalPilot-Token or ?token=;
            the browser tab that opens the page above is authorised automatically)
""")
    if HOST in ("0.0.0.0", "::"):
        print("Note: listening on every network interface. Anyone who can reach this computer\n"
              "      can open the interface; use --host 127.0.0.1 to keep it local.\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        try:
            n = _kill_all_procs()  # every running program, with its children, before the interpreter exits
            if n:
                print("Stopped %d running program(s)." % n)
        except Exception:
            pass
        server.server_close()


if __name__ == "__main__":
    main()
