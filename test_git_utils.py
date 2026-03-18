import os
import subprocess
import shutil

def is_git_repo(path: str) -> bool:
  git_dir = os.path.join(path, ".git")
  return os.path.isdir(git_dir)

def create_checkpoint(path: str, message: str) -> str | None:
  """Create a checkpoint commit without modifying the working tree or branch."""
  if not is_git_repo(path):
    return None
  try:
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = ".git/cody_checkpoint.index"
    
    index_path = os.path.join(path, ".git", "index")
    tmp_index_path = os.path.join(path, ".git", "cody_checkpoint.index")
    
    if os.path.exists(index_path):
        shutil.copy2(index_path, tmp_index_path)
    
    subprocess.run(
      ["git", "add", "-A"],
      cwd=path,
      env=env,
      check=True,
      capture_output=True,
    )
    
    tree_result = subprocess.run(
      ["git", "write-tree"],
      cwd=path,
      env=env,
      check=True,
      capture_output=True,
      text=True,
    )
    tree_hash = tree_result.stdout.strip()
    
    parent_args = []
    head_result = subprocess.run(
      ["git", "rev-parse", "HEAD"],
      cwd=path,
      capture_output=True,
      text=True,
    )
    if head_result.returncode == 0:
        parent_args = ["-p", head_result.stdout.strip()]
        
    commit_result = subprocess.run(
      ["git", "commit-tree", tree_hash, *parent_args, "-m", message],
      cwd=path,
      env=env,
      check=True,
      capture_output=True,
      text=True,
    )
    commit_hash = commit_result.stdout.strip()
    
    if os.path.exists(tmp_index_path):
        os.remove(tmp_index_path)
        
    # We also need to store this commit somewhere so it doesn't get garbage collected immediately,
    # though GC usually takes 30 days. Let's create a ref for it.
    subprocess.run(
      ["git", "update-ref", "-m", message, "refs/cody/checkpoints", commit_hash],
      cwd=path,
      check=True,
      capture_output=True,
    )
        
    return commit_hash
  except Exception as e:
    print(f"Error: {e}")
    return None

print(create_checkpoint("/home/pete/repos/cody", "Test checkpoint with ref"))
