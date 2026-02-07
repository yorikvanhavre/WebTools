import os


class Metadata(object):

    @classmethod
    def install_required(cls, python_exe, vendor_path, path):
        pylibs = []

        try:
            with open(os.path.join(path, 'metadata.txt'), 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('pylibs='):
                        libs_str = line.split('=', 1)[1]
                        pylibs = [lib.strip() for lib in libs_str.split(',') if lib.strip()]
        except IOError:
            pass

        if len(pylibs) > 0:
            print(f"Installing {pylibs}")
            import subprocess
            import sys
            import importlib.util

            for package in pylibs:
                package = package.strip()

                if 'PYTHONHOME' in os.environ:
                    del os.environ['PYTHONHOME']

                # Determine requirement name (strip common version specifiers)
                req_name = package
                for sep in ['==', '>=', '<=', '~=', '!=', '>', '<', '===']:
                    if sep in req_name:
                        req_name = req_name.split(sep, 1)[0]
                req_name = req_name.strip()

                # Check if already installed in vendor_path by filename heuristics
                already_installed = False
                if os.path.isdir(vendor_path):
                    try:
                        entries = os.listdir(vendor_path)
                    except Exception:
                        entries = []

                    norm_names = {req_name, req_name.replace('-', '_'), req_name.replace('-', '')}
                    lower_norm = {n.lower() for n in norm_names}

                    for e in entries:
                        # top-level package/module directory
                        if e in norm_names or e.lower() in lower_norm:
                            already_installed = True
                            break
                        # check dist-info / egg-info metadata directories
                        if e.endswith('.dist-info') or e.endswith('.egg-info'):
                            base = e.rsplit('.', 1)[0]
                            if base in norm_names or base.lower() in lower_norm:
                                already_installed = True
                                break

                # Also try import check by temporarily prepending vendor_path to sys.path
                if not already_installed:
                    added_to_syspath = False
                    try:
                        if os.path.isdir(vendor_path) and vendor_path not in sys.path:
                            sys.path.insert(0, vendor_path)
                            added_to_syspath = True

                        for candidate in [req_name, req_name.replace('-', '_')]:
                            try:
                                if importlib.util.find_spec(candidate) is not None:
                                    already_installed = True
                                    break
                            except Exception:
                                # ignore lookup errors and continue
                                pass
                    finally:
                        if added_to_syspath:
                            try:
                                sys.path.remove(vendor_path)
                            except ValueError:
                                pass

                if already_installed:
                    print(f"Skipping {package} — already installed in {vendor_path}")
                    continue

                p = subprocess.Popen(
                    [python_exe, '-m', 'pip', 'install', '--disable-pip-version-check', '--target', vendor_path, package],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )

                for line in iter(p.stdout.readline, b''):
                    if line:
                        print(line.decode('utf-8'), end='')
                print()

                for err in iter(p.stderr.readline, b''):
                    if err:
                        print(err.decode('utf-8'), end='')
                print()

                p.stdout.close()
                p.stderr.close()
                p.wait()
