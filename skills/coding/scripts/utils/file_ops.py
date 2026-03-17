import os

def check_file_exists(file_path):
  """Checks if a file exists."""
  return os.path.exists(file_path)

def read_file_contents(file_path):
  """Reads the contents of a file."""
  with open(file_path, 'r') as f:
    return f.read()

def write_file_contents(file_path, content):
  """Writes contents to a file."""
  with open(file_path, 'w') as f:
    f.write(content)

def ensure_indentation(content, spaces=2):
  """Ensures the content uses the specified number of spaces for indentation."""
  # Basic implementation, can be expanded for more complex parsing
  lines = content.split('\n')
  indented_lines = []
  for line in lines:
    # Replace tabs with spaces
    line = line.replace('\t', ' ' * spaces)
    indented_lines.append(line)
  return '\n'.join(indented_lines)
