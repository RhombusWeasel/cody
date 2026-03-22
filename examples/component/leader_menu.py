# Copy this file to your skill as `components/leader_menu.py`.
# Cody calls `register_leader(reg)` if defined.
#
# Many terminals send Ctrl+Space as ctrl+@; when leader_key is ctrl+space, Cody binds both.


def register_leader(reg):
  """Example: letter `e` under the leader menu opens a submenu, `x` runs an action."""

  async def example_action(app):
    app.notify("Example leader action (skill leader_menu)", severity="information")

  reg.add_submenu((), "e", "Example")
  reg.add_action(("e",), "x", "Say hello via footer", example_action)
