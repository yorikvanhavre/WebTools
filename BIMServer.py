#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2015 Yorik van Havre <yorik@uncreated.net>              *
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

import FreeCAD, os, time, tempfile, base64, Draft
from PySide import QtCore, QtGui

if FreeCAD.GuiUp:
    import FreeCADGui
    from DraftTools import translate
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt,txt):
        return txt
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    # \endcond


__title__="FreeCAD BimServer command"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"


class CommandBimServer:

    "the WebTools_BimServer command definition"

    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons",'bimserver.svg'),
                'MenuText': QT_TRANSLATE_NOOP("WebTools_BimServer","BIM server"),
                'ToolTip': QT_TRANSLATE_NOOP("WebTools_BimServer","Connects and interacts with a BIM server instance")}

    def Activated(self):
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
            FreeCADGui.Control.showDialog(BimServerTaskPanel())


class BimServerTaskPanel:

    '''The TaskPanel for the BimServer command'''

    def __init__(self):
        self.form = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","TaskBimServer.ui"))
        self.form.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),"icons","bimserver.svg")))
        self.form.labelStatus.setText("")
        QtCore.QObject.connect(self.form.buttonServer, QtCore.SIGNAL("clicked()"), self.login)
        QtCore.QObject.connect(self.form.buttonBrowser, QtCore.SIGNAL("clicked()"), self.browse)
        QtCore.QObject.connect(self.form.comboProjects, QtCore.SIGNAL("currentIndexChanged(int)"), self.getRevisions)
        QtCore.QObject.connect(self.form.buttonOpen, QtCore.SIGNAL("clicked()"), self.openFile)
        QtCore.QObject.connect(self.form.buttonUpload, QtCore.SIGNAL("clicked()"), self.uploadFile)
        self.prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Arch")
        self.Projects = []
        self.Revisions = []
        self.RootObjects = Draft.getObjectsOfType(FreeCAD.ActiveDocument.Objects,"Site")+Draft.getObjectsOfType(FreeCAD.ActiveDocument.Objects,"Building")
        self.RootObjects += Draft.getObjectsOfType(FreeCAD.ActiveDocument.Objects,"IfcSite")+Draft.getObjectsOfType(FreeCAD.ActiveDocument.Objects,"IfcBuilding")
        for o in self.RootObjects:
            self.form.comboRoot.addItem(o.Label)
        self.setLogged(False)
        url,token = self.getPrefs()
        if url and token:
            self.getProjects()

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Close)

    def accept(self):
        FreeCADGui.Control.closeDialog()

    def getPrefs(self):
        url = self.prefs.GetString("BimServerUrl","http://localhost:8082")
        if hasattr(self,"token"):
            token = self.token
        else:
            token = self.prefs.GetString("BimServerToken","")
            if token:
                self.token = token
        return url,token

    def setLogged(self,logged):
        if logged:
            self.form.buttonServer.setText("Connected")
            self.form.buttonServer.setIcon(QtGui.QIcon(":/icons/edit_OK.svg"))
            self.form.buttonServer.setToolTip("Click to log out")
            self.Connected = True
        else:
            self.form.buttonServer.setText("Not connected")
            self.form.buttonServer.setIcon(QtGui.QIcon(":/icons/edit_Cancel.svg"))
            self.form.buttonServer.setToolTip("Click to log in")
            self.Connected = False

    def login(self):
        self.setLogged(False)
        self.form.labelStatus.setText("")
        if self.Connected:
            # if the user pressed logout, delete the token
            self.prefs.SetString("BimServerToken","")
        else:
            url,token = self.getPrefs()
            loginform = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","DialogBimServerLogin.ui"))
            loginform.editUrl.setText(url)
            dlg = loginform.exec_()
            if dlg:
                url = loginform.editUrl.text()
                login = loginform.editLogin.text()
                passwd = loginform.editPassword.text()
                store = loginform.checkStore.isChecked()
                import requests, json
                self.form.labelStatus.setText("Logging in...")
                url2 = url + "/json"
                data = {'request': {'interface': 'AuthInterface', 'method': 'login', 'parameters': {'username': login, 'password': passwd}}}
                try:
                    resp = requests.post(url2,data = json.dumps(data))
                except:
                    FreeCAD.Console.PrintError(translate("WebTools","Unable to connect to BimServer at")+" "+url+"\n")
                    self.form.labelStatus.setText(translate("WebTools","Connection failed."))
                    return
                if resp.ok:
                    try:
                        token = resp.json()["response"]["result"]
                    except:
                        return
                    else:
                        if store:
                            self.prefs.SetString("BimServerUrl",url)
                            if token:
                                self.prefs.SetString("BimServerToken",token)
                        else:
                            self.prefs.SetString("BimServerToken","")
                        if token:
                            self.token = token
                            self.getProjects()
        self.form.labelStatus.setText("")

    def browse(self):
        url = self.prefs.GetString("BimServerUrl","http://localhost:8082")+"/apps/bimviews"
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url, QtCore.QUrl.TolerantMode))

    def getProjects(self):
        self.setLogged(False)
        self.Projects = []
        self.form.labelStatus.setText("")
        import requests, json
        url,token = self.getPrefs()
        if url and token:
            self.form.labelStatus.setText(translate("WebTools","Getting projects list..."))
            url += "/json"
            data = { "token": token, "request": { "interface": "SettingsInterface", "method": "getServerSettings", "parameters": { } } }
            try:
                resp = requests.post(url,data = json.dumps(data))
            except:
                FreeCAD.Console.PrintError(translate("WebTools","Unable to connect to BimServer at")+" "+url[:-5]+"\n")
                self.form.labelStatus.setText(translate("WebTools","Connection failed."))
                return
            if resp.ok:
                try:
                    name = resp.json()["response"]["result"]["name"]
                except:
                    pass # unable to get the server name
                else:
                    self.form.labelServerName.setText(name)
            data = { "token": token, "request": { "interface": "ServiceInterface", "method": "getAllProjects", "parameters": { "onlyTopLevel": "false", "onlyActive": "true" } } }
            resp = requests.post(url,data = json.dumps(data))
            if resp.ok:
                try:
                    projects = resp.json()["response"]["result"]
                except:
                    FreeCAD.Console.PrintError(translate("WebTools","Unable to get projects list from BimServer\n"))
                else:
                    self.setLogged(True)
                    self.form.comboProjects.clear()
                    for p in projects:
                        self.form.comboProjects.addItem(p["name"])
                    self.Projects = projects
                    self.form.comboProjects.setCurrentIndex(0)
                    self.getRevisions(0)
        self.form.labelStatus.setText("")

    def getRevisions(self,index):
        self.form.labelStatus.setText("")
        self.form.listRevisions.clear()
        self.Revisions = []
        import requests, json
        url,token = self.getPrefs()
        if url and token:
            url += "/json"
            if (index >= 0) and (len(self.Projects) > index):
                p = self.Projects[index]
                self.form.labelStatus.setText(translate("WebTools","Getting revisions..."))
                for rev in p["revisions"]:
                    data = { "token": token, "request": { "interface": "ServiceInterface", "method": "getRevision", "parameters": { "roid": rev } } }
                    resp = requests.post(url,data = json.dumps(data))
                    if resp.ok:
                        try:
                            name = resp.json()["response"]["result"]["comment"]
                            date = resp.json()["response"]["result"]["date"]
                        except:
                            pass # unable to get the revision
                        else:
                            date = time.strftime("%a %d %b %Y %H:%M:%S GMT", time.gmtime(int(date)/1000.0))
                            self.form.listRevisions.addItem(date+" - "+name)
                            self.Revisions.append(resp.json()["response"]["result"])
        self.form.labelStatus.setText("")

    def openFile(self):
        self.form.labelStatus.setText("")
        if (self.form.listRevisions.currentRow() >= 0) and (len(self.Revisions) > self.form.listRevisions.currentRow()):
            rev = self.Revisions[self.form.listRevisions.currentRow()]
            import requests, json
            url,token = self.getPrefs()
            if url and token:
                FreeCAD.Console.PrintMessage(translate("WebTools","Downloading file from Bimserver...\n"))
                self.form.labelStatus.setText(translate("WebTools","Checking available serializers..."))
                url += "/json"
                serializer = None
                for s in ["Ifc2x3tc1"]: # Ifc4 seems unreliable ATM, let's stick with good old Ifc2x3...
                    data = { "token": token, "request": { "interface": "ServiceInterface", "method": "getSerializerByName", "parameters": { "serializerName": s } } }
                    resp = requests.post(url,data = json.dumps(data))
                    if resp.ok:
                        try:
                            srl = resp.json()["response"]["result"]
                        except:
                            pass # unable to get this serializer
                        else:
                            serializer = srl
                            break
                if not serializer:
                    FreeCAD.Console.PrintError(translate("WebTools","Unable to get a valid serializer from the BimServer\n"))
                    return
                tf = QtGui.QFileDialog.getSaveFileName(QtGui.QApplication.activeWindow(), "Save the downloaded IFC file?", None, "IFC files (*.ifc)")
                if tf:
                    tf = tf[0]
                self.form.labelStatus.setText(translate("WebTools","Downloading file..."))
                data = { "token": token, "request": { "interface": "ServiceInterface", "method": "download", "parameters": { "roids": [rev["oid"]], "serializerOid": serializer["oid"], "query": "{\"includeAllFields\": true}", "sync": "false" } } }
                resp = requests.post(url,data = json.dumps(data))
                if resp.ok:
                    try:
                        downloadid = resp.json()["response"]["result"]
                    except:
                        FreeCAD.Console.PrintError(translate("WebTools","Unable to obtain a valid download for this revision from the BimServer\n"))
                        return
                data = { "token": token, "request": { "interface": "ServiceInterface", "method": "getDownloadData", "parameters": { "topicId": downloadid } } }
                resp = requests.post(url,data = json.dumps(data))
                if resp.ok:
                    try:
                        downloaddata = resp.json()["response"]["result"]["file"]
                    except:
                        FreeCAD.Console.PrintError(translate("WebTools","Unable to download the data for this revision.\n"))
                        return
                    else:
                        FreeCAD.Console.PrintMessage(translate("WebTools","Opening file...\n"))
                        self.form.labelStatus.setText(translate("WebTools","Opening file..."))
                        if not tf:
                            tf = tempfile.mktemp(suffix=".ifc")
                        f = open(tf,"wb")
                        f.write(base64.b64decode(downloaddata))
                        f.close()
                        import importIFC
                        importIFC.open(tf)
                        os.remove(tf) # why first ask for a name if we remove it anyway?
        self.form.labelStatus.setText("")

    def uploadFile(self):
        self.form.labelStatus.setText("")
        if (self.form.comboProjects.currentIndex() >= 0) and (len(self.Projects) > self.form.comboProjects.currentIndex()) and (self.form.comboRoot.currentIndex() >= 0):
            project = self.Projects[self.form.comboProjects.currentIndex()]
            import requests, json
            url,token = self.getPrefs()
            if url and token:
                url += "/json"
                deserializer = None
                FreeCAD.Console.PrintMessage(translate("WebTools","Saving file...\n"))
                self.form.labelStatus.setText(translate("WebTools","Checking available deserializers..."))
                import ifcopenshell
                schema = ifcopenshell.file().schema.lower()
                data = { "token": token, "request": { "interface": "PluginInterface",  "method": "getAllDeserializers", "parameters": { "onlyEnabled": "true" } } }
                resp = requests.post(url,data = json.dumps(data))
                if resp.ok:
                    try:
                        for d in resp.json()["response"]["result"]:
                            if schema in d["name"].lower():
                                deserializer = d
                                break
                    except:
                        pass
                if not deserializer:
                    FreeCAD.Console.PrintError(translate("WebTools","Unable to get a valid deserializer for the schema")+" "+schema+"\n")
                    return
                tf = QtGui.QFileDialog.getSaveFileName(QtGui.QApplication.activeWindow(), translate("WebTools","Save the IFC file before uploading?"), None, translate("WebTools","IFC files (*.ifc)"))
                comment = self.form.editComment.text()
                if tf and tf[0]:
                    tf = tf[0]
                    if not comment:
                        comment = os.path.basename(tf)
                else:
                    tf = tempfile.mktemp(suffix=".ifc")
                import exportIFC
                self.form.labelStatus.setText(translate("WebTools","Saving file..."))
                exportIFC.export([self.RootObjects[self.form.comboRoot.currentIndex()]],tf)
                f = open(tf,"rb")
                ifcdata = base64.b64encode(f.read()).decode("ascii")
                f.close()
                FreeCAD.Console.PrintMessage(translate("WebTools","Uploading file to Bimserver...\n"))
                self.form.labelStatus.setText(translate("WebTools","Uploading file..."))
                data = { "token": token, "request": { "interface": "ServiceInterface", "method": "checkinSync", "parameters": { "poid": project["oid"], "comment": comment, "deserializerOid": deserializer["oid"], "fileSize": os.path.getsize(tf), "fileName": os.path.basename(tf), "data": ifcdata, "merge": "false" } } }
                resp = requests.post(url,data = json.dumps(data))
                if resp.ok:
                    if "result" in resp.json()["response"]:
                        FreeCAD.Console.PrintMessage(translate("WebTools","File upload successful\n"))
                        self.getRevisions(self.form.comboProjects.currentIndex())
                    elif "exception" in resp.json()["response"]:
                        FreeCAD.Console.PrintError(translate("WebTools","File upload failed, caused by: ")+resp.json()["response"]["exception"]["message"]+"\n")
                    else:
                        FreeCAD.Console.PrintError(translate("WebTools","File upload failed\n"))
        self.form.labelStatus.setText("")


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('WebTools_BimServer',CommandBimServer())
