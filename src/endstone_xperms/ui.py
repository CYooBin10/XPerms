from __future__ import annotations

from endstone.form import ActionForm, Dropdown, MessageForm, ModalForm, TextInput, Toggle


class XPermsUI:
    labels = ("Players", "Groups", "Permissions", "Linter", "Audit", "Explain", "Simulator", "Settings")

    def __init__(self, plugin) -> None:
        self.plugin = plugin

    def open(self, player) -> None:
        uid = str(player.unique_id).lower()
        form = ActionForm("XPerms", "Select menu")
        for label in self.labels:
            form.add_button(label, on_click=lambda sender, label=label: self._open(uid, sender, label))
        player.send_form(form)

    def _online(self, uid: str, player) -> bool:
        return str(getattr(player, "unique_id", "")).lower() == uid and any(
            str(getattr(current, "unique_id", "")).lower() == uid for current in self.plugin.server.online_players
        )

    def _allowed(self, player, permission: str) -> bool:
        checker = getattr(player, "has_permission", None)
        return bool(checker("xperms.admin") or checker(permission)) if callable(checker) else False

    def _open(self, uid: str, player, label: str) -> None:
        permissions = {"Linter": "xperms.lint", "Audit": "xperms.audit", "Explain": "xperms.explain", "Simulator": "xperms.simulate", "Settings": "xperms.ui"}
        if not self._online(uid, player) or (label in permissions and not self._allowed(player, permissions[label])):
            return
        if label == "Players":
            self._message(uid, player, label, "Player information")
        elif label == "Groups":
            self._message(uid, player, label, "Group information")
        elif label == "Permissions":
            self._modal(uid, player, label, "Permission", "Value")
        elif label == "Linter":
            self._message(uid, player, label, "\n".join(issue.message for issue in self.plugin.linter.run()) or "No issues")
        elif label == "Audit":
            self._message(uid, player, label, "\n".join(str(item) for item in self.plugin.storage.audit.recent()) or "No audit records")
        elif label == "Explain":
            self._modal(uid, player, label, "User", "Permission")
        elif label == "Simulator":
            self._modal(uid, player, label, "User", "Node")
        else:
            self._modal(uid, player, label, "Option", "Enabled")

    def _message(self, uid, player, title, content):
        if self._online(uid, player):
            player.send_form(MessageForm(title, content, "Close", "Close"))

    def _modal(self, uid, player, title, first, second):
        controls = [TextInput(first), Dropdown("Group", list(self.plugin.storage.groups) or ["default"]), Toggle(second)]
        player.send_form(ModalForm(title, controls, "Close", on_submit=lambda sender, _: None))
