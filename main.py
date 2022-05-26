#!/usr/bin/env python3

from PyQt5.QtWidgets import (QApplication, QDialog, QLineEdit, QWidget, QMainWindow,
                             QVBoxLayout, QHBoxLayout,
                             QPushButton, QListWidget, QListWidgetItem, QLabel)
from PyQt5 import QtCore

import sys
import socket

from dataclasses import dataclass


@dataclass()
class OpenFDDParam:
    name: str
    description: str
    type: str
    typeInfo: list[str]


class OpenFDDDeviceAction():
    def __init__(self,
                 connection: 'OpenFDDConnection',
                 device: 'OpenFDDDevice',
                 id: str, name: str, description: str) -> None:
        self.device = device
        self.name = name
        self.id = id
        self.description = description
        self._connection = connection

    def getParams(self) -> list[OpenFDDParam]:
        command = f"list-action-params,{self.device.id},{self.id}"
        self._connection.sendLine(command)

        line = self._connection.readLine()
        params: list[OpenFDDParam] = []

        while line[0] != "done" and line[0] != "fail":
            paramName = line[0]
            paramDescription = line[1]
            paramType = line[2]

            params.append(OpenFDDParam(paramName,
                          paramDescription, paramType, line[2:]))
            line = self._connection.readLine()

        print(params)
        return params

    def run(self, params: list[str]):
        command = f"action-run,{self.device.id},{self.id},"
        for param in params:
            command += param + ','

        self._connection.sendLine(command)

        if self._connection.readLine()[0] != "done":
            raise Exception("Couldn't run action!")


class OpenFDDDevice():
    def __init__(self, connection: 'OpenFDDConnection', id: str, name: str) -> None:
        self._connection = connection
        self.id = id
        self.name = name

    def __repr__(self) -> str:
        return f"OpenFDDDevice('{self.name}')"

    def getActions(self) -> list[OpenFDDDeviceAction]:
        self._connection.sendLine("list-actions," + self.id)

        line = self._connection.readLine()
        actions: list[OpenFDDDeviceAction] = []

        while line[0] != "done" and line[0] != "fail":
            actionID, actionName, actionDescription = line
            actions.append(OpenFDDDeviceAction(
                self._connection, self, actionID, actionName, actionDescription))
            line = self._connection.readLine()

        return actions


class OpenFDDConnection():
    def __init__(self):
        self._unixSocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    def connect(self):
        # TODO: Make this user-defined!
        # TODO: Error handling
        self._unixSocket.connect("/var/run/openfdd.socket")

    def readLine(self) -> list[str]:
        # TODO/NOTE: Won't work all the time if a notification occured :/
        # TODO: Handle notifications

        items: list[str] = []
        currentItem = ""

        parsingEscape = False

        while True:
            char = self._unixSocket.recv(1)

            if char == b'\\':
                parsingEscape = True
                continue

            if char == b',' and not parsingEscape:
                items.append(currentItem)
                currentItem = ""
                continue

            if char == b'\n':
                items.append(currentItem)
                break

            currentItem += char.decode('ascii')
            parsingEscape = False

        print("Got a line:", items)

        return items

    def sendLine(self, command: str):
        print("Running:", command)

        command += '\n'
        self._unixSocket.send(command.encode("ascii"))

    def checkHeader(self) -> bool:
        return self.readLine()[0].startswith("openfdd")

    def getDevices(self) -> list[OpenFDDDevice]:
        self.sendLine("list-devices")

        line = self.readLine()

        devices: list[OpenFDDDevice] = []

        # TODO: Move error checking to self.read_line()?
        while line[0] != "done" and line[0] != "fail":
            device_id, name = line
            devices.append(OpenFDDDevice(self, device_id, name))

            line = self.readLine()

        # TODO: Check for failure

        return devices


