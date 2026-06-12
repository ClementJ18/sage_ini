"""A floating object browser that stays above the main window: every loaded object grouped by Side
then EditorSorting in a collapsible tree. Double-clicking a leaf loads that object as the
primary unit; right-clicking loads it as the comparison unit. Opened from the main
window's "Browser" menu action and rebuilt whenever a new source set is loaded."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sage_utils.views import _safe, display_name
from sage_utils.widgets import CopyableLabel as QLabel
from sage_utils.widgets import resource_path

ICON_FILE = "icon.ico"

_NO_SIDE = "Civilian"  # objects with no Side are sideless civilians in-game
_NO_SORTING = "NONE"  # objects with no EditorSorting (the engine's default)


def group_objects(game) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """Group the game's objects by Side then EditorSorting. Returns a nested mapping
    `side -> sorting -> [(raw name, display label), …]`, each leaf list sorted by label.
    Objects with no Side fall under "Civilian"; those with no EditorSorting under "NONE"."""
    groups: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for obj in game.objects.values():
        side = _safe(lambda o=obj: o.Side) or _NO_SIDE
        sorting = _safe(lambda o=obj: o.EditorSorting)
        sorting_name = getattr(sorting, "name", None) or _NO_SORTING
        # Lead with the raw template name, then the localized display name in brackets.
        shown = display_name(game, obj)
        label = f"{obj.name}  ({shown})" if shown else obj.name
        groups.setdefault(side, {}).setdefault(sorting_name, []).append((obj.name, label))
    for sortings in groups.values():
        for leaves in sortings.values():
            leaves.sort(key=lambda pair: pair[1].casefold())
    return groups


def _ordered_keys(keys) -> list[str]:
    """Alphabetical order with the placeholder buckets (parenthesised) sorted last."""
    return sorted(keys, key=lambda k: (k.startswith("("), k.casefold()))


class ObjectBrowser(QWidget):
    """A separate window, floating above the main window, listing every object as a
    Side → EditorSorting tree and driving the main window's two unit slots from clicks."""

    def __init__(self, browser) -> None:
        # A Tool window floats above its parent (the main window) only — not above other
        # applications — and is hidden/minimized along with it.
        super().__init__(browser, Qt.WindowType.Tool)
        self._browser = browser
        self.setWindowTitle("Object Browser")
        self.setWindowIcon(QIcon(str(resource_path(ICON_FILE, __file__))))
        self.resize(720, 760)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        hint = QLabel("Double-click loads as Unit 1, right-click loads as Unit 2.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(self.tree.indentation() // 2)  # tighter nesting
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.customContextMenuRequested.connect(self._on_right_click)
        self.tree.currentItemChanged.connect(self._update_buttons)
        layout.addWidget(self.tree)

        # Buttons act on the selected leaf, mirroring the double-/right-click shortcuts.
        buttons = QHBoxLayout()
        self.unit1_button = QPushButton("Load as Unit 1")
        self.unit1_button.clicked.connect(lambda: self._load_selected(slot=1))
        self.unit2_button = QPushButton("Load as Unit 2")
        self.unit2_button.clicked.connect(lambda: self._load_selected(slot=2))
        buttons.addWidget(self.unit1_button)
        buttons.addWidget(self.unit2_button)
        layout.addLayout(buttons)

        self.rebuild()
        self._update_buttons()

    def rebuild(self) -> None:
        """(Re)build the tree from the main window's current game, leaving every group
        collapsed. A no-op message stands in when no source is loaded yet."""
        self.tree.clear()
        game = self._browser.game
        if game is None:
            placeholder = QTreeWidgetItem(["Load a source in the main window first."])
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.tree.addTopLevelItem(placeholder)
            return

        groups = group_objects(game)
        for side in _ordered_keys(groups):
            side_item = QTreeWidgetItem([side])
            self.tree.addTopLevelItem(side_item)
            for sorting in _ordered_keys(groups[side]):
                leaves = groups[side][sorting]
                sort_item = QTreeWidgetItem([f"{sorting}  ({len(leaves)})"])
                side_item.addChild(sort_item)
                for name, label in leaves:
                    leaf = QTreeWidgetItem([label])
                    leaf.setData(0, Qt.ItemDataRole.UserRole, name)
                    leaf.setToolTip(0, name)
                    sort_item.addChild(leaf)
        self.tree.collapseAll()

    @staticmethod
    def _object_name(item: QTreeWidgetItem | None) -> str | None:
        """The raw object name stored on a leaf, or None for a group header."""
        if item is None:
            return None
        return item.data(0, Qt.ItemDataRole.UserRole)

    def _on_double_click(self, item: QTreeWidgetItem, _column: int) -> None:
        """Load a double-clicked object into the primary slot (group headers toggle)."""
        name = self._object_name(item)
        if name:
            self._browser.show_object(name)

    def _on_right_click(self, pos) -> None:
        """Load the right-clicked object into the comparison slot."""
        name = self._object_name(self.tree.itemAt(pos))
        if name:
            self._browser.compare_object(name)

    def _update_buttons(self, *_args) -> None:
        """Enable the load buttons only when a selectable object (a leaf) is selected."""
        enabled = self._object_name(self.tree.currentItem()) is not None
        self.unit1_button.setEnabled(enabled)
        self.unit2_button.setEnabled(enabled)

    def _load_selected(self, *, slot: int) -> None:
        """Load the currently selected leaf into Unit 1 or Unit 2 (no-op on a group)."""
        name = self._object_name(self.tree.currentItem())
        if not name:
            return
        if slot == 1:
            self._browser.show_object(name)
        else:
            self._browser.compare_object(name)
