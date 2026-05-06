from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
                             QToolBar, QToolButton, QPushButton, QDialog,
                             QStatusBar, QFileDialog, QTextEdit, QTableWidget,
                             QTableWidgetItem, QAbstractItemView, QAction,
                             QSpacerItem, QWidget, QLabel, QMenu)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
import os
import sys
import pickle

APP_NAME = 'Funduck'

def truncateStr(s, maxlen):
    return s[:maxlen - 1] + '…' if len(s) > maxlen else s

def HLine():
    t = QFrame()
    t.setFrameShape(QFrame.HLine)
    t.setFrameShadow(QFrame.Sunken)
    return t

kTopAlign, kBottomAlign = 1, 2
kLeftAlign, kRightAlign = 1, 2

def VBox(items, margin=0, spacing=5, align=None, stretch=None):
    box = QVBoxLayout()
    box.setContentsMargins(margin, margin, margin, margin)
    box.setSpacing(spacing)
    if stretch is None: stretch = [0] * len(items)
    if align == kBottomAlign: box.setAlignment(Qt.AlignBottom)
    elif align == kTopAlign: box.setAlignment(Qt.AlignTop)
    for x, st in zip(items, stretch):
        box.addLayout(x, st) if isinstance(x, (QVBoxLayout, QHBoxLayout, QGridLayout)) else box.addWidget(x, st)
    return box

def HBox(items, margin=0, spacing=5, align=None, stretch=None):
    box = QHBoxLayout()
    box.setContentsMargins(margin, margin, margin, margin)
    box.setSpacing(spacing)
    if stretch is None: stretch = [0] * len(items)
    if align == kRightAlign: box.setAlignment(Qt.AlignRight)
    elif align == kLeftAlign: box.setAlignment(Qt.AlignLeft)
    for x, st in zip(items, stretch):
        if isinstance(x, (QVBoxLayout, QHBoxLayout, QGridLayout)): box.addLayout(x, st)
        elif isinstance(x, QSpacerItem): box.addSpacerItem(x)
        else: box.addWidget(x, st)
    return box

_icons_cache = {}
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
def GetIcon(fname):
    if not fname: fname = ''
    if fname not in _icons_cache:
        _icons_cache[fname] = QIcon(resource_path(fname))
    return _icons_cache[fname]

def Action(owner, descr, icon, handler=None, shortcut=None, statustip=None, enabled=True, checkable=False, checked=None, *, bold=False):
    act = QAction(GetIcon(icon), descr, owner)
    act.setIconVisibleInMenu(True)
    if bold:
        f = act.font(); f.setBold(True); act.setFont(f)
    if shortcut: act.setShortcut(shortcut)
    if statustip: act.setStatusTip(statustip)
    if handler: act.triggered.connect(handler)
    act.setEnabled(enabled)
    if checkable or checked is not None:
        act.setCheckable(True)
        if checked is not None: act.setChecked(checked)
    return act

def Separator(owner):
    res = Action(owner, '', owner); res.setSeparator(True); return res

class Grid(QTableWidget):
    def __init__(self, col_names, widths=None, allow_deleting_rows=False):
        super().__init__(0, len(col_names))
        self.setHorizontalHeaderLabels(col_names)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.allow_deleting_rows = allow_deleting_rows
        if widths: self.load(widths)

    def keyPressEvent(self, event):
        if self.allow_deleting_rows and event.key() == Qt.Key_Delete:
            if self.currentItem() and self.currentRow() + 1 < self.rowCount():
                self.removeRow(self.currentRow())
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        if self.allow_deleting_rows and self.currentItem() and self.currentRow() + 1 < self.rowCount():
            menu = QMenu(self)
            menu.addAction(Action(self, 'Delete', '', lambda: self.removeRow(self.currentRow()), 'Delete'))
            menu.exec_(event.globalPos())

    def load(self, widths):
        for i, w in enumerate(widths): self.setColumnWidth(i, w)
    def save(self): return [self.columnWidth(i) for i in range(self.columnCount())]
    def setRowData(self, row, data, editable=True):
        for j in range(self.columnCount()):
            tmp = QTableWidgetItem(str(data[j]))
            if not editable: tmp.setFlags(tmp.flags() ^ Qt.ItemIsEditable)
            self.setItem(row, j, tmp)
    def setTableData(self, data, editable=True, fix_height=None):
        self.setRowCount(len(data))
        for i, x in enumerate(data): self.setRowData(i, x, editable)
        if fix_height is None: self.resizeRowsToContents()
        else:
            for i in range(len(data)): self.setRowHeight(i, fix_height)

class Table(QGridLayout):
    def __init__(self, items, margin=0):
        super().__init__()
        self.setContentsMargins(margin, margin, margin, margin)
        for i, (s, item) in enumerate(items):
            lbl = QLabel(s)
            lbl.setMinimumHeight(20)
            self.addWidget(lbl, i, 0, Qt.AlignTop)
            self.addWidget(ensureWidget(item), i, 1)
            self.setAlignment(lbl, Qt.AlignLeft | Qt.AlignTop)