class ActionRunnerPopup(QWidget):
    def __init__(self, parent: QWidget, action: OpenFDDDeviceAction) -> None:
        super().__init__(parent, QtCore.Qt.Dialog)

        self.action = action

        self._paramsValueEdits: dict[str, QLineEdit] = {}

        layout = QVBoxLayout()

        layout.addWidget(QLabel(action.id))

        for param in action.getParams():
            paramWidget = self._createParamWidget(param)
            layout.addWidget(paramWidget)

        runButton = QPushButton("Run action")
        runButton.clicked.connect(self._run)
        layout.addWidget(runButton)

        self.setLayout(layout)

    def _createParamWidget(self, param: OpenFDDParam) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()

        nameAndDescription = self._createParamNameAndDescriptionWidget(param)
        layout.addWidget(nameAndDescription)

        paramValueEdit = QLineEdit()
        self._paramsValueEdits[param.name] = paramValueEdit
        layout.addWidget(paramValueEdit)

        widget.setLayout(layout)
        return widget

    def _createParamNameAndDescriptionWidget(self, param: OpenFDDParam) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel(param.name))
        layout.addWidget(QLabel(param.description))

        widget.setLayout(layout)
        return widget

    def _run(self):
        paramValues: list[str] = []

        for param in self.action.getParams():
            paramValues.append(self._paramsValueEdits[param.name].text())

        self.action.run(paramValues)
        self.close()


class ListItemDeviceWidget(QWidget):
    def __init__(self, dev: OpenFDDDevice, parent=None) -> None:
        super(ListItemDeviceWidget, self).__init__(parent)

        self.device = dev

        label = QLabel(dev.name)
        layout = QHBoxLayout()
        layout.addWidget(label)

        self.setLayout(layout)


class DeviceActionWidget(QDialog):
    def __init__(self, action: OpenFDDDeviceAction, parent=None) -> None:
        super().__init__(parent)

        self.action = action

        layout = QHBoxLayout()

        nameAndDescription = self._createNameDescriptionWidget()
        layout.addWidget(nameAndDescription, 90)

        runButton = QPushButton("Run")
        runButton.clicked.connect(self._run)
        layout.addWidget(runButton, 10)

        self.setLayout(layout)

    def _createNameDescriptionWidget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        nameLabel = QLabel(self.action.name)
        layout.addWidget(nameLabel)

        descriptionLabel = QLabel(self.action.description)
        layout.addWidget(descriptionLabel)

        widget.setLayout(layout)
        return widget

    def _run(self):
        self.popupWindow = ActionRunnerPopup(self, self.action)
        self.popupWindow.show()


class OpenFDDControllerWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.openfddConnection = OpenFDDConnection()
        self.openfddConnection.connect()

        if not self.openfddConnection.checkHeader():
            raise Exception("Couldn't open connection to OpenFDD daemon!")

        self._mainWidget = QWidget()
        self._mainLayout = QHBoxLayout()
        self._mainWidget.setLayout(self._mainLayout)

        self._deviceList = self._createDeviceList()
        self._deviceConfigView = self._createDeviceConfigView()
        self._mainLayout.addWidget(self._deviceList, 33)
        self._mainLayout.addWidget(self._deviceConfigView, 67)

        self._deviceList.itemClicked.connect(
            lambda item: self.__deviceListClickHandler(item))

        self.setCentralWidget(self._mainWidget)

    def __deviceListClickHandler(self, itemClicked):
        deviceItem = self._deviceList.itemWidget(itemClicked)
        device = deviceItem.device

        layout = self._deviceConfigView.layout()

        for layoutItemIndex in reversed(range(layout.count())):
            layout.itemAt(layoutItemIndex).widget().deleteLater()

        for action in device.getActions():
            actionWidget = DeviceActionWidget(action)
            layout.addWidget(actionWidget)

    def _createDeviceList(self) -> QListWidget:
        deviceList = QListWidget()

        for connectionDevice in self.openfddConnection.getDevices():
            item = QListWidgetItem(deviceList)
            deviceList.addItem(item)
            deviceList.setItemWidget(
                item, ListItemDeviceWidget(connectionDevice))

        return deviceList

    def _createDeviceConfigView(self) -> QWidget:
        deviceConfig = QWidget()
        deviceConfigLayout = QVBoxLayout()
        deviceConfigLayout.setAlignment(QtCore.Qt.AlignTop)

        deviceConfig.setLayout(deviceConfigLayout)

        return deviceConfig


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OpenFDD Controller")

    window = OpenFDDControllerWindow()

    window.setWindowFlag(QtCore.Qt.Dialog)
    window.resize(800, 600)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
