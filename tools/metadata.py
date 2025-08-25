import os


class Metadata(object):

    @classmethod
    def install_required(cls, pip_exe, vendor_path, path):
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
            for package in pylibs:
                package = package.strip()

                if 'PYTHONHOME' in os.environ:
                    del os.environ['PYTHONHOME']

                import subprocess
                p = subprocess.Popen(
                    [pip_exe, 'install', '--disable-pip-version-check', '--target', vendor_path, package],
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
