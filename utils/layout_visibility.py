"""Sidebar open/closed state and toggle logic shared by app keybind mixins."""

sidebar_visibility: dict[str, bool] = {
  'util-sidebar': True,
  'term-sidebar': False,
}


def init_sidebar_state_from_cfg() -> None:
  from utils.cfg_man import cfg

  sidebar_visibility['util-sidebar'] = bool(cfg.get('interface.sidebar_open_on_start'))


def toggle_sidebar_on_app(app, sidebar_id: str) -> None:
  """Toggle #-visible class, optional dynamic app bindings, and terminal focus."""
  sidebar_visibility[sidebar_id] = not sidebar_visibility[sidebar_id]
  widget = app.query_one(f'#{sidebar_id}')
  widget.set_class(sidebar_visibility[sidebar_id], '-visible')
  if hasattr(widget, '_custom_bindings') and widget._custom_bindings:
    for binding in widget._custom_bindings:
      keys = binding[0]
      action = binding[1]
      desc = binding[2] if len(binding) > 2 else ""
      if sidebar_visibility[sidebar_id]:
        app.bind(keys, action, description=desc)
      elif hasattr(app, '_bindings') and keys in app._bindings.key_to_bindings:
        app._bindings.key_to_bindings[keys] = [
          b for b in app._bindings.key_to_bindings[keys] if b.action != action
        ]
        if not app._bindings.key_to_bindings[keys]:
          del app._bindings.key_to_bindings[keys]
    if hasattr(app, 'refresh_bindings'):
      app.refresh_bindings()
  if sidebar_visibility[sidebar_id] and sidebar_id == 'term-sidebar':
    app.set_timer(0.05, widget.start_terminal)
    widget.query_one("#terminal_bash").focus()
