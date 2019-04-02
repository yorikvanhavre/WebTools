#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2017 - Yorik van Havre <yorik@uncreated.net>            *
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

from __future__ import print_function

__title__ = "Sketchfab uploader"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"

import FreeCAD, os, zipfile, requests, tempfile, json, time, re

if FreeCAD.GuiUp:
    import FreeCADGui, WebGui
    from PySide import QtCore, QtGui
    from PySide.QtCore import QT_TRANSLATE_NOOP
    from DraftTools import translate
else:
    # \cond
    def translate(ctxt,txt):
        return txt
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    # \endcond


SKETCHFAB_UPLOAD_URL = "https://api.sketchfab.com/v3/models"
SKETCHFAB_TOKEN_URL = "https://sketchfab.com/settings/password"
SKETCHFAB_MODEL_URL = "https://sketchfab.com/show/"


class CommandSketchfab:
    
    "the WebTools_BimServer command definition"
    
    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons",'sketchfab.svg'),
                'MenuText': QT_TRANSLATE_NOOP("WebTools_Sketchfab","Sketchfab"),
                'ToolTip': QT_TRANSLATE_NOOP("WebTools_Sketchfab","Connects and uploads a model to a Sketchfab account")}

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
            FreeCADGui.Control.showDialog(SketchfabTaskPanel())


