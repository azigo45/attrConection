# -*- coding: utf-8 -*-
"""
Attribute Connector — final fix: added missing on_preview
Maya 2023 + PySide2
"""
from __future__ import print_function

import os
import sys
import traceback
from functools import partial
from collections import OrderedDict

from PySide2 import QtCore, QtWidgets, QtGui

try:  # pragma: no cover - Maya modules are optional during Qt-only development
    import maya.cmds as _maya_cmds
    import maya.mel as _maya_mel
    from maya import OpenMayaUI as _omui
    MAYA_AVAILABLE = True
except ImportError:  # pragma: no cover - executed outside of Maya
    MAYA_AVAILABLE = False

    class _DummyCmds(object):
        """Lightweight stub that mimics a subset of maya.cmds."""

        def ls(self, *args, **kwargs):
            return []

        def listAttr(self, *args, **kwargs):
            return []

        def getAttr(self, *args, **kwargs):
            return False

        def attributeQuery(self, *args, **kwargs):
            return None

        def objExists(self, *args, **kwargs):
            return False

        def undoInfo(self, *args, **kwargs):
            return None

        def connectAttr(self, *args, **kwargs):
            return None

        def listConnections(self, *args, **kwargs):
            return []

        def disconnectAttr(self, *args, **kwargs):
            return None

    class _DummyMel(object):
        def eval(self, *args, **kwargs):
            return None

    class _DummyOmui(object):
        class MQtUtil(object):
            @staticmethod
            def mainWindow():
                return None

    _maya_cmds = _DummyCmds()
    _maya_mel = _DummyMel()
    _omui = _DummyOmui()

try:  # pragma: no cover - optional dependency outside Maya
    import shiboken2
except ImportError:  # pragma: no cover - optional dependency outside Maya
    shiboken2 = None

cmds = _maya_cmds
mel = _maya_mel
omui = _omui

# Appearance constants (ChatGPT-inspired theme)
PANEL_BG_RGBA = "rgba(32,33,35,245)"
TITLE_BG_RGBA = "#343541"
TITLE_TEXT = "#ECECF1"
ACCENT_COLOR = "#10a37f"
ACCENT_TEXT = "#F7F7F8"
DARK_1 = "#202123"
DARK_2 = "#343541"
PANEL_BORDER = "#3f4147"
LABEL_LIGHT = "#ECECF1"
TABLE_BG = "#444654"
TABLE_HEADER_BG = "#565869"
TABLE_GRID = "#3f4147"
TABLE_SELECTION = "#0f8f6e"
TABLE_SELECTION_TEXT = "#F7F7F8"
REMOVE_BTN_BG = "#f04438"
REMOVE_BTN_BG_HOVER = "#f97066"
REMOVE_BTN_BG_PRESS = "#b42318"
WINDOW_NAME = "AttrConnector_ChatGPT_Theme"
TABLE_ROW_HEIGHT = 40

# Maya main window helper
def maya_main_window():
    ptr = None
    if MAYA_AVAILABLE and hasattr(omui, "MQtUtil"):
        try:
            ptr = omui.MQtUtil.mainWindow()
        except Exception:
            ptr = None
    if ptr and shiboken2:
        return shiboken2.wrapInstance(int(ptr), QtWidgets.QWidget)
    return None

# Attribute helpers
def list_writable_attributes(obj):
    try:
        all_attrs = cmds.listAttr(obj) or []
    except Exception:
        return []
    out = []
    for a in all_attrs:
        try:
            if cmds.getAttr("{0}.{1}".format(obj, a), settable=True):
                out.append(a)
        except Exception:
            continue
    return sorted(set(out))

def get_attr_type(node, attr):
    try:
        return cmds.attributeQuery(attr, node=node, attributeType=True)
    except Exception:
        return None

def categorize_attributes_for_objs(objs):
    if not objs:
        return OrderedDict(), set(), set()
    per = [set(list_writable_attributes(o)) for o in objs]
    common = set.intersection(*per) if len(per) > 1 else set(per[0]) if per else set()
    union = set.union(*per) if per else set()
    cats = {}
    for attr in sorted(union):
        a_type = None
        for o in objs:
            if cmds.objExists(o) and cmds.attributeQuery(attr, node=o, exists=True):
                a_type = get_attr_type(o, attr)
                break
        name = attr.lower()
        if any(k in name for k in ("translate","rotate","scale","pivot","orient","aim")):
            cat = "Transform"
        elif "visibility" in name or name in ("v","visible","isvisible"):
            cat = "Display"
        elif a_type in ("double3","float3","long3") or name.endswith(("x","y","z")):
            cat = "Vector/Compound"
        elif a_type in ("short","long","double","float","byte","doubleLinear"):
            cat = "Numeric"
        elif a_type == "bool":
            cat = "Boolean"
        elif a_type == "enum":
            cat = "Enum"
        elif a_type == "string":
            cat = "String"
        else:
            cat = "Other"
        cats.setdefault(cat, []).append((attr, attr in common))
    order = ["Transform","Vector/Compound","Numeric","Boolean","Enum","String","Display","Other"]
    ordered = OrderedDict()
    for k in order:
        if k in cats:
            ordered[k] = cats[k]
    for k in cats:
        if k not in ordered:
            ordered[k] = cats[k]
    return ordered, common, union

