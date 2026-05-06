from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPen
import os
import json

kProgramName = 'Funduck ESS'
kDefaultESName = 'Expert system'
kDefaultESDescription = ''
kGoal, kFactor, kNode = 1, 2, 3
objTypes = {}

def getId(obj): return obj.ident if obj else None
def getType(obj): return obj.getType() if obj else None

class State:
    def __init__(self):
        self.objMap, self.typedMaps = {}, {}
        self.undo_stack, self.redo_stack = [], []
        self.clipboard = None
        self.next_id = 0
        self.saved = True
        self.filename = None
        self.in_transaction = False
        self.on_update = None
        self.es_name = ''
        self.es_descr = ''

    def getName(self):
        if self.filename: return os.path.splitext(os.path.split(self.filename)[1])[0]
        return 'Unnamed'

    def getObject(self, ident): return self.objMap.get(ident)
    def getMap(self, obj_type):
        if obj_type not in self.typedMaps: self.typedMaps[obj_type] = {}
        return self.typedMaps[obj_type]
    def goalsMap(self): return self.getMap(kGoal)
    def factorsMap(self): return self.getMap(kFactor)
    def addObjectRaw(self, obj): self.getMap(obj.getType())[obj.ident] = obj; self.objMap[obj.ident] = obj
    def callUpdateHandler(self):
        if self.on_update: self.on_update()

    def wrapInTransaction(self, f):
        if self.in_transaction: return f()
        self.beginTransaction()
        try: return f()
        finally: self.endTransaction()

    def addNewObject(self, obj):
        def f():
            self.saved = False; self.next_id += 1; obj.ident = self.next_id; self.addObjectRaw(obj); return obj
        return self.wrapInTransaction(f)

    def modifyObject(self, obj):
        def f(): self.saved = False
        return self.wrapInTransaction(f)
    def modifyMetadata(self): self.modifyObject(None)

    def deleteObject(self, obj):
        def f(): self.saved = False; del self.getMap(obj.getType())[obj.ident]; del self.objMap[obj.ident]
        return self.wrapInTransaction(f)

    def deleteNode(self, node):
        def f(): node.traverse(lambda obj: self.deleteObject(obj))
        return self.wrapInTransaction(f)

    def canUndo(self): return bool(self.undo_stack)
    def canRedo(self): return bool(self.redo_stack)

    def undo(self):
        if not self.canUndo(): return
        self.redo_stack.append(self.getSnapshot()); self.setSnapshot(self.undo_stack.pop())
        self.saved = False; self.callUpdateHandler()
    def redo(self):
        if not self.canRedo(): return
        self.undo_stack.append(self.getSnapshot()); self.setSnapshot(self.redo_stack.pop())
        self.saved = False; self.callUpdateHandler()

    def beginTransaction(self, name='undefined_op'):
        self.undo_stack.append(self.getSnapshot()); self.redo_stack.clear(); self.in_transaction = True
    def endTransaction(self):
        self.in_transaction = False; self.callUpdateHandler()

    def getRoot(self): return self.objMap[0]
    def hasInTree(self, obj):
        def f(node): return True if node.content == obj else None
        return self.getRoot().traverse(f) is True
    def getCurrentNode(self):
        def f(node): return node if node.selected else None
        return self.getRoot().traverse(f)
    def setCurrentNode(self, node):
        def f(x): x.selected = (x == node)
        self.getRoot().traverse(f)

    def resetState(self):
        self.objMap.clear(); self.typedMaps.clear(); self.undo_stack.clear(); self.redo_stack.clear()
        self.clipboard = None; self.saved = True; self.filename = None; self.next_id = 0
        self.es_name = kDefaultESName; self.es_descr = kDefaultESDescription
        root = ESNode(0); root.selected = True; self.addObjectRaw(root)

    def getSnapshot(self):
        data, saved = [], set()
        def f(obj):
            if obj.ident in saved: return
            saved.add(obj.ident); data.append(obj.serialize(f))
        for obj in self.objMap.values(): f(obj)
        return json.dumps({'objects': data, 'version': 3, 'es_name': self.es_name, 'es_descr': self.es_descr, 'cur_node': getId(self.getCurrentNode())})

    def saveToFile(self, filename):
        with open(filename, 'wt', encoding='utf8') as f: f.write(self.getSnapshot())
        self.filename = filename; self.saved = True

    def setSnapshot(self, data):
        data = json.loads(data)
        self.objMap.clear(); self.typedMaps.clear(); self.next_id = 0
        if data.get('version', 0) > 1: self.es_name = data['es_name']; self.es_descr = data['es_descr']
        else: self.es_name = kDefaultESName; self.es_descr = kDefaultESDescription
        for item in data['objects']:
            obj = objTypes[item['ty']](); obj.deserialize(item); self.addObjectRaw(obj)
            self.next_id = max(self.next_id, obj.ident)
        if 'cur_node' in data: self.setCurrentNode(self.getObject(data['cur_node']))

    def loadFromFile(self, filename):
        with open(filename, encoding='utf8') as f: self.setSnapshot(f.read())
        self.undo_stack.clear(); self.redo_stack.clear(); self.clipboard = None; self.saved = True; self.filename = filename

    def getExtents(self):
        extents = [0, 0]
        def f(node): extents[0] = max(extents[0], node.x + node.width); extents[1] = max(extents[1], node.y + node.height)
        self.getRoot().traverse(f)
        return (extents[0] + ESNode.kDiagramMargin, extents[1] + ESNode.kDiagramMargin)

gstate = State()