def ToolBar(actions):
    res = QToolBar()
    res.setStyleSheet("QToolBar { border: 0px }")
    for x in actions:
        if x:
            if x.__class__.__name__ == 'QAction': res.addAction(x)
            else: res.addWidget(x)
        else: res.addSeparator()
    return res

def ToolBtn(action):
    res = QToolButton(); res.setDefaultAction(action); res.setAutoRaise(True); return res

def ToolBtnStack(actions): return HBox([ToolBtn(a) for a in actions], spacing=0, align=kLeftAlign)

def Button(caption, handler, *, enabled=True, autodefault=True):
    btn = QPushButton(caption); btn.setAutoDefault(autodefault); btn.clicked.connect(handler); btn.setEnabled(enabled); return btn

def ensureLayout(widget): return VBox([widget]) if isinstance(widget, QWidget) else widget

def ensureWidget(layout):
    if isinstance(layout, QWidget):
        return layout
    widget = QWidget()
    widget.setLayout(layout)
    return widget

class Dialog(QDialog):
    def __init__(self, appname, wndname, title, is_modal=True):
        super().__init__()
        self.appname, self.wndname, self.is_modal = appname, wndname, is_modal
        self.setWindowTitle(title)
        self.setWindowIcon(GetIcon('icons/duckling.png'))
        self.state_saver = StateSaver(wndname, appname)

    def done(self, code):
        super().done(code)
        self.close()

    def setCustomLayout(self, layout, has_statusbar, menu=None):
        if has_statusbar:
            self.sbar = QStatusBar()
            layout.setContentsMargins(10, 10, 10, 0)
            layout = VBox([layout, self.sbar], spacing=0, stretch=[1, 0])
        layout = ensureLayout(layout)
        if menu: layout.setMenuBar(menu)
        self.setLayout(layout)
        self.loadSettings()

    def setDialogLayout(self, layout, ok_handler, has_statusbar=True, close_btn=False, *, extra_buttons=None, autodefault=True, menu=None):
        buttons = []
        if extra_buttons: buttons.extend([Button(capt, handler, autodefault=autodefault) for capt, handler in extra_buttons])
        if close_btn: buttons.append(Button('Close', self.reject, autodefault=autodefault))
        else:
            buttons.extend([Button('OK', ok_handler, autodefault=autodefault), Button('Cancel', self.reject, autodefault=autodefault)])
            self.addAction(Action(self, 'OK', '', ok_handler, 'F5'))
        self.setCustomLayout(VBox([layout, HBox(buttons, align=kRightAlign)], 10), has_statusbar, menu)

    def loadSettings(self):
        s = QSettings(APP_NAME, self.appname)
        t = s.value(f"{self.wndname}/geometry")
        if t: self.restoreGeometry(t)
        self.state_saver.load()

    def closeEvent(self, event):
        s = QSettings(APP_NAME, self.appname)
        s.setValue(f"{self.wndname}/geometry", self.saveGeometry())
        self.state_saver.save()
        super().closeEvent(event)

    def registerStateObj(self, name, obj): self.state_saver.register(name, obj)

class SaveStateWrapper:
    def __init__(self, base): self.base = base
    def load(self, state): self.base.restoreState(state)
    def save(self): return self.base.saveState()

class StateSaver:
    def __init__(self, wndname, appname=APP_NAME): self.wndname, self.appname, self.objs = wndname, appname, []
    def load(self):
        if not self.objs: return
        s = QSettings(APP_NAME, self.appname)
        for name, obj in self.objs:
            t = s.value(f'{self.wndname}/{name}')
            if t is not None: obj.load(pickle.loads(t))
    def save(self):
        if not self.objs: return
        s = QSettings(APP_NAME, self.appname)
        for name, obj in self.objs: s.setValue(f'{self.wndname}/{name}', pickle.dumps(obj.save()))
    def register(self, name, obj): self.objs.append((name, obj))

def eventToNum(event):
    if Qt.Key_1 <= event.key() <= Qt.Key_9: return event.key() - Qt.Key_1
    if event.key() == Qt.Key_0: return 9
    return None

def showReport(title, text, only_close_button=True, modal=True):
    class ReportDialog(Dialog):
        def __init__(self, title, text):
            super().__init__(APP_NAME, 'report_wnd', title)
            e = QTextEdit(); e.setFont(QFont('Consolas', 10)); e.setReadOnly(True); e.setPlainText(text)
            self.resize(640, 480)
            self.setDialogLayout(e, lambda: self.accept(), has_statusbar=False, close_btn=only_close_button)
    d = ReportDialog(title, text)
    return d.exec_() if modal else (d.show(), d)

def getOpenFileName(owner, ident, title, filters, save=False):
    ident = 'openfile_' + ident
    s = QSettings(APP_NAME, APP_NAME)
    path = s.value(ident, defaultValue='')
    if save:
        fname, _ = QFileDialog.getSaveFileName(None, title, path, filters)
    else:
        fname, _ = QFileDialog.getOpenFileName(None, title, path, filters)
    if fname:
        s.setValue(ident, os.path.dirname(fname))
    return fname