# Button styles
def _btn_style_basic():
    base = QtGui.QColor(ACCENT_COLOR)
    hover = base.lighter(115).name()
    pressed = base.darker(115).name()
    border = base.darker(130).name()
    return """
    QPushButton {
        color: %s;
        border: 1px solid %s;
        padding: 8px 16px;
        border-radius: 12px;
        background-color: %s;
        font-weight:600;
    }
    QPushButton:hover {
        background-color: %s;
    }
    QPushButton:pressed {
        background-color: %s;
        padding-top:9px;
        padding-bottom:7px;
    }
    QPushButton:focus { outline: none; }
    """ % (
        ACCENT_TEXT,
        border,
        base.name(),
        hover,
        pressed,
    )

def _btn_style_gray():
    base = QtGui.QColor(TABLE_BG)
    hover = base.lighter(115).name()
    pressed = base.darker(115).name()
    border = QtGui.QColor(PANEL_BORDER).name()
    return """
    QPushButton {
        color: %s;
        border: 1px solid %s;
        background-color: %s;
        padding: 8px 16px;
        border-radius: 12px;
        font-weight:600;
    }
    QPushButton:hover {
        background-color: %s;
    }
    QPushButton:pressed {
        background-color: %s;
        padding-top:9px;
        padding-bottom:7px;
    }
    QPushButton:focus { outline: none; }
    """ % (ACCENT_TEXT, border, base.name(), hover, pressed)

def _btn_style_remove():
    return """
    QPushButton {
        background-color: %s;
        color: %s;
        border: 1px solid %s;
        border-radius: 10px;
        font-weight: 700;
        font-size: 16px;
        min-width: 32px;
        min-height: 32px;
    }
    QPushButton:hover {
        background-color: %s;
    }
    QPushButton:pressed {
        background-color: %s;
    }
    QPushButton:focus { outline: none; }
    """ % (REMOVE_BTN_BG, ACCENT_TEXT, QtGui.QColor(REMOVE_BTN_BG).darker(120).name(), REMOVE_BTN_BG_HOVER, REMOVE_BTN_BG_PRESS)

# Title bar (no refresh)
class TitleBar(QtWidgets.QWidget):
    def __init__(self, parent=None, title="Attribute Connector"):
        super(TitleBar, self).__init__(parent)
        self._drag = None
        self.setFixedHeight(50)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "background-color: %s; border: 1px solid %s; border-top-left-radius:12px; border-top-right-radius:12px;"
            " border-bottom-left-radius:0px; border-bottom-right-radius:0px; margin:0px;" % (TITLE_BG_RGBA, PANEL_BORDER)
        )
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(18, 8, 10, 8)
        lay.setSpacing(8)
        self.label = QtWidgets.QLabel(title)
        self.label.setStyleSheet("color:%s; font-weight:600; font-size:13px; letter-spacing:0.5px;" % TITLE_TEXT)
        self.label.setAlignment(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft)
        lay.addWidget(self.label, 1)
        lay.addStretch(1)
        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setFixedSize(32, 32)
        self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(_btn_style_basic())
        self.btn_close.clicked.connect(lambda: self.window().close())
        lay.addWidget(self.btn_close, 0)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag = e.globalPos() - self.window().frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag and (e.buttons() & QtCore.Qt.LeftButton):
            self.window().move(e.globalPos() - self._drag)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag = None
        e.accept()