class SketchfabTaskPanel:
    
    '''The TaskPanel for Sketchfab upload'''
    
    def __init__(self):
        
        self.url = None
        self.form = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","TaskSketchfab.ui"))
        self.form.ProgressBar.hide()
        self.form.Button_View.hide()
        self.form.fixLabel.hide()
        self.form.fixButton.hide()
        QtCore.QObject.connect(self.form.Button_Token,QtCore.SIGNAL("pressed()"),self.getToken)
        QtCore.QObject.connect(self.form.Button_Upload,QtCore.SIGNAL("pressed()"),self.upload)
        QtCore.QObject.connect(self.form.Button_View,QtCore.SIGNAL("pressed()"),self.viewModel)
        QtCore.QObject.connect(self.form.fixButton,QtCore.SIGNAL("pressed()"),self.fix)
        self.form.Text_Name.setText(FreeCAD.ActiveDocument.Label)
        self.form.Text_Token.setText(FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Web").GetString("SketchfabToken",""))

    def isAllowedAlterSelection(self):
        
        return True

    def isAllowedAlterView(self):
        
        return True

    def getStandardButtons(self):
        
        return int(QtGui.QDialogButtonBox.Close)

    def accept(self):
        
        FreeCADGui.ActiveDocument.resetEdit()
        return True

    def getToken(self):
        
        QtGui.QDesktopServices.openUrl(SKETCHFAB_TOKEN_URL)
        
    def get_request_payload(self, token, data={}, files={}, json_payload=False):
        
        """Helper method that returns the authentication token and proper content
        type depending on whether or not we use JSON payload."""
        headers = {'Authorization': 'Token {}'.format(token)}
        if json_payload:
            headers.update({'Content-Type': 'application/json'})
            data = json.dumps(data)
        return {'data': data, 'files': files, 'headers': headers}
        
    def saveFile(self):
        
        import FreeCADGui
        if self.form.Radio_Selection.isChecked():
            objects = FreeCADGui.Selection.getSelection()
        else:
            objects = [obj for obj in FreeCAD.ActiveDocument.Objects if obj.ViewObject.isVisible()]
        if not objects:
            QtGui.QMessageBox.critical(None,translate("WebTools","Nothing to upload"),translate("The selection of the document contains no object to upload"))
            return None
        filename = os.path.join(tempfile._get_default_tempdir(),next(tempfile._get_candidate_names()))
        filetype = self.form.Combo_Filetype.currentIndex()
        # 0 = obj + mtl, 1 = obj, 2 = dae, 3 = stl, 4 = IGES, 5 = iv (currently not working)
        if filetype == 0: # OBJ + MTL
            import importOBJ
            importOBJ.export(objects,filename+".obj")
            return self.packFiles(filename,[filename+".obj",filename+".mtl"])
        elif filetype == 1: # OBJ (mesh exporter)
            import Mesh
            Mesh.export(objects,filename+".obj")
            return self.packFiles(filename,[filename+".obj"])
        elif filetype == 2: # DAE
            import importDAE
            importDAE.export(objects,filename+".dae")
            return self.packFiles(filename,[filename+".dae"])
        elif filetype == 3: # STL
            import Mesh
            Mesh.export(objects,filename+".stl")
            return self.packFiles(filename,[filename+".stl"])
        elif filetype == 4: # IGES
            import Part
            Part.export(objects,filename+".iges")
            return self.packFiles(filename,[filename+".iges"])
        elif filetype == 5: # IV
            import FreeCADGui
            # remove objects with no face (unsupported by this format)
            nobjects = []
            for o in objects:
                if o.isDerivedFrom("Part::Feature"):
                    if o.Shape.Faces:
                        nobjects.append(o)
            FreeCADGui.export(nobjects,filename+".iv")
            # removing FreeCAD-specific nodes
            f = open(filename+".iv","rb")
            s = f.read()
            f.close()
            ver = FreeCAD.Version()
            vinfo = "# Exported by FreeCAD v" + ver[0] + "." + ver[1] + " build" + ver[2] + "\n"
            vinfo += "# http://www.freecadweb.org\n"
            s = s.replace("#Inventor V2.1 ascii","#Inventor V2.1 ascii\n"+vinfo)
            s = s.replace("SoBrepEdgeSet","IndexedLineSet")
            s = s.replace("SoBrepFaceSet","IndexedFaceSet")
            s = s.replace("SoBrepPointSet","IndexedPointSet")
            s = s.replace("\n","--endl--")
            s = re.sub("--endl--[ \t]+highlightIndex.*?--endl--","--endl--",s)
            s = re.sub("--endl--[ \t]+partIndex.*?--endl--","--endl--",s)
            s = re.sub("--endl--[ \t]+selectionIndex.*?--endl--","--endl--",s)
            s = re.sub("SFInt32 highlightIndex, ","",s)
            s = re.sub("MFInt32 partIndex, ","",s)
            s = re.sub("MFInt32 selectionIndex ","",s)
            s = re.sub(", \]"," \]",s)
            s = s.replace("--endl--","\n")
            f = open(filename+".iv","wb")
            f.write(s)
            f.close()
            print("saved "+filename+".iv")
            return self.packFiles(filename,[filename+".iv"])

    def packFiles(self,filename,fileslist):
        
        for f in fileslist:
            if not os.path.exists(f):
                return None
        z = zipfile.ZipFile(filename+".zip","w")
        for f in fileslist:
            z.write(f,os.path.basename(f))
        z.close()
        for f in fileslist:
            os.remove(f)
        s = os.path.getsize(filename+".zip")
        if s > 1048576:
            size = str(s >> 20)+" MB"
        else:
            size = str(s >> 10)+" KB"
        return (filename+".zip",size)

    def upload(self):

        if not self.form.Text_Name.text():
            QtGui.QMessageBox.critical(None,translate("WebTools","Model name is empty"),translate("You must provide a name for your model"))
            return
        if not self.form.Text_Token.text():
            QtGui.QMessageBox.critical(None,translate("WebTools","No token provided"),translate("The token is empty. Please press the Obtain button to get your user API token from Sketchfab, then copy / paste the API token to the field below"))
            return
            
        # saving file
        FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Web").SetString("SketchfabToken",self.form.Text_Token.text())
        pack = self.saveFile()
        if not pack:
            QtGui.QMessageBox.critical(None,translate("WebTools","File packing error"),translate("Unable to save and zip a file for upload"))
            return
            
        # preparing model data
        if os.path.getsize(pack[0]) >= 52428800:
            b = QtGui.QMessageBox()
            b.setText(translate("WebTools","Big upload"))
            b.setInformativeText(translate("WebTools","The file to be uploaded is %s, which is above the maximum 50Mb allowed by free Sketchfab accounts. Pro accounts allow for up to 200Mb. Continue?") % pack[1])
            b.setStandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            b.setDefaultButton(QtGui.QMessageBox.Cancel)
            ret = b.exec_()
            if ret != QtGui.QMessageBox.Ok:
                return            
        data = {
            "name": self.form.Text_Name.text(),
            "description": self.form.Text_Description.text(),
            "tags": ["freecad"]+[t.strip() for t in self.form.Text_Tags.text().split(",")],
            "private": self.form.Check_Private.isChecked(),
            "source":"freecad",
            }
        files = {
            "modelFile": open(pack[0], 'rb')
            }
            
        # performing upload
        self.form.Button_Upload.hide()
        # for now this is a fake progress bar, it won't move, just to show the user that the upload is in progress
        self.form.ProgressBar.setFormat(translate("WebTools","Uploading")+" "+pack[1]+"...")
        self.form.ProgressBar.show()
        QtGui.QApplication.instance().processEvents()
        try:
            r = requests.post(SKETCHFAB_UPLOAD_URL, **self.get_request_payload(self.form.Text_Token.text(), data, files=files))
        except requests.exceptions.RequestException as e:
            QtGui.QMessageBox.critical(None,translate("WebTools","Upload error"),translate("WebTools","Upload failed:")+" "+str(e))
            self.form.ProgressBar.hide()
            self.form.Button_Upload.show()
            return
        if r.status_code != requests.codes.created:
            QtGui.QMessageBox.critical(None,translate("WebTools","Upload error"),translate("WebTools","Upload failed:")+" "+str(r.json()))
            self.form.ProgressBar.hide()
            self.form.Button_Upload.show()
            return
        self.url = r.headers['Location']
        
        # patching model
        if self.form.Combo_Filetype.currentIndex() in [0,1,5]: # OBJ and IV formats: sketchfab expects inverted Y/Z axes
            self.form.fixLabel.show()
            self.form.fixButton.show()
        self.form.ProgressBar.hide()
        self.form.Button_View.show()
        
    def fix(self):
        
        self.form.ProgressBar.show()
        self.form.ProgressBar.setFormat(translate("WebTools","Awaiting confirmation..."))
        self.form.ProgressBar.setValue(75)
        if self.poll(self.url):
            self.form.ProgressBar.setFormat(translate("WebTools","Fixing model..."))
            QtGui.QApplication.instance().processEvents()
            self.patch(self.url)
        else:
            QtGui.QMessageBox.warning(None,translate("WebTools","Patch error"),translate("WebTools","Patching failed. The model was successfully uploaded, but might still require manual adjustments."))
        self.form.ProgressBar.hide()
        
    def poll(self,url):
        
        """GET the model endpoint to check the processing status."""
        max_errors = 10
        errors = 0
        retry = 0
        max_retries = 50
        retry_timeout = 5  # seconds
        while (retry < max_retries) and (errors < max_errors):
            try:
                r = requests.get(url, **self.get_request_payload(self.form.Text_Token.text()))
            except requests.exceptions.RequestException as e:
                print ('Sketchfab: Polling failed with error: ',str(e))
                errors += 1
                retry += 1
                continue
            result = r.json()
            if "error" in result:
                e = result["error"]
            else:
                e = result
            if r.status_code != requests.codes.ok:
                print ('Sketchfab: Polling failed with error: ',str(e))
                errors += 1
                retry += 1
                continue
            processing_status = result['status']['processing']
            if processing_status == 'PENDING':
                retry += 1
                time.sleep(retry_timeout)
                continue
            elif processing_status == 'PROCESSING':
                retry += 1
                time.sleep(retry_timeout)
                continue
            elif processing_status == 'FAILED':
                print ('Sketchfab: Polling failed: ',str(e))
                return False
            elif processing_status == 'SUCCEEDED':
                return True
            retry += 1
        print ('Sketchfab: Stopped polling after too many retries or too many errors')
        return False
        
    def patch(self,url):
        
        "applies different fixes to the uploaded model"
        options_url = os.path.join(url, 'options')
        data = {
            'orientation': '{"axis": [1, 0, 0], "angle": 270}'
            }
        try:
            r = requests.patch(options_url, **self.get_request_payload(self.form.Text_Token.text(), data, json_payload=True))
        except requests.exceptions.RequestException as e:
            QtGui.QMessageBox.warning(None,translate("WebTools","Patch error"),translate("WebTools","Patching failed. The model was successfully uploaded, but might still require manual adjustments:")+" "+str(e))
        else:
            if r.status_code != 204:
                QtGui.QMessageBox.warning(None,translate("WebTools","Patch error"),translate("WebTools","Patching failed. The model was successfully uploaded, but might still require manual adjustments:")+" "+str(r.content))

    def viewModel(self):
        
        if self.url:
            url = self.url.replace("api","www")
            url = url.replace("/v3","")
            QtGui.QDesktopServices.openUrl(url)


if FreeCAD.GuiUp:

    FreeCADGui.addCommand('WebTools_Sketchfab',CommandSketchfab())


