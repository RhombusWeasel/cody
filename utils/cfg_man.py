import getpass
import json
import os
import re
import sys

from utils.config_crypto import (
  DEFAULT_ITERATIONS,
  decrypt_json_bytes,
  encrypt_json_bytes,
)
from utils.paths import get_cody_dir, get_global_agents_dir


def deep_update(d, u):
  for k, v in u.items():
    if isinstance(v, dict):
      d[k] = deep_update(d.get(k, {}), v)
    else:
      d[k] = v
  return d


class ConfigPasswordRequired(RuntimeError):
  pass


class Config:
  def __init__(self, base_path: str, local_path: str):
    self._base_path = base_path
    self._local_path = local_path
    self.paths = [base_path, local_path]
    self.save_path = local_path
    self.data = {}
    self.changed = False
    self._encrypt_meta: dict[str, dict] = {}
    self._session_password: str | None = None

  def _enc_path(self, plain_path: str) -> str:
    return plain_path + ".enc"

  def _load_one(self, plain_path: str, password: str | None) -> None:
    enc_path = self._enc_path(plain_path)
    has_enc = os.path.isfile(enc_path)
    has_plain = os.path.isfile(plain_path)
    if has_enc and has_plain:
      if not password:
        raise ConfigPasswordRequired(
          f"Both plaintext and encrypted config exist at {plain_path}; "
          "password required to verify .enc and remove stale .json."
        )
      with open(enc_path, "rb") as f:
        blob = f.read()
      try:
        raw, salt, iterations = decrypt_json_bytes(blob, password)
      except ValueError as e:
        raise ValueError(
          f"Both plaintext and encrypted config exist for {plain_path}; "
          f".enc decrypt failed ({e}). Remove one file manually."
        ) from e
      try:
        os.remove(plain_path)
      except OSError as e:
        print(
          f"Warning: could not remove stale plaintext {plain_path}: {e}",
          file=sys.stderr,
        )
      self._encrypt_meta[plain_path] = {"salt": salt, "iterations": iterations}
      try:
        data = json.loads(raw.decode("utf-8"))
      except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in decrypted config {enc_path}: {e}") from e
      deep_update(self.data, data)
      return
    if has_enc:
      if not password:
        raise ConfigPasswordRequired(
          f"Encrypted config at {enc_path} requires a password "
          "(set CODY_CONFIG_PASSWORD or use --config-password-file)."
        )
      with open(enc_path, "rb") as f:
        blob = f.read()
      try:
        raw, salt, iterations = decrypt_json_bytes(blob, password)
      except ValueError as e:
        raise ValueError(str(e)) from e
      self._encrypt_meta[plain_path] = {"salt": salt, "iterations": iterations}
      try:
        data = json.loads(raw.decode("utf-8"))
      except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in decrypted config {enc_path}: {e}") from e
      deep_update(self.data, data)
    elif has_plain:
      if not password:
        raise ConfigPasswordRequired(
          f"Plaintext config at {plain_path} must be migrated to encrypted storage; "
          "set CODY_CONFIG_PASSWORD or use --config-password-file."
        )
      with open(plain_path, encoding="utf-8") as f:
        raw_text = f.read()
      try:
        data = json.loads(raw_text)
      except json.JSONDecodeError as e:
        print(f"Error loading config file {plain_path}: {e}")
        return
      deep_update(self.data, data)
      layer_bytes = json.dumps(data, indent=2).encode("utf-8")
      salt = os.urandom(16)
      blob = encrypt_json_bytes(
        layer_bytes, password, salt=salt, iterations=DEFAULT_ITERATIONS
      )
      os.remove(plain_path)
      enc_path = self._enc_path(plain_path)
      enc_dir = os.path.dirname(enc_path)
      if enc_dir:
        os.makedirs(enc_dir, exist_ok=True)
      with open(enc_path, "wb") as f:
        f.write(blob)
      self._encrypt_meta[plain_path] = {"salt": salt, "iterations": DEFAULT_ITERATIONS}

  def full_load(self, working_dir: str, password: str | None) -> None:
    self.data.clear()
    self._encrypt_meta.clear()
    self._session_password = password
    self.paths = [self._base_path, self._local_path]
    self.save_path = self._local_path
    for path in self.paths:
      self._load_one(path, password)
    proj = os.path.join(working_dir, ".agents", "cody_config.json")
    if proj not in self.paths:
      self.paths.append(proj)
    self.save_path = proj
    self._load_one(proj, password)

  def drill(self, mod_path, default=None):
    try:
      steps = [mod_path]
      if "." in mod_path:
        steps = mod_path.split(".")
        value = self.data
        for step in steps:
          if isinstance(value, list) and step.isdigit():
            value = value[int(step)]
          else:
            value = value[step]
        return value
      else:
        return self.data[mod_path]
    except (KeyError, TypeError, IndexError):
      return default

  def get(self, path, default=None):
    return self.drill(path, default)

  def set(self, path, value):
    steps = [path]
    if "." in path:
      steps = path.split(".")

    target = self.data
    for i, step in enumerate(steps[:-1]):
      next_step = steps[i + 1]
      if isinstance(target, list):
        if step.isdigit():
          step = int(step)
          while len(target) <= step:
            target.append([] if next_step.isdigit() else {})
          target = target[step]
        else:
          break
      else:
        if step not in target:
          target[step] = [] if next_step.isdigit() else {}
        target = target[step]

    last_step = steps[-1]
    if isinstance(target, list):
      if last_step.isdigit():
        last_step = int(last_step)
        while len(target) <= last_step:
          target.append(None)
        target[last_step] = value
    else:
      target[last_step] = value
    self.changed = True
    self.save()

  def _ensure_session_password(self) -> bool:
    if self._session_password:
      return True
    env_p = os.environ.get("CODY_CONFIG_PASSWORD")
    if env_p is not None:
      self._session_password = env_p
      return True
    try:
      self._session_password = getpass.getpass(
        "Config password (encrypts settings on disk): "
      )
    except EOFError:
      return False
    if not self._session_password:
      print("Config password required to save.", file=sys.stderr)
      return False
    return True

  def save(self):
    if not self.save_path:
      return
    if not self._ensure_session_password():
      return
    local_dir = os.path.dirname(self.save_path)
    if local_dir:
      os.makedirs(local_dir, exist_ok=True)
    meta = self._encrypt_meta.get(self.save_path)
    if not meta:
      salt = os.urandom(16)
      meta = {"salt": salt, "iterations": DEFAULT_ITERATIONS}
      self._encrypt_meta[self.save_path] = meta
    payload = json.dumps(self.data, indent=2)
    blob = encrypt_json_bytes(
      payload.encode("utf-8"),
      self._session_password,
      salt=meta["salt"],
      iterations=meta["iterations"],
    )
    enc_path = self._enc_path(self.save_path)
    with open(enc_path, "wb") as f:
      f.write(blob)
    if os.path.isfile(self.save_path):
      try:
        os.remove(self.save_path)
      except OSError as e:
        print(f"Could not remove plaintext config {self.save_path}: {e}", file=sys.stderr)

  def kdf_params_for_db_encrypt(self) -> tuple[bytes, int]:
    """
    Salt and iterations for encrypting the Cody project DB, reusing config KDF
    parameters when any encrypted config layer is loaded.
    """
    meta = self._encrypt_meta.get(self.save_path)
    if meta:
      return meta["salt"], meta["iterations"]
    for path in self.paths:
      m = self._encrypt_meta.get(path)
      if m:
        return m["salt"], m["iterations"]
    salt = os.urandom(16)
    meta = {"salt": salt, "iterations": DEFAULT_ITERATIONS}
    self._encrypt_meta[self.save_path] = meta
    return salt, DEFAULT_ITERATIONS


