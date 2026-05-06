from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDockWidget, QListWidget, QListWidgetItem
import common as cmn
from objects import gstate, kFactor, getId

kCheckOK = 0
kCheckWarning = 1
kCheckError = 2


class CheckResultsPanel(QDockWidget):
	def __init__(self, owner):
		super().__init__('ES Check Results')
		self.owner = owner
		self.setObjectName('results_panel')
		self.err_list = QListWidget()
		self.err_list.itemActivated.connect(self.onActivated)
		self.setWidget(self.err_list)
		self.setFeatures(QDockWidget.DockWidgetMovable)
	
	def onActivated(self, item):
		nid = item.data(Qt.UserRole)
		if nid is not None:
			self.owner.selectNode(nid)
	
	def reset(self):
		self.err_list.clear()
	
	def doCheck(self):
		self.err_list.clear()
		self.severity = kCheckOK
		
		def addMsg(message, severity, node=None):
			self.severity = max(self.severity, severity)
			item = QListWidgetItem(message)
			item.setData(Qt.UserRole, getId(node))
			if severity == kCheckError:
				icon = 'icons/error.png'
			elif severity == kCheckWarning:
				icon = 'icons/warning.png'
			else:
				icon = 'icons/ok.png'
			item.setIcon(cmn.GetIcon(icon))
			self.err_list.addItem(item)
		
		def f(node):
			if node.content is None:
				addMsg('Incomplete node', kCheckError, node)
		
		gstate.getRoot().traverse(f)
		
		used_factors = set()
		
		def check(node):
			content = node.content
			if content and content.getType() == kFactor:
				if content in used_factors:
					addMsg('Factor "%s" is used more than once in the same branch' % content.name, kCheckError, node)
					return
				used_factors.add(content)
			for c in node.children:
				check(c)
			if content and content.getType() == kFactor:
				used_factors.remove(content)
		
		check(gstate.getRoot())
		
		for g in gstate.goalsMap().values():
			if not gstate.hasInTree(g):
				addMsg('Target "%s" is not used' % g.name, kCheckWarning)
		
		for f in gstate.factorsMap().values():
			if not gstate.hasInTree(f):
				addMsg('Factor "%s" is not used' % f.name, kCheckWarning)
		
		if self.err_list.count() == 0:
			addMsg('No problems detected', kCheckOK)
		
		return self.severity


if __name__ == '__main__':
	pass