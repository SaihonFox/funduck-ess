import common as cmn
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QLineEdit, QPlainTextEdit, QApplication
from objects import gstate, ESGoal, kProgramName
import sys

def checkGoalName(name, allow_same=False):
    if not name: return 'Goal name cannot be empty'
    if allow_same: return
    for g in gstate.goalsMap().values():
        if g.name == name: return 'A goal with this name already exists'
    return None

class GoalDialog(cmn.Dialog):
    def __init__(self, obj=None):
        cmn.Dialog.__init__(self, 'ESS', 'GoalAdd', 'Add a Goal' if obj is None else 'Edit Goal')
        self.obj = obj
        self.edit_name = QLineEdit()
        self.edit_descr = QPlainTextEdit()
        self.new_obj = None
        
        layout = cmn.Table([
            ('Name', self.edit_name),
            ('Description', self.edit_descr) 
        ])
        self.setDialogLayout(layout, self.doOk)
        
        if obj is not None:
            self.edit_name.setText(obj.name)
            self.edit_descr.setPlainText(obj.descr)
    
    def doOk(self):
        name = self.edit_name.text().strip()
        descr = self.edit_descr.toPlainText().strip()
        err = checkGoalName(name, self.obj is not None)
        if err is not None:
            self.sbar.showMessage(err)
            return
        gstate.beginTransaction()
        try:
            if self.obj is None:
                goal = ESGoal(None, name, descr)
                gstate.addNewObject(goal)
                self.new_obj = goal
            else:
                gstate.modifyObject(self.obj)
                self.obj.name = name
                self.obj.descr = descr
        finally:
            gstate.endTransaction()
        self.accept()

class GoalsDialog(cmn.Dialog):
    def __init__(self, is_selecting=False):
        cmn.Dialog.__init__(self, 'ESS', 'Goals', 'Select a Goal' if is_selecting else 'Goals')
        self.is_selecting = is_selecting
        toolbar = cmn.ToolBar([
            cmn.Action(self, 'Add a goal (Ins)', 'icons/add.png', self.addGoal, 'Insert'),
            cmn.Action(self, 'Edit goal (Enter)', 'icons/edit.png', self.editGoalAction),
            cmn.Action(self, 'Delete goal (Del)', 'icons/delete.png', self.removeGoal, 'Delete')
        ])
        self.list = QListWidget(self)
        self.list.itemActivated.connect(self.onActivateItem)
        self.loadList()
        layout = cmn.VBox([toolbar, self.list], spacing=0)
        self.setDialogLayout(layout, self.doSelect, close_btn=not is_selecting, autodefault=False)

    def doSelect(self):
        cur = self.list.currentItem()
        if not cur:
            self.sbar.showMessage('You should select a goal first')
            return
        self.selected_item = cur.data(Qt.UserRole)
        self.accept()
        
    def loadList(self, cur_obj=None):
        if not cur_obj and self.list.currentItem():
            cur_obj = self.list.currentItem().data(Qt.UserRole)
         
        self.list.clear()
        for g in gstate.goalsMap().values():
            item = QListWidgetItem(g.name)
            item.setData(Qt.UserRole, g)
            self.list.addItem(item)
            if g == cur_obj:
                self.list.setCurrentItem(item)
        self.list.sortItems(Qt.AscendingOrder)
        if self.list.currentItem():
            self.list.scrollToItem(self.list.currentItem())
    
    def addGoal(self):
        d = GoalDialog()
        if d.exec_():
            self.loadList(d.new_obj)

    def onActivateItem(self, item):
        if self.is_selecting:
            self.doSelect()
        else:
            self.editGoal(item)
        
    def editGoalAction(self):
        cur = self.list.currentItem()
        if cur:
            self.editGoal(cur)
    
    def editGoal(self, item):
        if GoalDialog(item.data(Qt.UserRole)).exec_():
            self.loadList()
    
    def removeGoal(self):
        cur = self.list.currentItem()
        if cur is None:
            return
        if gstate.hasInTree(cur.data(Qt.UserRole)):
            QMessageBox.warning(self, kProgramName, 'This goal is used in the tree and cannot be deleted')
            return
        gstate.deleteObject(cur.data(Qt.UserRole))
        self.loadList()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gstate.resetState()
    gstate.addNewObject(ESGoal(None, 'Ice cream'))
    gstate.addNewObject(ESGoal(None, 'Taco'))
    d = GoalsDialog()
    d.exec_()