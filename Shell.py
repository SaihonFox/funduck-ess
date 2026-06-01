import sys
import os
import common as cmn
from objects import gstate, kProgramName, ESNode, kFactor, kGoal, getId, getType
from goals_ui import GoalsDialog, GoalDialog
from factors_ui import FactorsDialog, FactorDialog
from checker import CheckResultsPanel, kCheckError
from description_ui import DescriptionDialog
from about_ui import AboutDialog
from es_runner import ESWindow
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QScrollArea, QMenu,
                             QMessageBox, QFileDialog, QToolBar, QAction)
from PyQt5.QtCore import Qt, QSettings, QPoint
from PyQt5.QtGui import QPainter, QImage, QColor, QCursor


class DecisionTreeWidget(QWidget):
	def __init__(self, owner):
		super().__init__()
		self.panning = False
		self.setMouseTracking(True)
		self.setFocusPolicy(Qt.StrongFocus)
		pal = self.palette()
		pal.setColor(self.backgroundRole(), QColor('white'))
		self.setAutoFillBackground(True)
		self.setPalette(pal)
		self.owner = owner
	
	def getNodeUnderCursor(self, ev):
		def f(node):
			if node.x <= ev.x() <= node.x + node.width and node.y <= ev.y() <= node.y + node.height:
				return node
			return None
		
		return gstate.getRoot().traverse(f)
	
	def contextMenuEvent(self, ev):
		node = self.getNodeUnderCursor(ev)
		if not node: return
		menu = QMenu(self)
		menu.addAction(cmn.Action(self, 'Select a factor', '', lambda: self.setFactor(node), 'F'))
		menu.addAction(cmn.Action(self, 'Select a goal', '', lambda: self.setGoal(node), 'G'))
		if getType(node.content) == kGoal and not node.children:
			menu.addAction(cmn.Action(self, 'Add an extra goal', '', lambda: self.addExtraGoal(node), 'Shift+G'))
		if node.content is not None:
			menu.addAction(cmn.Action(self, 'Clear node', '', lambda: self.clearNodeUI(node), 'X'))
		menu.addSeparator()
		menu.addAction(cmn.Action(self, 'Copy', 'icons/copy.png', self.doCopy, 'Ctrl+C'))
		menu.addAction(cmn.Action(self, 'Paste', 'icons/paste.png', self.doPaste, 'Ctrl+V'))
		if node.content:
			menu.addSeparator()
			t = 'Edit factor' if node.content.getType() == kFactor else 'Edit goal'
			menu.addAction(cmn.Action(self, t, '', lambda: self.editCurrent(node), 'E'))
		menu.exec_(ev.globalPos())
	
	def doCopy(self):
		node = gstate.getCurrentNode()
		if node: gstate.clipboard = node.serializeSubtree()
	
	def doPaste(self):
		node = gstate.getCurrentNode()
		if not node or not gstate.clipboard: return
		data_dict = {x['id']: x for x in gstate.clipboard}
		
		def updateNode(nd, data):
			content_id = data.get('content')
			if content_id not in gstate.objMap: return
			nd.content = gstate.objMap[content_id]
			n_children = len(nd.content.choices) if nd.content.getType() == kFactor else len(data.get('children', []))
			for child_id in data.get('children', [])[:n_children]:
				t = gstate.addNewObject(ESNode());
				nd.children.append(t);
				updateNode(t, data_dict[child_id])
			while len(nd.children) < n_children: nd.children.append(gstate.addNewObject(ESNode()))
		
		gstate.beginTransaction('Paste')
		try:
			self.clearNode(node);
			updateNode(node, gstate.clipboard[0])
		finally:
			gstate.endTransaction()
	
	def editCurrent(self, node):
		if node.content.getType() == kFactor:
			FactorDialog(node.content).exec_()
		elif node.content.getType() == kGoal:
			GoalDialog(node.content).exec_()
	
	def mousePressEvent(self, ev):
		if ev.button() == Qt.MiddleButton:
			self.panning = True;
			self.last_pos = ev.globalPos();
			return
		node = self.getNodeUnderCursor(ev)
		if not node: return
		
		def set_sel(x):
			x.selected = (x == node)
		
		gstate.getRoot().traverse(set_sel);
		self.update()
	
	def mouseMoveEvent(self, ev):
		if not self.panning: return
		gpos = ev.globalPos()
		dx, dy = gpos.x() - self.last_pos.x(), gpos.y() - self.last_pos.y()
		self.last_pos = gpos
		sb = self.owner.pbox_scroll.horizontalScrollBar()
		if sb: sb.setValue(sb.value() - dx)
		sb = self.owner.pbox_scroll.verticalScrollBar()
		if sb: sb.setValue(sb.value() - dy)
	
	def mouseReleaseEvent(self, ev):
		self.panning = False
	
	def clearNode(self, node):
		gstate.modifyObject(node);
		node.content = None
		for c in list(node.children): gstate.deleteNode(c)
		node.children.clear()
	
	def clearNodeUI(self, node):
		if not node.content: return
		gstate.beginTransaction('Clear node')
		try:
			self.clearNode(node)
		finally:
			gstate.endTransaction()
	
	def setFactor(self, node):
		dialog = FactorsDialog(True)
		if not dialog.exec_(): return
		factor = dialog.selected_item
		if node.content == factor: return
		gstate.beginTransaction('Set Factor')
		try:
			self.clearNode(node);
			node.content = factor
			node.children = [gstate.addNewObject(ESNode()) for _ in factor.choices]
		finally:
			gstate.endTransaction()
	
	def setGoal(self, node):
		dialog = GoalsDialog(True)
		if not dialog.exec_(): return
		goal = dialog.selected_item
		if node.content == goal: return
		gstate.beginTransaction('Set Goal')
		try:
			self.clearNode(node); node.content = goal
		finally:
			gstate.endTransaction()
	
	def addExtraGoal(self, node):
		if getType(node.content) != kGoal or node.children: return
		dialog = GoalsDialog(True)
		if not dialog.exec_(): return
		goal = dialog.selected_item
		gstate.beginTransaction('Add Extra Goal')
		try:
			gstate.modifyObject(node); node.children.append(gstate.addNewObject(ESNode(None, goal)))
		finally:
			gstate.endTransaction()
	
	def keyPressEvent(self, ev):
		key = ev.key()
		cur = gstate.getCurrentNode()
		
		def getPrevNode(node):
			k = 0
			while True:
				p = node.parent
				if not p:
					return None
				idx = p.children.index(node)
				if idx == 0:
					k += 1
				else:
					node = p.children[idx - 1]; break
				node = p
			for _ in range(k):
				if node.children: node = node.children[-1]
			return node
		
		def getNextNode(node):
			k = 0
			while True:
				p = node.parent
				if not p:
					return None
				idx = p.children.index(node)
				if idx == len(p.children) - 1:
					k += 1
				else:
					node = p.children[idx + 1]; break
				node = p
			for _ in range(k):
				if node.children: node = node.children[0]
			return node
		
		if key in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down]:
			tgt = gstate.getRoot() if not cur else (cur.parent if key == Qt.Key_Left else (
				cur.children[0] if cur.children and key == Qt.Key_Right else getPrevNode(
					cur) if key == Qt.Key_Up else getNextNode(cur)))
			if tgt: self.owner.selectNode(getId(tgt))
			return
		if not cur: return
		if int(ev.modifiers()) == 0:
			if key == Qt.Key_F:
				self.setFactor(cur)
			elif key == Qt.Key_G:
				self.setGoal(cur)
			elif key == Qt.Key_E:
				self.editCurrent(cur)
			elif key == Qt.Key_X:
				self.clearNodeUI(cur)
		elif ev.modifiers() == Qt.ShiftModifier:
			if key == Qt.Key_G: self.addExtraGoal(cur)
	
	def paintEvent(self, ev):
		p = QPainter(self)
		p.setFont(ESNode.font)
		gstate.getRoot().render(p)


