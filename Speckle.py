#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2018 Yorik van Havre <yorik@uncreated.net>              *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import os, requests, xml.sax, uuid


### Generic Speckle interface (doesn't depend on FreeCAD)


def register(email,name,surname,company,password):
    
    data = {"email":email,"name":name,"surname":surname,"company":company,"password":password}
    r = requests.post(url='http://localhost:3000/api/accounts/register',data=data)

    if r.json()["success"] == True:
        return r.json()["token"]
    else:
        print(r.json()["message"])
        return False


def login(email,password):
    
    data = {"email":email,"password":password}
    r = requests.post(url='http://localhost:3000/api/accounts/login',data=data)

    if r.json()["success"] == True:
        #print r.json()["apiToken"]
        return r.json()["token"]
    else:
        print(r.json()["message"])
        return False


def getStreams(token):
    
    r = requests.get(url='http://localhost:3000/api/accounts/streams',headers={"Authorization":token})
    
    if r.json()["success"] == True:
        return r.json()["streams"]
    else:
        print(r.json()["message"])
        return False


def getSharedStreams(token):
    
    r = requests.get(url='http://localhost:3000/api/accounts/streams',headers={"Authorization":token})
    
    if r.json()["success"] == True:
        return r.json()["sharedStreams"]
    else:
        print(r.json()["message"])
        return False


def createStream(token,name="test"):
    
    headers = {"Authorization":token}
    data = {"_id":"59ce300e7056224ff5eb06ae","name":name,"objects":[],"layers":[]}
    
    data={"_id": "59ce300e7056224ff5eb06ae",
          "owner": "string",
          "private": True,
          "anonymousComments": True,
          "canRead": ["string"],
          "canWrite": ["string"],
          "comments": ["string"],
          "deleted": False,
          "streamId": "string",
          "name": "string",
          "objects": [ {"_id": "string",
                        "owner": "string",
                        "private": True,
                        "anonymousComments": True,
                        "canRead": ["string"],
                        "canWrite": ["string"],
                        "comments": ["string"],
                        "deleted": False,
                        "type": "Null",
                        "hash": "hash",
                        "geometryHash": "Type.hash",
                        "applicationId": "GUID",
                        "properties": {},
                        "parent": "string",
                        "children": ["string"],
                        "ancestors": ["string"] } ],
          "layers": [ { "name": "string",
                        "guid": "string",
                        "orderIndex": 0,
                        "startIndex": 0,
                        "objectCount": 0,
                        "topology": "string" } ],
          "baseProperties": {},
          "globalMeasures": {},
          "isComputedResult": False,
          "viewerLayers": [ {} ],
          "parent": "string",
          "children": ["string"],
          "ancestors": ["string"]}
    
    r = requests.post(url='http://localhost:3000/api/streams',data=data,headers=headers)
    return r
    if r.json()["success"] == True:
        return r.json()["streams"]
    else:
        print(r.json()["message"])
        return False


### FreeCAD <-> json conversion tools


def jsonify(obj):
    
    result = {"typeid":obj.TypeId}
    if hasattr(obj,"Name"):
        result["name"] = obj.Name
    reader = FCObjectReader(obj)
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, 0)
    parser.setContentHandler(reader)
    parser.parse(obj.Content)
    result["extensions"] = reader.extensions
    result["properties"] = reader.properties
    return result


### FreeCAD-specific interface


class FCObjectReader(xml.sax.ContentHandler):

    def __init__(self,obj):
        self.obj = obj
        self.extensions = []
        self.properties = []
        self.property = None
        self.enums = []

    def startElement(self, tag, attributes):
        if tag == "Extension":
            self.extensions.append(attributes)
        elif tag == "Property":
            self.property = attributes
            if attributes["type"] == "Part::PropertyPartShape":
                shape = getattr(self.obj,attributes["name"])
                if shape:
                    self.property["brep"] = shape.exportBrepToString()
        elif tag == "Enum":
            self.enums.append(attributes["value"])
        else:
            self.property.update(attributes)

    def endElement(self, tag):
        if tag == "Property":
            if self.property:
                self.properties.append(self.property)
        elif tag == "CustomEnumList":
            self.property["enumValues"] = self.enums
            self.enums = []



class CommandSpeckle:
    
    "the WebTools_Speckle command definition"
    
    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons",'speckle.svg'),
                'MenuText': QT_TRANSLATE_NOOP("WebTools_Speckle","Speckle.Works"),
                'ToolTip': QT_TRANSLATE_NOOP("WebTools_Speckle","Connects and interacts with a Specke.Works server instance")}

    def Activated(self):
        import FreeCAD
        try:
            import requests
        except:
            FreeCAD.Console.PrintError(translate("WebTools","requests python module not found, aborting. Please install python-requests\n"))
            return
        try:
            import json
        except:
            FreeCAD.Console.PrintError(translate("WebTools","json python module not found, aborting. Please install python-json\n"))
        else:
            FreeCADGui.Control.showDialog(SpeckleTaskPanel())


class SpeckleTaskPanel:


    def __init__(self):

        import FreeCAD, FreeCADGui
        from PySide import QtCore, QtGui
        self.form = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"dialogSpeckle.ui"))
        self.form.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),"icons","Speckle.svg")))
        self.prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/WebTools")
        



try:
    import FreeCAD
except:
    pass
else:
    if FreeCAD.GuiUp:
        import FreeCADGui
        FreeCADGui.addCommand('WebTools_Speckle',CommandSpeckle())
