# FreeCAD init script of the WebTools module  

#***************************************************************************
#*   (c) Yorik van Havre <yorik@uncreated.net> 2017                        *   
#*                                                                         *
#*   This file is part of the FreeCAD CAx development system.              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   FreeCAD is distributed in the hope that it will be useful,            *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        * 
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Lesser General Public License for more details.                   *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with FreeCAD; if not, write to the Free Software        * 
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************/

class WebToolsWorkbench (Workbench):
    "Web workbench object"
    def __init__(self):
        self.__class__.Icon = FreeCAD.getResourceDir() + "Mod/Web/Resources/icons/WebWorkbench.svg"
        self.__class__.MenuText = "WebTools"
        self.__class__.ToolTip = "WebTools workbench"

    def Initialize(self):
        import BIMServer, Git, Sketchfab
        cmds = ["WebTools_Git","WebTools_BimServer","WebTools_Sketchfab"] #,"WebTools_Speckle"]
        self.appendToolbar("Web tools",cmds)
        self.appendMenu("Web &Tools",cmds)

    def GetClassName(self):
        return "Gui::PythonWorkbench"

Gui.addWorkbench(WebToolsWorkbench())
