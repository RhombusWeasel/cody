import os, json, importlib
import importlib.util
import sys

def save_data(path, data):
    with open(path, 'w') as f:
        f.write(json.dumps(data, indent=2))

def load_data(path):
    with open(path, 'r')as f:
        return json.loads(f.read())

def discover_css(directory, relative_to=None):
  paths = []
  for root, dirs, files in os.walk(directory):
    dirs.sort()
    for file in sorted(files):
      if file.endswith('.css'):
        full = os.path.join(root, file)
        paths.append(os.path.relpath(full, relative_to) if relative_to else full)
  return paths

def load_folder(path, filetype='.json'):
    filedata = {}
    if os.path.isdir(path):
        for file in os.listdir(path):
            label = file[:-(len(filetype))]
            filepath = f'{path}/{file}'
            match filetype:
                case '.json':
                    if file[-5:] == '.json':
                        filedata[label] = load_data(filepath)
                case '.py':
                    if os.path.isdir(filepath):
                        filedata.update(load_folder(filepath, filetype))
                    elif file[0] != '_' and file[-3:] == '.py':
                        mod_name = filepath.replace('/', '_').replace('\\', '_').replace('.', '_')
                        spec = importlib.util.spec_from_file_location(mod_name, filepath)
                        if spec and spec.loader:
                            module = importlib.util.module_from_spec(spec)
                            sys.modules[mod_name] = module
                            spec.loader.exec_module(module)
                            filedata[label] = module
                case _:
                    pass
    return filedata
