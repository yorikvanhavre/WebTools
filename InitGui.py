# FreeCAD init script of the WebTools module  

# ***************************************************************************
# *   (c) Yorik van Havre <yorik@uncreated.net> 2017                        *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************/

import FreeCADGui
import FreeCAD
import os, sys

class WebToolsWorkbench(FreeCADGui.Workbench):
    """Web workbench object"""

    def __init__(self):
        self.__class__.Icon = os.path.join(self.get_workbench_directory(), "icons/webTools.svg")
        self.__class__.MenuText = "WebTools"
        self.__class__.ToolTip = "WebTools workbench"

        from pathlib import Path as pyPath
        import addonmanager_utilities as utils
        import tools.metadata as metadata

        # Determine how to invoke pip.
        # Older Addon Manager versions expose get_python_exe().
        # When unavailable, fall back to sys.executable.

        if hasattr(utils, "get_python_exe"):

            # Original behaviour.
            python_exe = pyPath(utils.get_python_exe())
            pip_command = [str(python_exe.with_stem("pip"))]

        else:
            # Fallback for newer Addon Manager versions.
            # Some FreeCAD installations expose FreeCAD.exe as sys.executable.
            # Use the bundled Python interpreter when available.
            python_exe = pyPath(sys.executable)

            if python_exe.name.lower() == "freecad.exe":
                bundled_python = python_exe.with_name("python.exe")
                if bundled_python.exists():
                    python_exe = bundled_python

            pip_command = [
                str(python_exe),
                "-m",
                "pip"
            ]

        vendor_path = pyPath(utils.get_pip_target_directory()).resolve()
        vendor_path.mkdir(parents=True, exist_ok=True)

        metadata.Metadata.install_required(
            pip_command,
            vendor_path,
            self.get_workbench_directory()
        )

    @classmethod
    def get_workbench_directory(cls):
        """Safely get the workbench directory path"""
        try:
            # Method 1: Try __file__ in function scope
            return os.path.dirname(__file__)
        except NameError:
            try:
                # Method 2: Use sys.modules
                module = sys.modules.get(__name__)
                if module and hasattr(module, '__file__'):
                    return os.path.dirname(module.__file__)
            except:
                pass

            try:
                # Method 3: Use inspect
                import inspect
                frame = inspect.currentframe()
                return os.path.dirname(inspect.getfile(frame))
            except:
                pass

            # Method 4: Fallback to known location
            return os.path.join(FreeCAD.getUserAppDataDir(), "Mod", "WebTools")

    def Initialize(self):
        # Do not remove imports
        import BIMServer, Git, Sketchfab
        cmds = ["WebTools_Git", "WebTools_BimServer", "WebTools_Sketchfab"]  # ,"WebTools_Speckle"]
        self.appendToolbar("Web tools", cmds)
        self.appendMenu("Web & Tools", cmds)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(WebToolsWorkbench())
