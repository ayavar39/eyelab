import logging

import eyepy as ep
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWidgets import QWidget
from eyelab.models.treeitemdelegate import TreeItemDelegate
from eyelab.models.treeview.itemmodel import (
    EnfaceTreeItemModel,
    TreeItem,
    TreeItemModel,
    VolumeTreeItemModel,
)
from eyelab.tools import area_tools, basic_tools, line_tools
from eyelab.views.ui.ui_scene_tab import Ui_SceneTab
import time
import os

def is_gpu_available():
    try:
        # Run a simple command to check if nvidia-smi is available
        result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # If the command runs successfully, assume GPU is available
        return result.returncode == 0
    except Exception:
        # If an exception occurs, assume GPU is not available
        return False

'''
def is_gpu_available():
    try:
        # Run a simple command to check if nvidia-smi is available
        result = os.system('nvidia-smi')

        # If the command runs successfully, assume GPU is available
        return result == 0
    except Exception as e:
        # If an exception occurs, assume GPU is not available
        # print(f"Error: {e}")
        return False
'''

logger = logging.getLogger("eyelab.viewtab")


class ViewTab(QWidget, Ui_SceneTab):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.data = data
        self.model: TreeItemModel = None

        self.line_tools = line_tools()
        self.area_tools = area_tools()
        self.basic_tools = basic_tools()

        self.upButton.clicked.connect(self.layer_up)
        self.downButton.clicked.connect(self.layer_down)
        self.downButton.clicked.connect(self.layer_down)
        self.opacitySlider.valueChanged.connect(self.set_opacity)

        # Todo: Fix bugs to enable featuress
        self.opacitySliderLabel.hide()
        self.opacitySlider.hide()
        self.upButton.hide()
        self.downButton.hide()

        self.current_tool = None
        self.setTools(self.basic_tools)

    # @property
    # def workspace(self):
    #    return self.parent()

    def set_model(self, model: TreeItemModel):
        self.model = model
        self.addButton.clicked.connect(self._add_annotation)
        self.deleteButton.clicked.connect(self._remove_annotation)

    def _remove_annotation(self):
        index = self.imageTreeView.selectionModel().currentIndex()
        self.model.remove_annotation(index)

    def _add_annotation(self):
        self.model.add_annotation()

    def configure_imageTreeView(self):
        self.imageTreeView.setModel(self.model)
        self.imageTreeView.header().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for col in range(1, self.model.columnCount()):
            self.imageTreeView.hideColumn(col)
        self.imageTreeView.setHeaderHidden(True)
        self.imageTreeView.setItemDelegate(TreeItemDelegate(self.imageTreeView))
        self.imageTreeView.setRootIsDecorated(False)

        self.imageTreeView.selectionModel().currentRowChanged.connect(
            self.on_currentChanged
        )

        self.imageTreeView.expandAll()

        self.imageTreeView.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        duplicate_action = QtGui.QAction(self)
        duplicate_action.setText("Duplicate All")
        duplicate_action.triggered.connect(self.duplicate_volume)

        self.imageTreeView.addAction(duplicate_action)

    def duplicate_volume(self):
        self.model.duplicate_volume(self.imageTreeView.selectionModel().currentIndex())

    def tools(self):
        return self._tools

    def setTools(self, tools=None, default="inspection"):
        if tools is None:
            tools = self.basic_tools
        self._tools = tools
        self._set_tool_buttons()
        self._switch_to_tool(default)()

    def _set_tool_buttons(self):
        layout = self.toolsWidget.layout()
        # Remove previous tools
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)
        # Add current tools
        for i, (name, tool) in enumerate(self.tools().items()):
            layout.addWidget(tool.button, 1, i, 1, 1)
            tool.button.clicked.connect(self._switch_to_tool(name))

    def _switch_to_tool(self, name):
        def func():
            tool = self._tools[name]
            for n, t in self._tools.items():
                t.button.setChecked(False)
                t.disable()
            tool.button.setChecked(True)

            # Show tool options
            self.toolboxWidget.layout().removeWidget(self.optionsWidget)
            self.optionsWidget.setParent(None)
            self.toolboxWidget.layout().addWidget(tool.options_widget)

            self.optionsWidget = tool.options_widget
            self.toolboxWidget.repaint()

            self.current_tool = tool
            tool.enable()

            # if self.tool.paint_preview.scene() == self.scene():
            #    self.scene().removeItem(self.tool.paint_preview)
            # self.tool.paint_preview.setParentItem(
            #    self.scene().activePanel())

        return func

    def set_opacity(self, value):
        self.model.tree_root.setOpacity(value / 100)

    def layer_up(self):
        selected = self.imageTreeView.selectionModel().currentIndex()

        parent = selected.parent()
        row1 = selected.row()
        row2 = row1 - 1

        if 0 < row1 <= parent.internalPointer().childCount():
            self.model.switchRows(row2, row1, parent)
            # self.imageTreeView.selectionModel().currentRowChanged.emit(
            #    self.model.index(row1, 0, parent),
            #    self.model.index(row2, 0, parent))

    def layer_down(self):
        selected = self.imageTreeView.selectionModel().currentIndex()

        parent = selected.parent()
        source_row = selected.row()
        target_row = source_row + 1

        if 0 <= source_row < parent.internalPointer().childCount() - 1:
            self.model.switchRows(source_row, target_row, parent)
            # self.imageTreeView.selectionModel().currentRowChanged.emit(
            #    self.model.index(row1, 0, parent),
            #    self.model.index(row2, 0, parent))

    @QtCore.Slot("QModelIndex", "QModelIndex")
    def on_currentChanged(self, current, previous):
        current_tree_item = self.model.getItem(current)
        previous_tree_item = self.model.getItem(previous)

        # Change activated item
        self.model.activate(current)
        self.model.deactivate(previous)

        # Set tools for current item
        if current_tree_item.parent.data("name") == "Layers":
            self.line_tools["spline"].options_widget.set_data(
                current_tree_item.itemData
            )
            self.setTools(self.line_tools, default="spline")
        elif current_tree_item.parent.data("name") == "Areas":
            self.setTools(self.area_tools, default="pen")

