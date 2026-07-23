import os


class Metadata(object):

    @classmethod
    def _package_installed(cls, package):
        """Returns True if the package is already installed."""

        package_map = {
            "GitPython": "git",
        }

        module_name = package_map.get(package, package)

        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
        
    @classmethod
    def install_required(cls, pip_command, vendor_path, path):
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
            import subprocess
            for package in pylibs:
                package = package.strip()

                if cls._package_installed(package):
                    print(f"{package} already installed")
                    continue

                if 'PYTHONHOME' in os.environ:
                    del os.environ['PYTHONHOME']

                command = list(pip_command)

                command.extend([
                    'install',
                    '--disable-pip-version-check',
                    '--target',
                    str(vendor_path),
                    package
                ])

                print(f"Installing {package}")

                p = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
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
                if p.returncode != 0:
                    print(f"Failed installing {package} (exit code {p.returncode})")