def project_db_base_path() -> str:
  return os.path.join(get_cody_dir(), ".agents", "cody_data.db")


def _project_db_requires_password_at_startup() -> bool:
  b = project_db_base_path()
  return os.path.isfile(b) or os.path.isfile(b + ".enc")


root_dir = get_cody_dir()
_base_path = os.path.join(get_global_agents_dir(), "cody_settings.json")
_local_path = os.path.join(root_dir, ".agents", "cody_config.json")

_old_base = f'{os.path.expanduser("~")}/.cody/settings.json'
_old_local = os.path.join(root_dir, "config.json")
if (
  os.path.exists(_old_base)
  and not os.path.exists(_base_path)
  and not os.path.exists(_base_path + ".enc")
):
  os.makedirs(os.path.dirname(_base_path), exist_ok=True)
  with open(_old_base) as f:
    with open(_base_path, "w") as out:
      out.write(f.read())
if (
  os.path.exists(_old_local)
  and not os.path.exists(_local_path)
  and not os.path.exists(_local_path + ".enc")
):
  os.makedirs(os.path.dirname(_local_path), exist_ok=True)
  with open(_old_local) as f:
    with open(_local_path, "w") as out:
      out.write(f.read())

cfg = Config(_base_path, _local_path)

_config_bootstrapped = False