class VolumeTab(ViewTab):
    def __init__(self, data: ep.KnotEyeVolume, parent=None):
        super().__init__(data, parent)
        self.set_model(VolumeTreeItemModel(data=data, parent=self))
        self.configure_imageTreeView()

        # Connect the buttons to the corresponding functions # Thomas
        self.brightnessIncreaseButton.clicked.connect(self.increase_brightness)
        self.brightnessDecreaseButton.clicked.connect(self.decrease_brightness)

        # Connect the buttons to the corresponding functions # Thomas
        self.contrastIncreaseButton.clicked.connect(self.increase_contrast)
        self.contrastDecreaseButton.clicked.connect(self.decrease_contrast)

    def next_slice(self):
        self.model.next_slice(self.current_tool)
        self.model.scene.addItem(self.current_tool.paint_preview)
        self.model.scene.set_image() 

    def last_slice(self):
        self.model.last_slice(self.current_tool)
        self.model.scene.addItem(self.current_tool.paint_preview)
        self.model.scene.set_image() 
    
    #########
    # The required functions for connecting buttons to functions
    def increase_brightness(self): 
        try:
            # Assuming 'self.data' is the instance of ep.KnotEyeVolume
            if not is_gpu_available():
                self.data.increase_brightness_cpu()
                print("cpu")
            else:                                  
                self.data.increase_brightness() 
                print("gpu")
            self.model.scene.set_image() 

        except Exception as e:
            print(f"Error: {e}")

    def decrease_brightness(self):
        try:
            # Assuming 'self.data' is the instance of ep.KnotEyeVolume
            if not is_gpu_available():
                self.data.decrease_brightness_cpu()                      
            else:
                self.data.decrease_brightness() # 
            self.model.scene.set_image()  

        except Exception as e:
            print(f"Error: {e}")
    
    def increase_contrast(self):
        try:
            # Assuming 'self.data' is the instance of ep.KnotEyeVolume                            
            if not is_gpu_available():
                self.data.increase_contrast_cpu()
            else: 
                self.data.increase_contrast() # increase_contrast_cpu    
            self.model.scene.set_image() 

        except Exception as e:
            print(f"Error: {e}")


    def decrease_contrast(self):
        try:
            # Assuming 'self.data' is the instance of ep.KnotEyeVolume
            if not is_gpu_available():            
                self.data.decrease_contrast_cpu()
            else:
                self.data.decrease_contrast() #  
            self.model.scene.set_image()  

        except Exception as e:
            print(f"Error: {e}")

    #########


    @property
    def current_item(self):
        model_index = self.imageTreeView.selectionModel().currentIndex()
        tree_item = self.model.getItem(model_index)
        if type(tree_item) == TreeItem:
            item = self.model.annotation_items[id(tree_item.annotation)][
                self.model.current_slice
            ]
            return item


class EnfaceTab(ViewTab):
    def __init__(self, data: ep.EyeEnface, parent=None):
        super().__init__(data, parent)
        self.set_model(EnfaceTreeItemModel(data=data, parent=self))

        self.configure_imageTreeView()

    @property
    def current_item(self):
        model_index = self.imageTreeView.selectionModel().currentIndex()
        tree_item = self.model.getItem(model_index)
        if type(tree_item) == TreeItem:
            item = self.model.annotation_items[id(tree_item.annotation)]
            return item
