"""Shared layout helper for the SAGE browser UI."""


def clear_layout(layout) -> None:
    """Delete every widget (and nested layout) in `layout`, leaving it empty."""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())
