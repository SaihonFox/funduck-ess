import common as cmn
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QMessageBox, QLineEdit, QRadioButton, QApplication
from objects import gstate, ESFactor, kProgramName, ESNode
import sys

def checkFactorName(name, allow_same=False):
    if not name: return 'Factor name cannot be empty'
    if allow_same: return
    for g in gstate.factorsMap().values():
        if g.name == name: return 'Factor with this name already exists'
    return None

class FactorDialog(cmn.Dialog):
    def __init__(self, obj=None):
        cmn.Dialog.__init__(self, 'ESS', 'FactorAdd', 'Add a Factor' if obj is None else 'Edit Factor')
        self.init_done = False
        self.obj = obj
        self.edit_name = QLineEdit()
        
        def make_rb(text, checked=False):
            rb = QRadioButton(text)
            rb.toggled.connect(self.updateUI)
            rb.setChecked(checked)
            return rb
        
        self.edit_choices = cmn.Grid(['Values'], [500], True)
        self.edit_choices.cellChanged.connect(self.onCellChanged)
        self.rb_binary = make_rb('Binary', True)
        self.rb_text = make_rb('Text')
        
        self.new_obj = None
        layout = cmn.VBox([
            cmn.Table([('Name', self.edit_name),
                        ('Type', cmn.VBox([self.rb_binary, self.rb_text]) )]),
            self.edit_choices
        ])
        self.setDialogLayout(layout, self.doOk)
        
        choices = []        
        if obj is not None:
            self.edit_name.setText(obj.name)
            if not obj.is_binary:
                self.rb_text.setChecked(True)
                choices = obj.choices
            
        self.edit_choices.setTableData([[s] for s in choices] + [['']])
        self.init_done = True
        self.updateUI()
    
    def resizeEvent(self, ev):
        self.edit_choices.setColumnWidth(0, self.edit_choices.width())
        return cmn.Dialog.resizeEvent(self, ev)
        
    def updateUI(self):
        if self.init_done:
            self.edit_choices.setEnabled(self.rb_text.isChecked())

    def get_choice(self, i):
        item = self.edit_choices.item(i, 0)
        if item is None: return ''
        return item.text().strip()

    def onCellChanged(self):
        rc = self.edit_choices.rowCount()
        if rc == 0: return
        if self.get_choice(rc - 1):
            self.edit_choices.setRowCount(rc + 1)
            self.edit_choices.setCurrentCell(rc, 0)
            self.edit_choices.resizeRowToContents(rc)
    
    def doOk(self):
        name = self.edit_name.text().strip()
        is_binary = self.rb_binary.isChecked()
        
        if is_binary:
            choices = ESFactor.getBinaryChoices()
        else:
            choices = [self.get_choice(i) for i in range(self.edit_choices.rowCount())]
            choices = list(filter(None, choices))
        if len(choices) < 2:
            err = 'A factor should have at least two values'
        elif len(set(choices)) != len(choices):
            err = 'All values must be different'
        else:
            err = checkFactorName(name, self.obj is not None)
        if err is not None:
            self.sbar.showMessage(err)
            return
        gstate.beginTransaction()
        try:
            if self.obj is None:
                factor = ESFactor(None, name)
                gstate.addNewObject(factor)
                self.new_obj = factor
            else:
                factor = self.obj
                gstate.modifyObject(factor)
                factor.name = name
                
            factor.is_binary = is_binary
            
            def update_node(node):
                if node.content != factor: return
                gstate.modifyObject(node)
                while len(node.children) < len(choices):
                    node.children.append(gstate.addNewObject(ESNode()))
                while len(choices) < len(node.children):
                    gstate.deleteNode(node.children.pop())
                    
            if len(factor.choices) != len(choices):
                gstate.getRoot().traverse(update_node)
            factor.choices = choices
                
        finally:
            gstate.endTransaction()        
        self.accept()

class FactorsDialog(cmn.Dialog):
    def __init__(self, is_selecting=False):
        cmn.Dialog.__init__(self, 'ESS', 'Factors', 'Select a factor' if is_selecting else 'Factors')
        self.is_selecting = is_selecting
        toolbar = cmn.ToolBar([
            cmn.Action(self, 'Add a factor (Ins)', 'icons/add.png', self.addFactor, 'Insert'),
            cmn.Action(self, 'Edit factor (Enter)', 'icons/edit.png', self.editFactorAction),
            cmn.Action(self, 'Delete factor (Del)', 'icons/delete.png', self.removeFactor, 'Delete')
        ])
        self.list = QListWidget(self)
        self.list.itemActivated.connect(self.onActivateItem)
        self.loadList()
        layout = cmn.VBox([toolbar, self.list], spacing=0)
        self.setDialogLayout(layout, self.doSelect, close_btn=not is_selecting, autodefault=False)

    def doSelect(self):
        cur = self.list.currentItem()
        if not cur:
            self.sbar.showMessage('You should select a factor first')
            return
        self.selected_item = cur.data(Qt.UserRole)
        self.accept()
        
    def loadList(self, cur_obj=None):
        if not cur_obj and self.list.currentItem():
            cur_obj = self.list.currentItem().data(Qt.UserRole)
         
        self.list.clear()
        for g in gstate.factorsMap().values():
            item = QListWidgetItem(g.name)
            item.setData(Qt.UserRole, g)
            self.list.addItem(item)
            if g == cur_obj:
                self.list.setCurrentItem(item)
        self.list.sortItems(Qt.AscendingOrder)
        if self.list.currentItem():
            self.list.scrollToItem(self.list.currentItem())
    
    def addFactor(self):
        d = FactorDialog()
        if d.exec_():
            self.loadList(d.new_obj)

    def onActivateItem(self, item):
        if self.is_selecting:
            self.doSelect()
        else:
            self.editFactor(item)
        
    def editFactorAction(self):
        cur = self.list.currentItem()
        if cur:
            self.editFactor(cur)
    
    def editFactor(self, item):
        if FactorDialog(item.data(Qt.UserRole)).exec_():
            self.loadList()
    
    def removeFactor(self):
        cur = self.list.currentItem()
        if cur is None:
            return
        if gstate.hasInTree(cur.data(Qt.UserRole)):
            QMessageBox.warning(self, kProgramName, 'This factor is used in the tree and cannot be deleted')
            return
        gstate.deleteObject(cur.data(Qt.UserRole))
        self.loadList()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    gstate.resetState()
    gstate.addNewObject(ESFactor(None, 'Wanna party?'))
    gstate.addNewObject(ESFactor(None, 'Wanna eat?'))
    d = FactorsDialog()
    d.exec_()