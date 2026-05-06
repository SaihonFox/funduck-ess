import common as cmn
from PyQt5 import QtWidgets
from objects import gstate


class DescriptionDialog(cmn.Dialog):
	def __init__(self):
		self.edit_name = QtWidgets.QLineEdit(gstate.es_name)
		self.edit_descr = QtWidgets.QPlainTextEdit(gstate.es_descr)
		cmn.Dialog.__init__(self, 'ESS', 'ESDescription', 'Expert system description')
		layout = cmn.Table([('Name', self.edit_name), ('Description', self.edit_descr)])
		self.setDialogLayout(layout, self.doOk)
	
	def doOk(self):
		name = self.edit_name.text().strip()
		descr = self.edit_descr.toPlainText()
		if not name:
			self.sbar.showMessage('Name cannot be empty')
			return
		gstate.modifyMetadata()
		gstate.es_name = name
		gstate.es_descr = descr
		self.accept()


if __name__ == '__main__':
	app = QtWidgets.QApplication([])
	gstate.resetState()
	d = DescriptionDialog()
	d.exec_()