# Reorderable table widget (with animation)
class ReorderableTableWidget(QtWidgets.QTableWidget):
    ANIM_DURATION = 240
    ANIM_EASING = QtCore.QEasingCurve.OutCubic

    def __init__(self, *args, **kwargs):
        super(ReorderableTableWidget, self).__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._drag_start_row = None
        self._animating = False
        # styling: remove left header, remove frame, set background
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QTableWidget {
                background: transparent;
                color: %s;
                gridline-color: %s;
                selection-background-color: %s;
                selection-color: %s;
                outline: none;
                border: none;
                font-size: 12px;
                alternate-background-color: %s;
            }
            QTableWidget::item:selected {
                background: %s;
                color: %s;
            }
            QTableView::item:focus {
                outline: none;
            }
            QHeaderView::section {
                background: %s;
                color: %s;
                border:0;
                border-bottom: 1px solid %s;
                padding:6px;
                border-top-left-radius:8px;
                border-top-right-radius:8px;
            }
            QHeaderView::section:horizontal:first {
                border-top-left-radius:8px;
            }
            QHeaderView::section:horizontal:last {
                border-top-right-radius:8px;
            }
            QTableCornerButton::section {
                background: %s;
                border: 0;
            }
        """ % (
            LABEL_LIGHT,
            TABLE_GRID,
            TABLE_SELECTION,
            TABLE_SELECTION_TEXT,
            QtGui.QColor(TABLE_BG).darker(110).name(),
            TABLE_SELECTION,
            TABLE_SELECTION_TEXT,
            TABLE_HEADER_BG,
            LABEL_LIGHT,
            PANEL_BORDER,
            TABLE_HEADER_BG,
        ))
        self.setColumnWidth(0, 40)

    def mousePressEvent(self, event):
        idx = self.indexAt(event.pos())
        if idx.isValid():
            self._drag_start_row = idx.row()
        else:
            self._drag_start_row = None
        super(ReorderableTableWidget, self).mousePressEvent(event)

    def dropEvent(self, event):
        if self._animating:
            event.ignore()
            return
        try:
            target_idx = self.indexAt(event.pos())
            target_row = target_idx.row() if target_idx.isValid() else (self.rowCount()-1)
            src_row = self._drag_start_row
            if src_row is None:
                super(ReorderableTableWidget, self).dropEvent(event)
                return
            sel_q = self.selectionModel().selectedRows() or []
            sel_rows = sorted({s.row() for s in sel_q}) if sel_q else [src_row]
            if target_row in sel_rows:
                super(ReorderableTableWidget, self).dropEvent(event)
                return

            total = self.rowCount()
            old_rows = []
            for r in range(total):
                name = self.item(r,1).text() if self.item(r,1) else ""
                attr = self.item(r,2).text() if self.item(r,2) else "none"
                old_rows.append({"name":name, "attr":attr})
            sel_set = set(sel_rows)
            selected_block = [old_rows[i] for i in sel_rows]
            remaining = [old_rows[i] for i in range(total) if i not in sel_set]

            ref_item = old_rows[target_row] if 0 <= target_row < total else None
            if ref_item and ref_item in remaining:
                idx_in_rem = remaining.index(ref_item)
                insert_at = idx_in_rem if target_row < min(sel_rows) else idx_in_rem + 1
            else:
                insert_at = len(remaining)
            new_rows = remaining[:insert_at] + selected_block + remaining[insert_at:]

            # animation capture
            old_tops = [self._row_top(r) for r in range(total)]
            row_heights = [self.rowHeight(r) for r in range(total)]
            sel_ids = [i for i in range(total) if i in sel_set]
            remaining_ids = [i for i in range(total) if i not in sel_set]
            new_id_order = remaining_ids[:insert_at] + sel_ids + remaining_ids[insert_at:]
            cum = 0
            tops_by_newpos = []
            for nid in new_id_order:
                tops_by_newpos.append(cum)
                cum += row_heights[nid] if nid < len(row_heights) else 20
            new_tops = [0]*total
            for newpos, oldidx in enumerate(new_id_order):
                new_tops[oldidx] = tops_by_newpos[newpos]

            viewport = self.viewport()
            overlays = []
            anim_group = QtCore.QParallelAnimationGroup(self)
            for r in range(total):
                pix = self._capture_row_pixmap(r)
                lbl = QtWidgets.QLabel(viewport)
                lbl.setPixmap(pix)
                lbl.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
                lbl.setGeometry(0, old_tops[r], viewport.width(), row_heights[r])
                lbl.show()
                lbl.raise_()
                overlays.append(lbl)
                anim = QtCore.QPropertyAnimation(lbl, b"pos", self)
                anim.setDuration(self.ANIM_DURATION)
                anim.setEasingCurve(self.ANIM_EASING)
                anim.setStartValue(QtCore.QPoint(0, old_tops[r]))
                anim.setEndValue(QtCore.QPoint(0, new_tops[r]))
                anim_group.addAnimation(anim)

            self._animating = True

            def on_finished():
                for lbl in overlays:
                    try:
                        lbl.hide()
                        lbl.deleteLater()
                    except Exception:
                        pass
                try:
                    self.setRowCount(0)
                    for nr, rdict in enumerate(new_rows):
                        self.insertRow(nr)
                        self.setRowHeight(nr, TABLE_ROW_HEIGHT)
                        itn = QtWidgets.QTableWidgetItem(str(nr+1))
                        itn.setFlags(itn.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.setItem(nr,0,itn)
                        name_item = QtWidgets.QTableWidgetItem(rdict["name"])
                        name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.setItem(nr,1,name_item)
                        attr_item = QtWidgets.QTableWidgetItem(rdict["attr"])
                        attr_item.setFlags(attr_item.flags() ^ QtCore.Qt.ItemIsEditable)
                        self.setItem(nr,2,attr_item)
                        btn = QtWidgets.QPushButton("✕")
                        btn.setToolTip("Remove this row")
                        btn.setCursor(QtCore.Qt.PointingHandCursor)
                        btn.setFocusPolicy(QtCore.Qt.NoFocus)
                        btn.setStyleSheet(_btn_style_remove())
                        btn.setFixedSize(34, 34)
                        btn.clicked.connect(lambda checked=False, b=btn, t=self: ReorderableTableWidget._on_remove_button_clicked(t,b))
                        self.setCellWidget(nr,3,btn)
                except Exception:
                    traceback.print_exc()
                self._animating = False
                try:
                    self.clearSelection()
                    for i in range(len(sel_rows)):
                        self.selectRow(insert_at + i)
                except Exception:
                    pass

            anim_group.finished.connect(on_finished)
            anim_group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
            event.accept()
        except Exception:
            traceback.print_exc()
            try:
                super(ReorderableTableWidget, self).dropEvent(event)
            except Exception:
                pass

    def _row_top(self, row):
        y = 0
        for r in range(row):
            y += self.rowHeight(r)
        return y

    def _capture_row_pixmap(self, row):
        viewport = self.viewport()
        top = self._row_top(row)
        height = self.rowHeight(row)
        width = viewport.width()
        rect = QtCore.QRect(0, top, width, height)
        return viewport.grab(rect)

    @staticmethod
    def _on_remove_button_clicked(table, button):
        try:
            vp = table.viewport()
            pos = button.mapTo(vp, QtCore.QPoint(2,2))
            idx = table.indexAt(pos)
            if idx.isValid():
                row = idx.row()
                table.removeRow(row)
                for r in range(table.rowCount()):
                    it = table.item(r,0)
                    if it:
                        it.setText(str(r+1))
            else:
                for r in range(table.rowCount()):
                    w = table.cellWidget(r,3)
                    if w is button:
                        table.removeRow(r)
                        for rr in range(table.rowCount()):
                            it = table.item(rr,0)
                            if it:
                                it.setText(str(rr+1))
                        break
        except Exception:
            traceback.print_exc()

# Attribute picker (styled)
class AttributePickerDialog(QtWidgets.QDialog):
    attribute_chosen = QtCore.Signal(str)
    def __init__(self, objects, parent=None):
        super(AttributePickerDialog, self).__init__(parent)
        self.objects = list(objects)
        self.setWindowTitle("Pick Attribute")
        self.setMinimumSize(460,420)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._build_ui()
        self._fill_tree()

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10,10,10,10)
        outer.setSpacing(0)

        panel = QtWidgets.QFrame()
        panel.setObjectName("pickerPanel")
        panel.setStyleSheet(
            "QFrame#pickerPanel{ background:%s; border:1px solid %s; border-top-left-radius:12px; border-top-right-radius:0px; border-bottom-left-radius:12px; border-bottom-right-radius:12px; }"
            % (PANEL_BG_RGBA, PANEL_BORDER)
        )
        outer.addWidget(panel)

        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(0,0,8,8)
        panel_layout.setSpacing(6)

        self.title_bar = TitleBar(self, "Pick Attribute")
        panel_layout.addWidget(self.title_bar)

        body = QtWidgets.QWidget()
        body_layout = QtWidgets.QVBoxLayout(body)
        body_layout.setContentsMargins(12,10,12,12)
        body_layout.setSpacing(12)
        panel_layout.addWidget(body)

        top_row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel("Search:")
        lbl.setStyleSheet("color:%s; background: transparent; border: none;" % LABEL_LIGHT)
        top_row.addWidget(lbl)
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("search attribute...")
        self.edit_search.setStyleSheet(
            "background:%s; color:%s; border:1px solid %s; border-radius:10px; padding:6px;"
            "selection-background-color:%s; selection-color:%s;"
            % (DARK_2, LABEL_LIGHT, PANEL_BORDER, TABLE_SELECTION, TABLE_SELECTION_TEXT)
        )
        top_row.addWidget(self.edit_search,1)
        body_layout.addLayout(top_row)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet(
            "QTreeWidget {"
            "    background:%s;"
            "    color:%s;"
            "    border:1px solid %s;"
            "    border-radius:10px;"
            "    padding:8px;"
            "}"
            "QTreeWidget::item {"
            "    background: transparent;"
            "}"
            "QTreeWidget::item:selected {"
            "    background:%s;"
            "    color:%s;"
            "    border-radius:6px;"
            "}"
            % (TITLE_BG_RGBA, LABEL_LIGHT, PANEL_BORDER, TABLE_SELECTION, TABLE_SELECTION_TEXT)
        )
        body_layout.addWidget(self.tree, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Apply")
        self.btn_apply.setStyleSheet(_btn_style_basic())
        self.btn_cancel = QtWidgets.QPushButton("Cancel")
        self.btn_cancel.setStyleSheet(_btn_style_gray())
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_apply)
        body_layout.addLayout(btn_row)
        self.edit_search.textChanged.connect(self._fill_tree)
        self.tree.itemDoubleClicked.connect(self._on_double)
        self.btn_apply.clicked.connect(self._on_apply)
        self.btn_cancel.clicked.connect(self.reject)

    def _fill_tree(self):
        self.tree.clear()
        cats, common, union = categorize_attributes_for_objs(self.objects)
        q = (self.edit_search.text() or "").lower()
        for cat, items in cats.items():
            top = QtWidgets.QTreeWidgetItem(self.tree)
            top.setText(0, cat)
            top.setFlags(top.flags() & ~QtCore.Qt.ItemIsSelectable)
            for attr, present_all in items:
                if q and q not in attr.lower():
                    continue
                child = QtWidgets.QTreeWidgetItem(top)
                child.setText(0, attr)
                child.setData(0, QtCore.Qt.UserRole, attr)
                if not present_all:
                    f = child.font(0); f.setItalic(True); child.setFont(0, f)
        if q:
            self.tree.expandAll()
        else:
            self.tree.collapseAll()

    def _get_selected_attr(self):
        it = self.tree.currentItem()
        if not it:
            return None
        return it.data(0, QtCore.Qt.UserRole)

    def _on_double(self, item, col):
        attr = item.data(0, QtCore.Qt.UserRole)
        if attr:
            self.attribute_chosen.emit(attr)
            self.accept()

    def _on_apply(self):
        attr = self._get_selected_attr()
        if not attr:
            QtWidgets.QMessageBox.warning(self, "No attribute", "Please select an attribute first.")
            return
        self.attribute_chosen.emit(attr)
        self.accept()

# Main connector widget
class AttrConnectorWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(AttrConnectorWidget, self).__init__(parent)
        self.setStyleSheet("background-color:%s; color:%s;" % (DARK_1, LABEL_LIGHT))
        self._build_ui()
        self._connect_signals()
        if not MAYA_AVAILABLE:
            self.log_status(["Running in standalone Qt mode — Maya commands are disabled."])

    def _build_ui(self):
        L = QtWidgets.QVBoxLayout(self)
        L.setContentsMargins(12,10,12,12)
        L.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        left = QtWidgets.QVBoxLayout()
        hdr = QtWidgets.QHBoxLayout()
        lbl_src = QtWidgets.QLabel("Sources")
        lbl_src.setStyleSheet(
            "color:%s; font-weight:700; background: transparent; border: none;" % LABEL_LIGHT
        )
        hdr.addWidget(lbl_src)
        hdr.addStretch()
        self.btn_src_add_to = QtWidgets.QPushButton("Add to (Sources)")
        self.btn_src_add_to.setStyleSheet(_btn_style_basic())
        self.btn_src_clear = QtWidgets.QPushButton("Clear")
        self.btn_src_clear.setStyleSheet(_btn_style_gray())
        hdr.addWidget(self.btn_src_add_to)
        hdr.addWidget(self.btn_src_clear)
        left.addLayout(hdr)

        self.tbl_src = ReorderableTableWidget(0,4)
        self.tbl_src.setHorizontalHeaderLabels(["#", "Object", "Attribute", ""])
        self._setup_table(self.tbl_src)
        self.tbl_src_container = QtWidgets.QFrame()
        self.tbl_src_container.setObjectName("tableContainerLeft")
        self.tbl_src_container.setStyleSheet(
            "#tableContainerLeft { background:%s; border:1px solid %s; border-radius:12px; padding:4px; }"
            % (TABLE_BG, PANEL_BORDER)
        )
        src_container_layout = QtWidgets.QVBoxLayout(self.tbl_src_container)
        src_container_layout.setContentsMargins(6,6,6,6)
        src_container_layout.setSpacing(0)
        src_container_layout.addWidget(self.tbl_src)
        left.addWidget(self.tbl_src_container)

        row_btn = QtWidgets.QHBoxLayout()
        row_btn.addStretch()
        self.btn_src_add_attr = QtWidgets.QPushButton("Add Attribute")
        self.btn_src_add_attr.setStyleSheet(_btn_style_basic())
        row_btn.addWidget(self.btn_src_add_attr)
        left.addLayout(row_btn)
        top.addLayout(left,1)

        right = QtWidgets.QVBoxLayout()
        hdr2 = QtWidgets.QHBoxLayout()
        lbl_tgt = QtWidgets.QLabel("Targets")
        lbl_tgt.setStyleSheet(
            "color:%s; font-weight:700; background: transparent; border: none;" % LABEL_LIGHT
        )
        hdr2.addWidget(lbl_tgt)
        hdr2.addStretch()
        self.btn_tgt_add_to = QtWidgets.QPushButton("Add to (Targets)")
        self.btn_tgt_add_to.setStyleSheet(_btn_style_basic())
        self.btn_tgt_clear = QtWidgets.QPushButton("Clear")
        self.btn_tgt_clear.setStyleSheet(_btn_style_gray())
        hdr2.addWidget(self.btn_tgt_add_to)
        hdr2.addWidget(self.btn_tgt_clear)
        right.addLayout(hdr2)

        self.tbl_tgt = ReorderableTableWidget(0,4)
        self.tbl_tgt.setHorizontalHeaderLabels(["#", "Object", "Attribute", ""])
        self._setup_table(self.tbl_tgt)
        self.tbl_tgt_container = QtWidgets.QFrame()
        self.tbl_tgt_container.setObjectName("tableContainerRight")
        self.tbl_tgt_container.setStyleSheet(
            "#tableContainerRight { background:%s; border:1px solid %s; border-radius:12px; padding:4px; }"
            % (TABLE_BG, PANEL_BORDER)
        )
        tgt_container_layout = QtWidgets.QVBoxLayout(self.tbl_tgt_container)
        tgt_container_layout.setContentsMargins(6,6,6,6)
        tgt_container_layout.setSpacing(0)
        tgt_container_layout.addWidget(self.tbl_tgt)
        right.addWidget(self.tbl_tgt_container)

        row_btn2 = QtWidgets.QHBoxLayout()
        row_btn2.addStretch()
        self.btn_tgt_add_attr = QtWidgets.QPushButton("Add Attribute")
        self.btn_tgt_add_attr.setStyleSheet(_btn_style_basic())
        row_btn2.addWidget(self.btn_tgt_add_attr)
        right.addLayout(row_btn2)
        top.addLayout(right,1)
        L.addLayout(top)

        actions = QtWidgets.QHBoxLayout()
        self.btn_preview = QtWidgets.QPushButton("Preview")
        self.btn_preview.setStyleSheet(_btn_style_gray())
        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_connect.setStyleSheet(_btn_style_basic())
        self.btn_disconnect = QtWidgets.QPushButton("Disconnect")
        self.btn_disconnect.setStyleSheet(_btn_style_gray())
        actions.addWidget(self.btn_preview)
        actions.addWidget(self.btn_connect)
        actions.addWidget(self.btn_disconnect)
        actions.addStretch()
        L.addLayout(actions)

        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(200)
        self.txt_log.setStyleSheet(
            "background: %s; color:%s; border:1px solid %s; border-radius:12px; padding:10px;"
            % (DARK_2, LABEL_LIGHT, PANEL_BORDER)
        )
        L.addWidget(self.txt_log)

        self.tbl_src.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_tgt.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_src.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tbl_tgt.itemDoubleClicked.connect(self._on_item_double_clicked)

    def _connect_signals(self):
        self.btn_src_add_to.clicked.connect(lambda: self.add_to_table(self.tbl_src))
        self.btn_tgt_add_to.clicked.connect(lambda: self.add_to_table(self.tbl_tgt))
        self.btn_src_clear.clicked.connect(lambda: self.clear_table(self.tbl_src))
        self.btn_tgt_clear.clicked.connect(lambda: self.clear_table(self.tbl_tgt))
        self.btn_src_add_attr.clicked.connect(lambda: self.open_attribute_picker_for_table(self.tbl_src))
        self.btn_tgt_add_attr.clicked.connect(lambda: self.open_attribute_picker_for_table(self.tbl_tgt))
        self.btn_preview.clicked.connect(self.on_preview)          # now on_preview exists
        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)

    def _setup_table(self, table):
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Fixed)
        header.setDefaultAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        table.setColumnWidth(0, 60)
        table.setColumnWidth(3, 50)
        table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)

    def log_status(self, lines):
        self.txt_log.clear()
        for l in lines:
            self.txt_log.appendPlainText(l)

    def update_numbering(self):
        for tbl in (self.tbl_src, self.tbl_tgt):
            for r in range(tbl.rowCount()):
                it = tbl.item(r,0)
                if not it:
                    it = QtWidgets.QTableWidgetItem(str(r+1))
                    it.setFlags(it.flags() ^ QtCore.Qt.ItemIsEditable)
                    tbl.setItem(r,0,it)
                else:
                    it.setText(str(r+1))

    def clear_table(self, table):
        table.setRowCount(0)
        self.update_numbering()

    def add_row(self, table, obj_name, attr_name="none"):
        r = table.rowCount()
        table.insertRow(r)
        table.setRowHeight(r, TABLE_ROW_HEIGHT)
        num_item = QtWidgets.QTableWidgetItem(str(r+1))
        num_item.setFlags(num_item.flags() ^ QtCore.Qt.ItemIsEditable)
        table.setItem(r,0,num_item)
        name_item = QtWidgets.QTableWidgetItem(obj_name)
        name_item.setFlags(name_item.flags() ^ QtCore.Qt.ItemIsEditable)
        table.setItem(r,1,name_item)
        attr_item = QtWidgets.QTableWidgetItem(attr_name)
        attr_item.setFlags(attr_item.flags() ^ QtCore.Qt.ItemIsEditable)
        table.setItem(r,2,attr_item)
        btn = QtWidgets.QPushButton("✕")
        btn.setToolTip("Remove this row")
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setStyleSheet(_btn_style_remove())
        btn.setFixedSize(34, 34)
        btn.clicked.connect(lambda checked=False, b=btn, t=table: ReorderableTableWidget._on_remove_button_clicked(t,b))
        table.setCellWidget(r,3,btn)

    def add_to_table(self, table):
        sel = cmds.ls(selection=True) or []
        if not sel:
            if not MAYA_AVAILABLE:
                # Provide a placeholder row so the UI remains testable in Qt-only mode.
                placeholder_idx = table.rowCount() + 1
                self.add_row(table, "standalone_node_%d" % placeholder_idx)
                self.update_numbering()
            return
        for s in sel:
            self.add_row(table, s)
        self.update_numbering()

    def open_attribute_picker_for_table(self, table, rows_to_apply=None):
        sel_q = table.selectionModel().selectedRows() or []
        if rows_to_apply is None:
            rows = [s.row() for s in sel_q] if sel_q else list(range(table.rowCount()))
        else:
            rows = rows_to_apply if isinstance(rows_to_apply, (list,tuple)) else [rows_to_apply]
        if not rows:
            return
        objs = [table.item(r,1).text() for r in rows if table.item(r,1)]
        dlg = AttributePickerDialog(objs, parent=self)
        def apply_attr(attr):
            sel_now = table.selectionModel().selectedRows() or []
            target_rows = [s.row() for s in sel_now] if sel_now else rows
            if not target_rows:
                target_rows = rows
            for r in target_rows:
                item = table.item(r,2)
                if not item:
                    item = QtWidgets.QTableWidgetItem(attr)
                    item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
                    table.setItem(r,2,item)
                else:
                    item.setText(attr)
        dlg.attribute_chosen.connect(apply_attr)
        dlg.exec_()

    def _on_item_double_clicked(self, item):
        try:
            if item.column() == 2:
                tbl = item.tableWidget()
                row = item.row()
                self.open_attribute_picker_for_table(tbl, rows_to_apply=[row])
        except Exception:
            traceback.print_exc()

    # ---------------- connect/disconnect/preview logic ----------------
    def on_connect(self):
        src_count = self.tbl_src.rowCount()
        tgt_count = self.tbl_tgt.rowCount()
        if src_count == 0 or tgt_count == 0:
            self.log_status(["Nothing to connect"])
            return
        if not MAYA_AVAILABLE:
            self.log_status(["Preview only: Maya commands unavailable in standalone mode."])
            return

        src_objs = [self.tbl_src.item(i,1).text() if self.tbl_src.item(i,1) else "" for i in range(src_count)]
        tgt_objs = [self.tbl_tgt.item(i,1).text() if self.tbl_tgt.item(i,1) else "" for i in range(tgt_count)]
        src_attrs = [self.tbl_src.item(i,2).text() if self.tbl_src.item(i,2) else "none" for i in range(src_count)]
        tgt_attrs = [self.tbl_tgt.item(i,2).text() if self.tbl_tgt.item(i,2) else "none" for i in range(tgt_count)]

        status_lines = []
        # single source -> all targets
        if src_count == 1:
            src = src_objs[0]; sattr = src_attrs[0]
            if not sattr or sattr == "none":
                self.log_status(["Source attribute missing"])
                return
            cmds.undoInfo(openChunk=True)
            try:
                for j in range(tgt_count):
                    tgt = tgt_objs[j]; tattr = tgt_attrs[j]
                    if not tattr or tattr == "none":
                        continue
                    src_full = "{}.".format(src) + sattr
                    tgt_full = "{}.".format(tgt) + tattr
                    try:
                        if cmds.objExists(src_full) and cmds.objExists(tgt_full):
                            cmds.connectAttr(src_full, tgt_full, force=True)
                            status_lines.append("Connected %s -> %s" % (src_full, tgt_full))
                    except Exception:
                        continue
            finally:
                cmds.undoInfo(closeChunk=True)
            self.log_status(status_lines if status_lines else ["No connections made"])
            return

        # multiple sources -> require equal count
        if src_count > 1:
            if src_count != tgt_count:
                self.log_status(["Count mismatch: sources != targets"])
                return
            cmds.undoInfo(openChunk=True)
            try:
                for i in range(src_count):
                    src = src_objs[i]; sattr = src_attrs[i]
                    tgt = tgt_objs[i]; tattr = tgt_attrs[i]
                    if not sattr or sattr == "none" or not tattr or tattr == "none":
                        continue
                    src_full = "{}.".format(src) + sattr
                    tgt_full = "{}.".format(tgt) + tattr
                    try:
                        if cmds.objExists(src_full) and cmds.objExists(tgt_full):
                            cmds.connectAttr(src_full, tgt_full, force=True)
                            status_lines.append("Connected %s -> %s" % (src_full, tgt_full))
                    except Exception:
                        continue
            finally:
                cmds.undoInfo(closeChunk=True)
            self.log_status(status_lines if status_lines else ["No connections made"])
            return

    def on_disconnect(self):
        if not MAYA_AVAILABLE:
            self.log_status(["Preview only: Maya commands unavailable in standalone mode."])
            return
        pairs = self.gather_pairs_1to1()
        if not pairs:
            self.log_status(["No pairs to disconnect"])
            return
        status_lines = []
        cmds.undoInfo(openChunk=True)
        try:
            for src, sattr, tgt, tattr in pairs:
                if not sattr or sattr == "none" or not tattr or tattr == "none":
                    continue
                tf = "{}.".format(tgt) + tattr
                if not cmds.objExists(tf):
                    continue
                inc = cmds.listConnections(tf, source=True, destination=False, plugs=True) or []
                for c in inc:
                    if c == "{}.".format(src) + sattr:
                        try:
                            cmds.disconnectAttr(c, tf)
                            status_lines.append("Disconnected %s -> %s" % (c, tf))
                        except Exception:
                            continue
        finally:
            cmds.undoInfo(closeChunk=True)
        self.log_status(status_lines if status_lines else ["No disconnections"])

    def gather_pairs_1to1(self):
        pairs = []
        n = min(self.tbl_src.rowCount(), self.tbl_tgt.rowCount())
        for i in range(n):
            src = self.tbl_src.item(i,1).text() if self.tbl_src.item(i,1) else ""
            tgt = self.tbl_tgt.item(i,1).text() if self.tbl_tgt.item(i,1) else ""
            sattr = self.tbl_src.item(i,2).text() if self.tbl_src.item(i,2) else ""
            tattr = self.tbl_tgt.item(i,2).text() if self.tbl_tgt.item(i,2) else ""
            pairs.append((src, sattr, tgt, tattr))
        return pairs

    # ---------- the previously missing preview method ----------
    def on_preview(self):
        pairs = self.gather_pairs_1to1()
        if not pairs:
            self.log_status(["No pairs to preview"])
            return
        lines = ["Preview:"]
        for p in pairs:
            lines.append("  {}.{} -> {}.{}".format(p[0], p[1] or "<none>", p[2], p[3] or "<none>"))
        self.log_status(lines)

# Main window
class AttrConnectorWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(AttrConnectorWindow, self).__init__(parent)
        self.setObjectName(WINDOW_NAME)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(980,680)
        outer = QtWidgets.QWidget()
        outer.setStyleSheet("background: transparent;")
        ol = QtWidgets.QVBoxLayout(outer)
        ol.setContentsMargins(0,0,0,0)
        ol.setSpacing(0)
        panel = QtWidgets.QFrame()
        panel.setStyleSheet(
            "QFrame{ background:%s; border:1px solid %s; border-top-left-radius:12px; border-top-right-radius:12px; border-bottom-left-radius:12px; border-bottom-right-radius:12px; }"
            % (PANEL_BG_RGBA, PANEL_BORDER)
        )
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        panel.setGraphicsEffect(shadow)
        pl = QtWidgets.QVBoxLayout(panel)
        pl.setContentsMargins(0,0,0,8)
        pl.setSpacing(6)
        self.title = TitleBar(self, "Attribute Connector")
        pl.addWidget(self.title)
        self.body = AttrConnectorWidget(self)
        pl.addWidget(self.body)
        ol.addWidget(panel)
        self.setCentralWidget(outer)


def show_attr_connector_ui():
    app = QtWidgets.QApplication.instance()
    app_created = False
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
        app_created = True
    mw = maya_main_window()
    if mw:
        try:
            for w in mw.findChildren(QtWidgets.QMainWindow):
                if w.objectName() == WINDOW_NAME:
                    w.close()
        except Exception:
            pass
    win = AttrConnectorWindow(parent=mw)
    win.show()
    if app_created and not MAYA_AVAILABLE:
        app.exec_()
    return win


if __name__ == "__main__":
    show_attr_connector_ui()