class ESObject:
    def __init__(self, ident): self.ident = ident
    def getType(self): return None
    def serialize(self, f): return {'id': self.ident, 'ty': self.getType()}
    def deserialize(self, data): self.ident = data['id']

class ESGoal(ESObject):
    def __init__(self, ident=None, name='Undefined', descr='Undefined'):
        super().__init__(ident); self.name = name; self.descr = descr
    def getType(self): return kGoal
    def serialize(self, f):
        res = super().serialize(f); res['name'] = self.name; res['descr'] = self.descr; return res
    def deserialize(self, data): super().deserialize(data); self.name = data['name']; self.descr = data['descr']
objTypes[kGoal] = ESGoal

class ESFactor(ESObject):
    def __init__(self, ident=None, name='Undefined'):
        super().__init__(ident); self.name = name; self.is_binary = True; self.choices = self.getBinaryChoices()
    def getType(self): return kFactor
    def serialize(self, f):
        res = super().serialize(f); res['name'] = self.name; res['is_binary'] = self.is_binary; res['choices'] = self.choices; return res
    def deserialize(self, data): super().deserialize(data); self.name = data['name']; self.is_binary = data['is_binary']; self.choices = data['choices']
    @staticmethod
    def getBinaryChoices(): return ['Yes', 'No']
objTypes[kFactor] = ESFactor

class ESNode(ESObject):
    def __init__(self, ident=None, content=None):
        super().__init__(ident)
        self.children, self.content = [], content
        self.x = self.y = self.width = self.height = self.lineheight = 0
        self.selected = False
    def getType(self): return kNode
    def serialize(self, f):
        res = super().serialize(f)
        def id_(obj): f(obj) if obj else None; return getId(obj)
        res['content'] = id_(self.content)
        res['children'] = [id_(x) for x in self.children]
        return res
    def deserialize(self, data):
        super().deserialize(data)
        self.content = gstate.getObject(data['content'])
        self.children = [gstate.getObject(x) for x in data['children']]
    def serializeSubtree(self):
        data = []
        def f(obj):
            if obj.getType() != kNode: return
            data.append(obj.serialize(f))
        data.append(self.serialize(f))
        return list(reversed(data))
    def traverse(self, f):
        t = f(self)
        if t is not None: return t
        for c in self.children:
            t = c.traverse(f)
            if t is not None: return t

    font = QFont("Arial", 10)
    kDefaultText = 'Select a factor or goal'
    kHorizontalMargin = 5; kItemVerticalMargin = 5; kDiagramMargin = 10

    def computeLayout(self, x, y, parent=None):
        self.computeDimensions(); self.parent = parent; self.x = x; self.y = y
        kVerticalSpan = 5; res2 = 0
        if self.children and getType(self.content) != kGoal and getType(self.children[0].content) != kFactor:
            res2 += self.min_item_height
        for c in self.children: res2 += c.computeLayout(x + self.width + 20, y + res2, self) + kVerticalSpan
        self.ys = [y]; n = len(self.getText())
        for i in range(n):
            t = self.ys[-1] + self.min_item_height
            if i > 0 and i + 1 < n: t = max(t, self.children[i-1].ys[-1])
            self.ys.append(t)
        self.height = self.ys[-1] - self.ys[0]
        return max(self.height, res2 - kVerticalSpan)

    def getEntryPoint(self): return QPointF(self.x, self.ys[0] + self.min_item_height / 2)
    def getExitPoint(self, idx): return QPointF(self.x + self.width, self.ys[idx] + self.min_item_height / 2)

    def computeDimensions(self):
        text = self.getText()
        fm = QFontMetrics(self.font)
        self.lineheight = fm.height()
        self.min_item_height = self.lineheight + 2 * self.kItemVerticalMargin
        self.width = max(fm.horizontalAdvance(x) for x in text) + 2 * self.kHorizontalMargin
        self.height = self.min_item_height * len(text)

    def getText(self):
        if self.content:
            ty = self.content.getType()
            if ty == kGoal: return [self.content.name]
            if ty == kFactor: return [self.content.name] + self.content.choices
        return [self.kDefaultText]

    def getColor(self):
        if self.content:
            ty = self.content.getType()
            if ty == kGoal: return QColor(128, 255, 128)
            if ty == kFactor: return QColor(192, 192, 255)
        return QColor(255, 255, 0)

    def render(self, p, ignore_selection=False):
        p.setBrush(self.getColor())
        if self.selected and not ignore_selection:
            pen = QPen(QColor("blue")); pen.setWidth(3); p.setPen(pen)
        p.drawRect(self.x, self.y, self.width, self.height)
        if self.selected: p.setPen(QColor("black"))
        text = self.getText(); x = self.x + self.kHorizontalMargin
        for texty, s in zip(self.ys, text): p.drawText(x, texty + self.lineheight, s)
        def rightLine(a, b):
            mx = (a.x() + b.x()) / 2
            if abs(a.y() - b.y()) < 10: a.setY(b.y())
            p.drawLine(a, QPointF(mx, a.y())); p.drawLine(QPointF(mx, a.y()), QPointF(mx, b.y())); p.drawLine(QPointF(mx, b.y()), b)
        for liney in self.ys[1:-1]: p.drawLine(QPointF(self.x, liney), QPointF(self.x + self.width, liney))
        start_idx = 1 if self.content and self.content.getType() == kFactor else 0
        for i, c in enumerate(self.children, start_idx):
            rightLine(self.getExitPoint(i), c.getEntryPoint()); c.render(p, ignore_selection)

objTypes[kNode] = ESNode