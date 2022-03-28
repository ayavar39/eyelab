import logging
import sys
import os
from functools import partial
from PySide6 import QtWidgets, QtGui
from PySide6.QtWidgets import QFileDialog

import eyepy as ep
from eyelab.config import EYELAB_FOLDER

from eyelab.views.ui.ui_main_window import Ui_MainWindow
from eyelab.views.workspace import Workspace
from eyelab.dialogs import ProceedDialog, NotificationDialog


class eyelab(QtWidgets.QMainWindow, Ui_MainWindow):
    """Create the main window that stores all of the widgets necessary for the application."""

    def __init__(self, parent=None):
        """Initialize the components of the main window."""
        super().__init__(parent)
        self.setupUi(self)

        self.save_path = None

        self.actionImportVol.triggered.connect(
            partial(self.import_data, method=ep.import_heyex_vol, format="file")
        )
        self.actionImportHEXML.triggered.connect(
            partial(self.import_data, method=ep.import_heyex_xml, format="folder")
        )
        self.actionImportRETOUCH.triggered.connect(
            partial(self.import_data, method=ep.import_retouch, format="folder")
        )
        self.actionImportDuke.triggered.connect(
            partial(self.import_data, method=ep.import_duke_mat, format="file")
        )
        self.actionImportBSFolder.triggered.connect(
            partial(self.import_data, method=ep.import_bscan_folder, format="folder")
        )
        self.actionSaveAnnotations.triggered.connect(self.save_annotations)
        self.actionSaveAnnotationsAs.triggered.connect(
            partial(self.save_annotations, save_as=True)
        )
        self.actionLoadAnnotations.triggered.connect(self.load_annotations)
        self.menuAnnotations.hide()
        self.actionOpen.triggered.connect(self.load)
        self.actionSave.triggered.connect(self.save)
        self.actionSave_As.triggered.connect(partial(self.save, save_as=True))
        self.actionShortcutSheet.triggered.connect(lambda: self.open_help("shortcuts"))
        self.actionAreaAnnotationGuide.triggered.connect(
            lambda: self.open_help("area_annotation")
        )
        self.actionLayerAnnotationGuide.triggered.connect(
            lambda: self.open_help("layer_annotation")
        )
        self.actionRegistrationGuide.triggered.connect(
            lambda: self.open_help("registration")
        )
        self.actionIntroduction.triggered.connect(
            lambda: self.open_help("introduction")
        )

        self.workspace = Workspace(parent=self)
        self.setCentralWidget(self.workspace)

        from eyepy.data import load

        # ev = load("drusen_patient")
        # ev.add_voxel_annotation(
        #    ep.drusen(ev.layers["RPE"], ev.layers["BM"], ev.shape), name="Drusen"
        # )
        # self.workspace.set_data(ev)

        # self.statusBar().showMessage("")

    def import_data(self, method, format):
        if not self.workspace.data is None:
            message = "The import repaces all data you have in your workspace. Do you want to proceed?"
            dialog = ProceedDialog(message=message, parent=self)
            if dialog.exec() == QtWidgets.QDialog.Rejected:
                return

        if format == "file":
            path = QFileDialog.getOpenFileName()[0]
        elif format == "folder":
            path = QFileDialog.getExistingDirectory()

        self.workspace.set_data(method(path))

    def open_help(self, topic):
        if topic == "introduction":
            dialog = IntroductionHelp(self)
        elif topic == "shortcuts":
            dialog = ShortcutHelp(self)
        elif topic == "area_annotation":
            dialog = AreaAnnotationHelp(self)
        elif topic == "layer_annotation":
            dialog = LayerAnnotationHelp(self)
        elif topic == "registration":
            dialog = RegistrationHelp(self)
        else:
            raise ValueError("topic not available")

        if dialog.exec() == QtWidgets.QDialog.Rejected:
            pass

    def get_save_location(self):
        if "PYCHARM_HOSTED" in os.environ:
            options = QFileDialog.DontUseNativeDialog
        else:
            options = None
        self.save_path, filter = QFileDialog.getSaveFileName(
            parent=self, caption="Save", filter="Eye files (*.eye)", options=options
        )
        if not self.save_path.endswith(".eye"):
            self.save_path = self.save_path + ".eye"
        return self.save_path

    def save(self, save_as=False):
        if self.save_path is None or save_as is True:
            path = self.get_save_location()
            if path == "":
                return

        self.workspace.data.save(self.save_path)

    def load(self):
        if self.workspace.data is not None:
            message = "Loading data replaces the current data. Do you want to proceed?"
            dialog = ProceedDialog(message=message, parent=self)
            if dialog.exec() == QtWidgets.QDialog.Rejected:
                return

        path = QFileDialog.getOpenFileName(
            parent=self,
            caption="Load",
            filter="Eye files (*.eye)",
        )[0]
        if path == "":
            return
        ev = ep.EyeVolume.load(path)
        self.workspace.set_data(ev)

    def save_annotations(self, save_as=False):
        if self.save_path is None or save_as is True:
            path = self.get_save_location()
            if path == "":
                return

        self.workspace.data.save_annotations(self.save_path)

    def load_annotations(self):
        if self.workspace.data is None:
            message = (
                "Annotations can only be loaded after importing the corresponding data."
            )
            dialog = NotificationDialog(message=message, parent=self)
            dialog.exec()
            return
        message = "Loading annotations replaces all current annotations. Do you want to proceed?"
        dialog = ProceedDialog(message=message, parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            path = QFileDialog.getOpenFileName()[0]
            self.workspace.data.load_annotations(path)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        # Save all unchanged annotations
        # Todo: Ask for save if there is unsaved work
        if self.workspace.data_changed:
            message = "Do you want to save before closing?"
            dialog = ProceedDialog(message=message, parent=self)
            if dialog.exec() == QtWidgets.QDialog.Accepted:
                self.actionSaveAnnotations.trigger()
        super().closeEvent(a0)


def main(log_level=logging.DEBUG):
    # create logger for "oat" application
    logger = logging.getLogger("eyelab")
    logger.setLevel(logging.DEBUG)

    # create file handler which logs debug messages
    fh = logging.FileHandler(EYELAB_FOLDER / "eyelab.log")
    fh.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    fh.setFormatter(file_formatter)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    cmd_formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    ch.setFormatter(cmd_formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("Starting Application.")

    application = QtWidgets.QApplication(sys.argv)
    window = eyelab()
    # desktop = QtGui.QScreen().availableGeometry()
    # width = (desktop.width() - window.width()) / 2
    # height = (desktop.height() - window.height()) / 2
    # window.show()
    # window.move(width, height)
    window.showMaximized()

    sys.exit(application.exec())


if __name__ == "__main__":
    main()
