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
    

__title__="FreeCAD Git commands"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"


class CommandGit:
    
    "the WebTools_Git command definition"
    
    def GetResources(self):
        return {'Pixmap'  : os.path.join(os.path.dirname(__file__),"icons",'git.svg'),
                'MenuText': QtCore.QT_TRANSLATE_NOOP("WebTools_Git","Git"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("WebTools_Git","Manages the current document with Git")}

    def Activated(self):
        f = FreeCAD.ActiveDocument.FileName
        if not f:
            FreeCAD.Console.PrintError(translate("WebTools","This document is not saved. Please save it first.\n"))
            return
        try:
            import git
        except:
            FreeCAD.Console.PrintError(translate("WebTools","The Python Git module was not found. Please install the python-git package.\n"))
            return
        try:
            repo = git.Repo(os.path.dirname(f), search_parent_directories=True)
        except:
            FreeCAD.Console.PrintError(translate("WebTools","This document doesn't appear to be part of a Git repository.\n"))
            return
        else:
            FreeCADGui.Control.showDialog(GitTaskPanel(repo))


class GitTaskPanel:
    
    '''The TaskPanel for the Git command'''
    
    def __init__(self,repo):
        self.form = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","TaskGit.ui"))
        self.form.setWindowIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__),"icons","git.svg")))
        self.form.labelStatus.setText("")
        QtCore.QObject.connect(self.form.buttonRefresh, QtCore.SIGNAL("clicked()"), self.getFiles)
        QtCore.QObject.connect(self.form.buttonLog, QtCore.SIGNAL("clicked()"), self.getLog)
        QtCore.QObject.connect(self.form.buttonSelectAll, QtCore.SIGNAL("clicked()"), self.form.listFiles.selectAll)
        QtCore.QObject.connect(self.form.buttonDiff, QtCore.SIGNAL("clicked()"), self.getDiff)
        QtCore.QObject.connect(self.form.buttonCommit, QtCore.SIGNAL("clicked()"), self.commit)
        QtCore.QObject.connect(self.form.buttonPush, QtCore.SIGNAL("clicked()"), self.push)
        QtCore.QObject.connect(self.form.buttonPull, QtCore.SIGNAL("clicked()"), self.pull)
        self.repo = repo
        self.getRemotes()
        self.getFiles()

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Close)

    def accept(self):
        FreeCADGui.Control.closeDialog()
        
    def getFiles(self):
        self.form.labelStatus.setText("")
        self.form.listFiles.clear()
        self.modified = self.repo.git.diff("--name-only").split()
        self.untracked = self.repo.git.ls_files("--other","--exclude-standard").split()
        for f in self.modified:
            self.form.listFiles.addItem(f)
        for f in self.untracked:
            self.form.listFiles.addItem(f+" *")
        self.form.labelStatus.setText(translate("WebTools","Branch")+": "+self.repo.active_branch.name)

    def getLog(self):
        textform = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","DialogDisplayText.ui"))
        textform.setWindowTitle("Git log")
        textform.browserText.setPlainText(self.repo.git.log())
        textform.exec_()
        
    def getDiff(self):
        if (self.form.listFiles.currentRow() >= 0):
            f = (self.modified+self.untracked)[self.form.listFiles.currentRow()]
            textform = FreeCADGui.PySideUic.loadUi(os.path.join(os.path.dirname(__file__),"ui","DialogDisplayText.ui"))
            textform.setWindowTitle("Diff: "+f)
            textform.browserText.setPlainText(self.repo.git.diff(f))
            textform.exec_()
            
    def getRemotes(self):
        self.form.listRepos.clear()
        if self.repo.remotes:
            for r in self.repo.remotes:
                self.form.listRepos.addItem(r.name+": "+r.url)
        else:
            FreeCAD.Console.PrintWarning(translate("WebTools","Warning: no remote repositories.\n"))
            
    def commit(self):
        if not self.form.listFiles.selectedItems():
            FreeCAD.Console.PrintError(translate("WebTools","Please select file(s) to commit.\n"))
            self.form.labelStatus.setText(translate("WebTools","No file selected"))
            return
        if not self.form.editMessage.text():
            FreeCAD.Console.PrintError(translate("WebTools","Please write a commit message.\n"))
            self.form.labelStatus.setText(translate("WebTools","No commit message"))
            return
        for it in self.form.listFiles.selectedItems():
            f = it.text()
            if f[-2:] == " *":
                f = f[:-2]
            self.repo.git.add(f)
        s = self.repo.git.commit(m=self.form.editMessage.text())
        FreeCAD.Console.PrintMessage(translate("WebTools","Successfully committed %i files.\n") % len(self.form.listFiles.selectedItems()))
        self.form.labelStatus.setText(translate("WebTools","Files committed."))
        if s:
            FreeCAD.Console.PrintMessage(s+"\n")
        self.getFiles()
        
    def push(self):
        if len(self.form.listRepos.selectedItems()) != 1:
            FreeCAD.Console.PrintError(translate("WebTools","Please select a repo to push to.\n"))
            self.form.labelStatus.setText(translate("WebTools","No repo selected"))
            return
        self.form.labelStatus.setText(translate("WebTools","Pushing files..."))
        r = self.form.listRepos.selectedItems()[0].text().split(":")[0]
        s = self.repo.git.push(r)
        FreeCAD.Console.PrintMessage(translate("WebTools","Successfully pushed to")+" "+r+"\n")
        self.form.labelStatus.setText(translate("WebTools","Files pushed."))
        if s:
            FreeCAD.Console.PrintMessage(s+"\n")
        self.getFiles()
        
    def pull(self):
        if len(self.form.listRepos.selectedItems()) != 1:
            FreeCAD.Console.PrintError(translate("WebTools","Please select a repo to pull from.\n"))
            self.form.labelStatus.setText(translate("WebTools","No repo selected"))
            return
        self.form.labelStatus.setText(translate("WebTools","Pulling files..."))
        r = self.form.listRepos.selectedItems()[0].text().split(":")[0]
        s = self.repo.git.pull(r)
        FreeCAD.Console.PrintMessage(translate("WebTools","Successfully pulled from")+" "+r+"\n")
        self.form.labelStatus.setText(translate("WebTools","Files pulled."))
        if s:
            FreeCAD.Console.PrintMessage(s+"\n")
        if os.path.basename(FreeCAD.ActiveDocument.FileName) in s:
            FreeCAD.Console.PrintWarning(translate("WebTools","Warning: the current document file has been changed by this pull. Please save your document to keep your changes.\n"))



if FreeCAD.GuiUp:

    FreeCADGui.addCommand('WebTools_Git',CommandGit())