class MainW(QMainWindow):
	def __init__(self):
		super().__init__()
		self.resize(800, 600)
		self.setWindowTitle(kProgramName)
		self.setWindowIcon(cmn.GetIcon('icons/duckling.png'))
		self.check_results = CheckResultsPanel(self)
		self.addDockWidget(Qt.BottomDockWidgetArea, self.check_results)
		s = QSettings('PlatBox', 'Hal0')
		t = s.value("mainwnd/geometry")
		if t: self.restoreGeometry(t)
		t = s.value("mainwnd/dockstate")
		if t: self.restoreState(t)
		self.pbox = DecisionTreeWidget(self)
		self.pbox_scroll = QScrollArea(self)
		self.pbox_scroll.setWidget(self.pbox)
		self.pbox_scroll.setWidgetResizable(True)
		self.pbox_scroll.setFocusProxy(self.pbox)
		self.setCentralWidget(self.pbox_scroll)
		menubar = self.menuBar()
		fileMenu = menubar.addMenu('File')
		self.act_new_es = cmn.Action(self, 'New expert system', 'icons/new.png', self.doNew, 'Ctrl+N')
		self.act_open_es = cmn.Action(self, 'Open...', 'icons/open.png', self.doOpen, 'Ctrl+O')
		self.act_save_es = cmn.Action(self, 'Save', 'icons/save.png', self.doSave, 'Ctrl+S')
		self.act_save_es_as = cmn.Action(self, 'Save as...', '', self.doSaveAs)
		self.act_export_png = cmn.Action(self, 'Export the decision tree to PNG...', '', self.doExportPNG)
		self.act_export_rules = cmn.Action(self, 'Export the rules list to TXT...', '', self.doExportRulesTxt)
		self.act_check_es = cmn.Action(self, 'Check the system', 'icons/flag-blue.png', self.doCheckES, 'F8')
		self.act_run_es = cmn.Action(self, 'Run the system', 'icons/run.png', self.doRunES, 'F9')
		self.act_about = cmn.Action(self, 'About...', 'icons/info.png', lambda: AboutDialog().exec_())
		for a in [self.act_new_es, self.act_open_es, self.act_save_es, self.act_save_es_as, None, self.act_export_png,
		          self.act_export_rules, None, self.act_check_es, self.act_run_es, None,
		          cmn.Action(self, 'Exit', '', self.exitApp)]:
			fileMenu.addAction(a) if a else fileMenu.addSeparator()
		editMenu = menubar.addMenu('Edit')
		self.act_undo = cmn.Action(self, 'Undo', 'icons/undo.png', gstate.undo, 'Ctrl+Z')
		self.act_redo = cmn.Action(self, 'Redo', 'icons/redo.png', gstate.redo, 'Ctrl+Shift+Z')
		self.act_goals = cmn.Action(self, 'Goals...', '', self.doGoals, 'Ctrl+G')
		self.act_factors = cmn.Action(self, 'Factors...', '', self.doFactors, 'Ctrl+F')
		self.act_es_info = cmn.Action(self, 'Expert system description...', '', self.doEditDescription, 'Ctrl+D')
		for a in [self.act_undo, self.act_redo, None, self.act_goals, self.act_factors, None, self.act_es_info]:
			editMenu.addAction(a) if a else editMenu.addSeparator()
		helpMenu = menubar.addMenu('Help');
		helpMenu.addAction(self.act_about)
		toolbar = cmn.ToolBar(
			[self.act_new_es, self.act_open_es, self.act_save_es, None, self.act_undo, self.act_redo, None,
			 self.act_check_es, self.act_run_es, None, self.act_about])
		toolbar.setObjectName('tlb_main');
		toolbar.setWindowTitle('Toolbar')
		self.addToolBar(toolbar)
		gstate.on_update = self.updateUI
		self.doNew()
		self.show()
	
	def closingCheck(self):
		if gstate.saved: return True
		ans = QMessageBox.question(self, kProgramName, 'Save changes in expert system "%s"?' % gstate.getName(),
		                           QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
		if ans == QMessageBox.No: return True
		if ans == QMessageBox.Cancel: return False
		return self.doSave()
	
	def exitApp(self):
		if self.closingCheck(): QApplication.quit()
	
	def updateUI(self):
		self.setWindowTitle(gstate.getName() + ' - ' + kProgramName)
		self.act_undo.setEnabled(gstate.canUndo());
		self.act_redo.setEnabled(gstate.canRedo())
		gstate.getRoot().computeLayout(ESNode.kDiagramMargin, ESNode.kDiagramMargin)
		w, h = gstate.getExtents()
		self.pbox.setMinimumSize(w, h);
		self.pbox.update()
	
	def resetUI(self):
		self.check_results.reset(); self.updateUI(); self.pbox.setFocus()
	
	def doNew(self):
		if not self.closingCheck(): return
		gstate.resetState();
		self.resetUI()
	
	def doOpenRaw(self, fname):
		try:
			gstate.loadFromFile(fname)
		except:
			QMessageBox.critical(self, kProgramName,
			                     'An error occurred while opening file "%s"' % fname); gstate.resetState(); raise
		self.resetUI()
	
	def doOpen(self):
		if not self.closingCheck(): return
		fname = cmn.getOpenFileName(self, 'es', 'Open File', 'Expert System Files (*.es)')
		if fname: self.doOpenRaw(fname)
	
	def doSaveRaw(self, fname):
		try:
			gstate.saveToFile(fname)
		except:
			QMessageBox.critical(self, kProgramName, 'An error occurred while writing to file "%s"' % fname); raise
	
	def doSave(self):
		if gstate.filename: self.doSaveRaw(gstate.filename); return True
		return self.doSaveAs()
	
	def doSaveAs(self):
		fname = cmn.getOpenFileName(self, 'es', 'Save to File', 'Expert System Files (*.es)', save=True)
		if fname: self.doSaveRaw(fname); self.updateUI(); return True
		return False
	
	def doExportPNG(self):
		fname = cmn.getOpenFileName(self, 'es', 'Export to PNG', 'PNG Images (*.png)', save=True)
		if not fname: return
		w, h = gstate.getExtents()
		img = QImage(w, h, QImage.Format_RGB32);
		img.fill(QColor("white"))
		with QPainter(img) as p:
			p.setFont(ESNode.font);
			gstate.getRoot().render(p, True)
		img.save(fname, 'PNG')
	
	def doExportRulesTxt(self):
		fname = cmn.getOpenFileName(self, 'es', 'Export Rules to TXT', 'Text Files (*.txt)', save=True)
		if not fname: return
		if not fname.endswith('.txt'): fname += '.txt'
		
		rules = []
		root = gstate.getRoot()
		
		def traverse(node, path):
			if node.content is None:
				return
			
			if node.content.getType() == kGoal:
				if path:
					condition_str = " И ".join(path)
					rule_str = f'ЕСЛИ {condition_str} ТО {node.content.name};'
					rules.append(rule_str)
				else:
					rule_str = f'ТО {node.content.name};'
					rules.append(rule_str)
				return
			
			if node.content.getType() == kFactor:
				factor_name = node.content.name
				for i, child in enumerate(node.children):
					choice_val = node.content.choices[i] if i < len(node.content.choices) else f"Variant {i + 1}"
					new_path = path + [f'"{factor_name}" = "{choice_val}"']
					traverse(child, new_path)
		
		traverse(root, [])
		
		try:
			with open(fname, 'w', encoding='utf-8') as f:
				f.write(f"Список правил для темы: {gstate.es_name}\n")
				f.write(f"Число правил: {len(rules)}\n\n")
				for idx, rule in enumerate(rules, 1):
					f.write(f"{idx}. {rule}\n")
			QMessageBox.information(self, "Export Successful", f"Rules exported to {fname}")
		except Exception as e:
			QMessageBox.critical(self, "Export Error", f"Failed to write file: {str(e)}")
	
	def doCheckES(self):
		self.check_results.doCheck()
	
	def doEditDescription(self):
		DescriptionDialog().exec_()
	
	def doRunES(self):
		ESWindow().exec_()
	
	def doGoals(self):
		GoalsDialog().exec_()
	
	def doFactors(self):
		FactorsDialog().exec_()
	
	def selectNode(self, node_id):
		node = gstate.getRoot().traverse(lambda nd: nd if nd.ident == node_id else None)
		if node:
			gstate.setCurrentNode(node)
			self.pbox_scroll.ensureVisible(node.x + node.width, node.y + node.height)
			self.pbox_scroll.ensureVisible(node.x, node.y)
			self.pbox.update()
	
	def closeEvent(self, event):
		if not self.closingCheck(): event.ignore(); return
		s = QSettings('PlatBox', 'Hal0')
		s.setValue("mainwnd/geometry", self.saveGeometry())
		s.setValue('mainwnd/dockstate', self.saveState())


def main():
	QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
	app = QApplication(sys.argv)
	app.setApplicationName(kProgramName)
	_ = MainW()
	sys.exit(app.exec_())


if __name__ == '__main__':
	main()