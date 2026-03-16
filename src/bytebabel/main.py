"""ByteBabel entry point."""


def main() -> None:
    from .logger import setup_logging
    setup_logging()

    from .app import App
    from .ui.window import AppWindow

    window = AppWindow()
    app = App(window)
    window.set_app(app)
    window.mainloop()


if __name__ == "__main__":
    main()