def _candidate_plain_paths(working_dir: str) -> list[str]:
  wd = os.path.abspath(working_dir)
  proj = os.path.join(wd, ".agents", "cody_config.json")
  return [_base_path, _local_path, proj]


def _any_encrypted_config(working_dir: str) -> bool:
  for p in _candidate_plain_paths(working_dir):
    if os.path.isfile(p + ".enc"):
      return True
  return False


def _any_plaintext_config(working_dir: str) -> bool:
  for p in _candidate_plain_paths(working_dir):
    if os.path.isfile(p):
      return True
  return False


def _resolve_password(config_password_file: str | None) -> str:
  env_p = os.environ.get("CODY_CONFIG_PASSWORD")
  if env_p is not None:
    return env_p
  if config_password_file:
    with open(config_password_file, encoding="utf-8") as f:
      return f.read().strip()
  return getpass.getpass("Config password: ")


def _prompt_new_password() -> str:
  a = getpass.getpass("New config password: ")
  b = getpass.getpass("Confirm config password: ")
  if a != b:
    print("Passwords do not match.", file=sys.stderr)
    sys.exit(1)
  if not a:
    print("Password must not be empty.", file=sys.stderr)
    sys.exit(1)
  return a


def migrate_encrypt_configs(working_directory: str, password: str) -> None:
  for plain in _candidate_plain_paths(working_directory):
    enc = plain + ".enc"
    if os.path.isfile(enc):
      print(f"Skip (already encrypted): {enc}", file=sys.stderr)
      continue
    if not os.path.isfile(plain):
      continue
    with open(plain, encoding="utf-8") as f:
      raw = f.read()
    json.loads(raw)
    blob = encrypt_json_bytes(raw.encode("utf-8"), password)
    with open(enc, "wb") as f:
      f.write(blob)
    os.remove(plain)
    print(f"Encrypted: {plain} -> {enc}")


def ensure_config_loaded(
  working_directory: str,
  *,
  encrypt_config: bool = False,
  config_password_file: str | None = None,
) -> None:
  global _config_bootstrapped
  wd = os.path.abspath(working_directory)

  if encrypt_config:
    pwd = _prompt_new_password()
    migrate_encrypt_configs(wd, pwd)
    sys.exit(0)

  if _config_bootstrapped:
    return

  pwd: str | None = None
  if (
    _any_encrypted_config(wd)
    or _any_plaintext_config(wd)
    or _project_db_requires_password_at_startup()
  ):
    pwd = _resolve_password(config_password_file)

  try:
    cfg.full_load(wd, pwd)
  except ConfigPasswordRequired as e:
    print(str(e), file=sys.stderr)
    sys.exit(1)
  except ValueError as e:
    print(f"Config error: {e}", file=sys.stderr)
    sys.exit(1)

  _config_bootstrapped = True


def ensure_config_loaded_if_needed(working_directory: str | None = None) -> None:
  if _config_bootstrapped:
    return
  ensure_config_loaded(working_directory or os.path.abspath(os.getcwd()))


_ENV_REF = re.compile(r"\$\{env:([^}]+)\}")
_CFG_REF = re.compile(r"\$\{cfg:([^}]+)\}")


def expand_config_value(value: str, config: Config | None = None) -> str:
  if not isinstance(value, str):
    return str(value) if value is not None else ""
  c = config or cfg

  def repl_env(match: re.Match) -> str:
    key = match.group(1).strip()
    return os.environ.get(key, "")

  def repl_cfg(match: re.Match) -> str:
    path = match.group(1).strip()
    v = c.get(path, "")
    if v is None:
      return ""
    return str(v)

  step = _ENV_REF.sub(repl_env, value)
  return _CFG_REF.sub(repl_cfg, step)
