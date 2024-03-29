#!/usr/bin/python

'''
*************************************************************************
 *
 * Fracktal Works
 * __________________
 * Authors: Vijay Varada
 * Created: Nov 2016
 *
 * Licence: AGPLv3
*************************************************************************
'''
import mainGUI_volterra_400_dual
import keyboard
import dialog
import styles

from PyQt4 import QtCore, QtGui
import time
import sys
import subprocess
from octoprintAPI import octoprintAPI
from hurry.filesize import size
from datetime import datetime
# from functools import partial
import qrcode
# pip install websocket-client
import websocket
import json
import random
import uuid
import os
# import serial
import io
import requests
import re

import RPi.GPIO as GPIO


GPIO.setmode(GPIO.BCM)  # Use the board numbering scheme
GPIO.setwarnings(False)  # Disable GPIO warnings

# TODO:
'''
# Remove SD card capability from octoprint settings
# Should add error/status checking in the response in some functions in the octoprintAPI
# session keys??
# printer status should show errors from printer.
# async requests
# http://eli.thegreenplace.net/2011/04/25/passing-extra-arguments-to-pyqt-slot
# fix wifi
# status bar netweorking and wifi stuff
# reconnect to printer using GUI
# check if disk is getting full
# recheck for internet being conneted, refresh button
# load filaments from a file
# store settings to a file
# change the way active extruder print stores the current active extruder using positionEvent
#settings should show the current wifi
#clean up keyboard nameing
#add asertions and exeptions
#disaable done button if empty
#oncancel change filament cooldown
#toggle temperature indipendant of motion
#get active extruder from motion controller. when pausing, note down and resume with active extruder
#QR code has dictionary with IP address also
Testing:
# handle nothing selected in file select menus when deleting and printing etc.
# Delete items from local and USB
# different file list pages for local and USB
# test USB/Local properly
# check for uploading error when uploading from USB
# Test if active extruder goes back after pausing
# TRy to fuck with printing process from GUI
# PNG Handaling
# dissable buttons while printing
'''

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++Global variables++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

ip = '0.0.0.0:5000'
apiKey = 'B508534ED20348F090B4D0AD637D3660'

file_name = ''
Development = True
filaments = [
                ("PLA", 220),
                ("ABS", 240),
                ("PETG", 240),
                ("PVA", 230),
                ("TPU", 240),
                ("Nylon", 250),
                ("PolyCarbonate", 265),
                ("HIPS", 240),
                ("WoodFill", 220),
                ("CopperFill", 200),
                ("Breakaway", 240)
]     }


calibrationPosition = {'X1': 340, 'Y1': 42,
                       'X2': 30, 'Y2': 42,
                       'X3': 185, 'Y3': 352,
                       'X4': 185, 'Y4': 42
                       }

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


def run_async(func):
    '''
    Function decorater to make methods run in a thread
    '''
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def getIP(interface):
    try:
        scan_result = \
            subprocess.Popen("ifconfig | grep " + interface + " -A 1", stdout=subprocess.PIPE, shell=True).communicate()[0]
        # Processing STDOUT into a dictionary that later will be converted to a json file later
        # scan_result = scan_result.split(
        #     '\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
        # scan_result = [s.strip() for s in scan_result]
        # # scan_result = [s.strip('"') for s in scan_result]
        # scan_result = filter(None, scan_result)
        # ip = scan_result[1][scan_result[1].index('inet ') + 5: 23]
        match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", scan_result)
        # print(scan_result)
        print(match)
        if match:
            return match.group(1)
        return None
    except:
        return None


def getMac(interface):
    try:
        mac = subprocess.Popen(" cat /sys/class/net/" + interface + "/address", 
                               stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not mac:
            return "Not found"
        return mac.upper()
    except:
        return "Error"


def getWifiAp():
    try:
        ap = subprocess.Popen("iwgetid -r", 
                              stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not ap:
            return "Not connected"
        return ap
    except:
        return "Error"


def getHostname():
    try:
        hostname = subprocess.Popen("cat /etc/hostname", stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not hostname:
            return "Not connected"
        return hostname + ".local"
    except:
        return "Error"


class BuzzerFeedback(object):
    def __init__(self, buzzerPin):
        GPIO.cleanup()
        self.buzzerPin = buzzerPin
        GPIO.setup(self.buzzerPin, GPIO.OUT)
        GPIO.output(self.buzzerPin, GPIO.LOW)

    @run_async
    def buzz(self):
        GPIO.output(self.buzzerPin, (GPIO.HIGH))
        time.sleep(0.005)
        GPIO.output(self.buzzerPin, GPIO.LOW)


buzzer = BuzzerFeedback(12)

'''
To get the buzzer to beep on button press
'''

OriginalPushButton = QtGui.QPushButton
OriginalToolButton = QtGui.QToolButton


class QPushButtonFeedback(QtGui.QPushButton):
    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        OriginalPushButton.mousePressEvent(self, QMouseEvent)


class QToolButtonFeedback(QtGui.QToolButton):
    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        OriginalToolButton.mousePressEvent(self, QMouseEvent)


QtGui.QToolButton = QToolButtonFeedback
QtGui.QPushButton = QPushButtonFeedback


class Image(qrcode.image.base.BaseImage):
    def __init__(self, border, width, box_size):
        self.border = border
        self.width = width
        self.box_size = box_size
        size = (width + border * 2) * box_size
        self._image = QtGui.QImage(
            size, size, QtGui.QImage.Format_RGB16)
        self._image.fill(QtCore.Qt.white)

    def pixmap(self):
        return QtGui.QPixmap.fromImage(self._image)

    def drawrect(self, row, col):
        painter = QtGui.QPainter(self._image)
        painter.fillRect(
            (col + self.border) * self.box_size,
            (row + self.border) * self.box_size,
            self.box_size, self.box_size,
            QtCore.Qt.black)

    def save(self, stream, kind=None):
        pass


class ClickableLineEdit(QtGui.QLineEdit):
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self, parent)

    def mousePressEvent(self, QMouseEvent):
        buzzer.buzz()
        self.emit(QtCore.SIGNAL("clicked()"))


class MainUiClass(QtGui.QMainWindow, mainGUI_volterra_400_dual.Ui_MainWindow):
    '''
    Main GUI Workhorse, all slots and events defined within
    The main implementation class that inherits methods, variables etc from mainGUI_volterra_400_dual.py and QMainWindow
    '''

    def setupUi(self, MainWindow):
        super(MainUiClass, self).setupUi(MainWindow)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("Gotham"))
        font.setPointSize(15)

        self.wifiPasswordLineEdit = ClickableLineEdit(self.wifiSettingsPage)
        self.wifiPasswordLineEdit.setGeometry(QtCore.QRect(0, 170, 480, 60))
        self.wifiPasswordLineEdit.setFont(font)
        self.wifiPasswordLineEdit.setStyleSheet(styles.textedit)
        self.wifiPasswordLineEdit.setObjectName(_fromUtf8("wifiPasswordLineEdit"))

        font.setPointSize(11)
        self.ethStaticIpLineEdit = ClickableLineEdit(self.ethStaticSettings)
        self.ethStaticIpLineEdit.setGeometry(QtCore.QRect(120, 10, 300, 30))
        self.ethStaticIpLineEdit.setFont(font)
        self.ethStaticIpLineEdit.setStyleSheet(styles.textedit)
        self.ethStaticIpLineEdit.setObjectName(_fromUtf8("ethStaticIpLineEdit"))

        self.ethStaticGatewayLineEdit = ClickableLineEdit(self.ethStaticSettings)
        self.ethStaticGatewayLineEdit.setGeometry(QtCore.QRect(120, 60, 300, 30))
        self.ethStaticGatewayLineEdit.setFont(font)
        self.ethStaticGatewayLineEdit.setStyleSheet(styles.textedit)
        self.ethStaticGatewayLineEdit.setObjectName(_fromUtf8("ethStaticGatewayLineEdit"))

        self.menuCartButton.setDisabled(True)

        self.movie = QtGui.QMovie("templates/img/loading.gif")
        self.loadingGif.setMovie(self.movie)
        self.movie.start()

    def __init__(self):
        '''
        This method gets called when an object of type MainUIClass is defined
        '''
        super(MainUiClass, self).__init__()
        # Calls setupUi that sets up layout and geometry of all UI elements
        self.setupUi(self)
        self.stackedWidget.setCurrentWidget(self.loadingPage)
        self.setStep(10)
        self.keyboardWindow = None
        self.changeFilamentHeatingFlag = False
        self.setHomeOffsetBool = False
        self.currentImage = None
        self.currentFile = None
        self.sanityCheck = ThreadSanityCheck()
        self.sanityCheck.start()
        self.connect(self.sanityCheck, QtCore.SIGNAL('LOADED'), self.proceed)
        self.connect(self.sanityCheck, QtCore.SIGNAL('STARTUP_ERROR'), self.handleStartupError)
        self.setNewToolZOffsetFromCurrentZBool = False
        self.setActiveExtruder(0)

        self.dialog_doorlock = None
        self.dialog_filamentsensor = None

        for spinbox in self.findChildren(QtGui.QSpinBox):
            lineEdit = spinbox.lineEdit()
            lineEdit.setReadOnly(True)
            lineEdit.setDisabled(True)
            p = lineEdit.palette()
            p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(40, 40, 40))
            lineEdit.setPalette(p)

        # Thread to get the get the state of the Printer as well as the temperature

    def proceed(self, virtual):
        '''
        Startes websocket, as well as initialises button actions and callbacks. THis is done in such a manner so that the callbacks that dnepend on websockets
        load only after the socket is available which in turn is dependent on the server being available which is checked in the sanity check thread
        '''
        self.QtSocket = QtWebsocket()
        self.QtSocket.start()
        self.setActions()
        self.movie.stop()
        self.stackedWidget.setCurrentWidget(MainWindow.homePage)
        self.isFilamentSensorInstalled()
        self.virtualPrinterMode.setVisible(virtual)
        self.setIPStatus()

    def setActions(self):

        '''
        defines all the Slots and Button events.
        '''
        #--Dual Caliberation Addition--
        self.connect(self.QtSocket, QtCore.SIGNAL('SET_Z_TOOL_OFFSET'), self.setZToolOffset)
        self.connect(self.QtSocket, QtCore.SIGNAL('Z_PROBE_OFFSET'), self.updateEEPROMProbeOffset) #sets the current position of the probe offset to eeprom
        self.connect(self.QtSocket, QtCore.SIGNAL('TEMPERATURES'), self.updateTemperature)
        self.connect(self.QtSocket, QtCore.SIGNAL('STATUS'), self.updateStatus)
        self.connect(self.QtSocket, QtCore.SIGNAL('PRINT_STATUS'), self.updatePrintStatus)
        self.connect(self.QtSocket, QtCore.SIGNAL('UPDATE_STARTED'), self.softwareUpdateProgress)
        self.connect(self.QtSocket, QtCore.SIGNAL('UPDATE_LOG'), self.softwareUpdateProgressLog)
        self.connect(self.QtSocket, QtCore.SIGNAL('UPDATE_LOG_RESULT'), self.softwareUpdateResult)
        self.connect(self.QtSocket, QtCore.SIGNAL('UPDATE_FAILED'), self.updateFailed)
        self.connect(self.QtSocket, QtCore.SIGNAL('CONNECTED'), self.onServerConnected)
        self.connect(self.QtSocket, QtCore.SIGNAL('FILAMENT_SENSOR_TRIGGERED'), self.filamentSensorHandler)
        self.connect(self.QtSocket, QtCore.SIGNAL('FIRMWARE_UPDATER'), self.firmwareUpdateHandler)
        self.connect(self.QtSocket, QtCore.SIGNAL('Z_PROBING_FAILED'), self.showProbingFailed)
        self.connect(self.QtSocket, QtCore.SIGNAL('TOOL_OFFSET'), self.getToolOffset)
        self.connect(self.QtSocket, QtCore.SIGNAL('ACTIVE_EXTRUDER'), self.setActiveExtruder)
        self.connect(self.QtSocket, QtCore.SIGNAL('DOOR_LOCK_STATE'), self.doorLockHandler)
        self.connect(self.QtSocket, QtCore.SIGNAL('DOOR_LOCK_MSG'), self.doorLockMsg)

        # Text Input events
        self.connect(self.wifiPasswordLineEdit, QtCore.SIGNAL("clicked()"),
                     lambda: self.startKeyboard(self.wifiPasswordLineEdit.setText))
        self.connect(self.ethStaticIpLineEdit, QtCore.SIGNAL("clicked()"),
                     lambda: self.ethShowKeyboard(self.ethStaticIpLineEdit))
        self.connect(self.ethStaticGatewayLineEdit, QtCore.SIGNAL("clicked()"),
                     lambda: self.ethShowKeyboard(self.ethStaticGatewayLineEdit))

        # Button Events:

        # Home Screen:
        self.stopButton.pressed.connect(self.stopActionMessageBox)
        self.menuButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.controlButton.pressed.connect(self.control)
        self.playPauseButton.clicked.connect(self.playPauseAction)
        self.doorLockButton.clicked.connect(self.doorLock)

        # MenuScreen
        self.menuBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
        self.menuControlButton.pressed.connect(self.control)
        self.menuPrintButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.menuCalibrateButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
        self.menuSettingsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # Calibrate Page
        self.calibrateBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.nozzleOffsetButton.pressed.connect(self.requestEEPROMProbeOffset)
        self.nozzleOffsetSetButton.pressed.connect(
            lambda: self.setZProbeOffset(self.nozzleOffsetDoubleSpinBox.value()))
        self.nozzleOffsetBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))

        self.moveZMT1CaliberateButton.pressed.connect(lambda: octopiclient.jog(z=-0.025)) # --Dual Caliberation Addition--
        self.moveZPT1CaliberateButton.pressed.connect(lambda: octopiclient.jog(z=0.025))

        self.calibrationWizardButton.clicked.connect(self.quickStep1)
        self.quickStep1NextButton.clicked.connect(self.quickStep2)
        self.quickStep2NextButton.clicked.connect(self.quickStep3)
        self.quickStep3NextButton.clicked.connect(self.quickStep4)
        self.quickStep4NextButton.clicked.connect(self.nozzleHeightStep1)
        self.nozzleHeightStep1NextButton.clicked.connect(self.nozzleHeightStep1)
        self.quickStep1CancelButton.pressed.connect(self.cancelStep)
        self.quickStep2CancelButton.pressed.connect(self.cancelStep)
        self.quickStep3CancelButton.pressed.connect(self.cancelStep)
        self.quickStep4CancelButton.pressed.connect(self.cancelStep)
        self.nozzleHeightStep1CancelButton.pressed.connect(self.cancelStep)
        
        self.toolOffsetXSetButton.pressed.connect(self.setToolOffsetX)
        self.toolOffsetYSetButton.pressed.connect(self.setToolOffsetY)
        self.toolOffsetZSetButton.pressed.connect(self.setToolOffsetZ)
        self.toolOffsetXYBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
        self.toolOffsetZBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
        self.toolOffsetXYButton.pressed.connect(self.toolOffsetXY)
        self.toolOffsetZButton.pressed.connect(self.toolOffsetZ)

        self.testPrintsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.testPrintsPage1))
        self.testPrintsNextButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.testPrintsPage2))
        self.testPrintsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
        self.testPrintsCancelButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
        self.dualCaliberationPrintButton.pressed.connect(
            lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                   str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'dualCalibration'))
        self.bedLevelPrintButton.pressed.connect(
            lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                   str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'bedLevel'))
        self.movementTestPrintButton.pressed.connect(
            lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                   str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'movementTest'))
        self.singleNozzlePrintButton.pressed.connect(
            lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                   str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'dualTest'))
        self.dualNozzlePrintButton.pressed.connect(
            lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                   str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'singleTest'))

        # PrintLocationScreen
        self.printLocationScreenBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.fromLocalButton.pressed.connect(self.fileListLocal)
        self.fromUsbButton.pressed.connect(self.fileListUSB)

        # fileListLocalScreen
        self.localStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.localStorageScrollUp.pressed.connect(
            lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() - 1))
        self.localStorageScrollDown.pressed.connect(
            lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() + 1))
        self.localStorageSelectButton.pressed.connect(self.printSelectedLocal)
        self.localStorageDeleteButton.pressed.connect(self.deleteItem)

        # selectedFile Local Screen
        self.fileSelectedBackButton.pressed.connect(self.fileListLocal)
        self.fileSelectedPrintButton.pressed.connect(self.printFile)

        # filelistUSBPage
        self.USBStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
        self.USBStorageScrollUp.pressed.connect(
            lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() - 1))
        self.USBStorageScrollDown.pressed.connect(
            lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() + 1))
        self.USBStorageSelectButton.pressed.connect(self.printSelectedUSB)
        self.USBStorageSaveButton.pressed.connect(lambda: self.transferToLocal(prnt=False))

        # selectedFile USB Screen
        self.fileSelectedUSBBackButton.pressed.connect(self.fileListUSB)
        self.fileSelectedUSBTransferButton.pressed.connect(lambda: self.transferToLocal(prnt=False))
        self.fileSelectedUSBPrintButton.pressed.connect(lambda: self.transferToLocal(prnt=True))

        # ControlScreen
        self.moveYPButton.pressed.connect(lambda: octopiclient.jog(y=self.step, speed=1000))
        self.moveYMButton.pressed.connect(lambda: octopiclient.jog(y=-self.step, speed=1000))
        self.moveXMButton.pressed.connect(lambda: octopiclient.jog(x=-self.step, speed=1000))
        self.moveXPButton.pressed.connect(lambda: octopiclient.jog(x=self.step, speed=1000))
        self.moveZPButton.pressed.connect(lambda: octopiclient.jog(z=self.step, speed=1000))
        self.moveZMButton.pressed.connect(lambda: octopiclient.jog(z=-self.step, speed=1000))
        self.extruderButton.pressed.connect(lambda: octopiclient.extrude(self.step))
        self.retractButton.pressed.connect(lambda: octopiclient.extrude(-self.step))
        self.motorOffButton.pressed.connect(lambda: octopiclient.gcode(command='M18'))
        self.fanOnButton.pressed.connect(lambda: octopiclient.gcode(command='M106'))
        self.fanOffButton.pressed.connect(lambda: octopiclient.gcode(command='M107'))
        self.cooldownButton.pressed.connect(self.coolDownAction)
        self.step100Button.pressed.connect(lambda: self.setStep(100))
        self.step1Button.pressed.connect(lambda: self.setStep(1))
        self.step10Button.pressed.connect(lambda: self.setStep(10))
        self.homeXYButton.pressed.connect(lambda: octopiclient.home(['x', 'y']))
        self.homeZButton.pressed.connect(lambda: octopiclient.home(['z']))
        self.toolToggleTemperatureButton.clicked.connect(self.selectToolTemperature)
        self.toolToggleMotionButton.clicked.connect(self.selectToolMotion)
        self.controlBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
        self.setToolTempButton.pressed.connect(self.setToolTemp)
        self.tool180PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T1 S180') if self.toolToggleTemperatureButton.isChecked() else octopiclient.gcode(command='M104 T0 S180'))
        #self.tool220PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T1 S220') if self.toolToggleTemperatureButton.isChecked() else octopiclient.gcode(command='M104 T0 S220'))
        self.tool250PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T1 S250') if self.toolToggleTemperatureButton.isChecked() else octopiclient.gcode(command='M104 T0 S250'))
        self.setBedTempButton.pressed.connect(lambda: octopiclient.setBedTemperature(self.bedTempSpinBox.value()))
        self.bed60PreheatButton.pressed.connect(lambda: octopiclient.setBedTemperature(target=60))
        self.bed100PreheatButton.pressed.connect(lambda: octopiclient.setBedTemperature(target=100))
        self.setChamberTempButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T2 S' + str(self.chamberTempSpinBox.value())))
        self.chamber40PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T2 S40'))
        self.chamber70PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M041 T2 S70'))
        self.setFilboxTempButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T3 S' + str(self.filboxTempSpinBox.value())))
        self.filbox30PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T3 S30'))
        self.filbox40PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T3 S40'))
        self.setFlowRateButton.pressed.connect(lambda: octopiclient.flowrate(self.flowRateSpinBox.value()))
        self.setFeedRateButton.pressed.connect(lambda: octopiclient.feedrate(self.feedRateSpinBox.value()))

        self.moveZPBabyStep.pressed.connect(lambda: octopiclient.gcode(command='M290 Z0.025'))
        self.moveZMBabyStep.pressed.connect(lambda: octopiclient.gcode(command='M290 Z-0.025'))

        # ChangeFilament rutien
        self.changeFilamentButton.pressed.connect(self.changeFilament)
        self.toolToggleChangeFilamentButton.clicked.connect(self.selectToolChangeFilament)
        self.changeFilamentBackButton.pressed.connect(self.control)
        self.changeFilamentBackButton2.pressed.connect(self.changeFilamentCancel)
        self.changeFilamentUnloadButton.pressed.connect(lambda: self.unloadFilament())
        self.changeFilamentLoadButton.pressed.connect(lambda: self.loadFilament())
        self.loadDoneButton.pressed.connect(self.control)
        self.unloadDoneButton.pressed.connect(self.changeFilament)
        self.retractFilamentButton.pressed.connect(lambda: octopiclient.extrude(-20))
        self.ExtrudeButton.pressed.connect(lambda: octopiclient.extrude(20))

        # Settings Page
        self.settingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
        self.networkSettingsButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
        self.displaySettingsButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))
        self.pairPhoneButton.pressed.connect(self.pairPhoneApp)
        self.OTAButton.pressed.connect(self.softwareUpdate)
        self.versionButton.pressed.connect(self.displayVersionInfo)
        self.restartButton.pressed.connect(self.askAndReboot)
        self.restoreFactoryDefaultsButton.pressed.connect(self.restoreFactoryDefaults)
        self.restorePrintSettingsButton.pressed.connect(self.restorePrintDefaults)

        # Network settings page
        self.networkInfoButton.pressed.connect(self.networkInfo)
        self.configureWifiButton.pressed.connect(self.wifiSettings)
        self.configureEthButton.pressed.connect(self.ethSettings)
        self.networkSettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # Network Info Page
        self.networkInfoBackButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))

        # WifiSetings page
        self.wifiSettingsSSIDKeyboardButton.pressed.connect(
            lambda: self.startKeyboard(self.wifiSettingsComboBox.addItem))
        self.wifiSettingsCancelButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
        self.wifiSettingsDoneButton.pressed.connect(self.acceptWifiSettings)

        # Ethernet setings page
        self.ethStaticCheckBox.stateChanged.connect(self.ethStaticChanged)
        # self.ethStaticCheckBox.stateChanged.connect(lambda: self.ethStaticSettings.setVisible(self.ethStaticCheckBox.isChecked()))
        self.ethStaticIpKeyboardButton.pressed.connect(lambda: self.ethShowKeyboard(self.ethStaticIpLineEdit))
        self.ethStaticGatewayKeyboardButton.pressed.connect(lambda: self.ethShowKeyboard(self.ethStaticGatewayLineEdit))
        self.ethSettingsDoneButton.pressed.connect(self.ethSaveStaticNetworkInfo)
        self.ethSettingsCancelButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))

        # Display settings
        self.rotateDisplay.pressed.connect(self.showRotateDisplaySettingsPage)
        self.calibrateTouch.pressed.connect(self.touchCalibration)
        self.displaySettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # Rotate Display Settings
        self.rotateDisplaySettingsDoneButton.pressed.connect(self.saveRotateDisplaySettings)
        self.rotateDisplaySettingsCancelButton.pressed.connect(
            lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))

        # QR Code
        self.QRCodeBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

        # SoftwareUpdatePage
        self.softwareUpdateBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
        self.performUpdateButton.pressed.connect(lambda: octopiclient.performSoftwareUpdate())

        # Firmware update page
        self.firmwareUpdateBackButton.pressed.connect(self.firmwareUpdateBack)

        # Filament sensor toggle
        self.toggleFilamentSensorButton.clicked.connect(self.toggleFilamentSensor)

    ''' +++++++++++++++++++++++++Print Restore+++++++++++++++++++++++++++++++++++ '''

    def printRestoreMessageBox(self, file):
        '''
        Displays a message box alerting the user of a filament error
        '''
        if dialog.WarningYesNo(self, file + " Did not finish, would you like to restore?"):
            response = octopiclient.restore(restore=True)
            if response["status"] == "Successfully Restored":
                dialog.WarningOk(response["status"])
            else:
                dialog.WarningOk(response["status"])
        else:
            octoprintAPI.restore(restore=False)

    def onServerConnected(self):
        self.isFilamentSensorInstalled()
        # if not self.__timelapse_enabled:
        #     return
        # if self.__timelapse_started:
        #     return
        try:
            response = octopiclient.isFailureDetected()
            if response["canRestore"] is True:
                self.printRestoreMessageBox(response["file"])
            else:
                self.firmwareUpdateCheck()
        except:
            print "error on Server Connected"
            pass

    ''' +++++++++++++++++++++++++Filament Sensor++++++++++++++++++++++++++++++++++++++ '''


    def isFilamentSensorInstalled(self):
        success = False
        try:
            headers = {'X-Api-Key': apiKey}
            req = requests.get('http://{}/plugin/Julia2018FilamentSensor/status'.format(ip), headers=headers)
            success = req.status_code == requests.codes.ok
        except:
            pass
        self.toggleFilamentSensorButton.setEnabled(success)
        return success

    def toggleFilamentSensor(self):
        headers = {'X-Api-Key': apiKey}
        # payload = {'sensor_enabled': self.toggleFilamentSensorButton.isChecked()}
        requests.get('http://{}/plugin/Julia2018FilamentSensor/toggle'.format(ip), headers=headers)   # , data=payload)

    def filamentSensorHandler(self, data):
        sensor_enabled = False
        # print(data)

        if 'sensor_enabled' in data:
            sensor_enabled = data["sensor_enabled"] == 1

        icon = 'filamentSensorOn' if sensor_enabled else 'filamentSensorOff'
        self.toggleFilamentSensorButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/" + icon)))

        if not sensor_enabled:
            return

        triggered_extruder0 = False
        triggered_extruder1 = False
        triggered_door = False
        pause_print = False

        if 'filament' in data:
            triggered_extruder0 = data["filament"] == 0
        elif 'extruder0' in data:
            triggered_extruder0 = data["extruder0"] == 0

        if 'filament2' in data:
            triggered_extruder1 = data["filament2"] == 0
        elif 'extruder0' in data:
            triggered_extruder1 = data["extruder1"] == 0

        if 'door' in data:
            triggered_door = data["door"] == 0
        if 'pause_print' in data:
            pause_print = data["pause_print"]

        if triggered_extruder0 and self.stackedWidget.currentWidget() not in [self.changeFilamentPage, self.changeFilamentProgressPage,
                                  self.changeFilamentExtrudePage, self.changeFilamentRetractPage]:
            if dialog.WarningOk(self, "Filament outage in Extruder 0"):
                pass

        if triggered_extruder1 and self.stackedWidget.currentWidget() not in [self.changeFilamentPage, self.changeFilamentProgressPage,
                                  self.changeFilamentExtrudePage, self.changeFilamentRetractPage]:
            if dialog.WarningOk(self, "Filament outage in Extruder 1"):
                pass

        if triggered_door:
            if self.printerStatusText == "Printing":
                no_pause_pages = [self.controlPage, self.changeFilamentPage, self.changeFilamentProgressPage,
                                  self.changeFilamentExtrudePage, self.changeFilamentRetractPage]
                if not pause_print or self.stackedWidget.currentWidget() in no_pause_pages:
                    if dialog.WarningOk(self, "Door opened"):
                        return
                octopiclient.pausePrint()
                if dialog.WarningOk(self, "Door opened. Print paused.", overlay=True):
                    return
            else:
                if dialog.WarningOk(self, "Door opened"):
                    return

    ''' +++++++++++++++++++++++++++ Volterra VAS +++++++++++++++++++++++++++++++++++++ '''

    def doorLock(self):
        '''
        function that toggles locking and unlocking the front door
        :return:
        '''
        octopiclient.overrideDoorLock()

    def doorLockMsg(self, data):
        if "msg" not in data:
            return

        msg = data["msg"]

        if self.dialog_doorlock:
            self.dialog_doorlock.close()
            self.dialog_doorlock = None

        if msg is not None:
            self.dialog_doorlock = dialog.dialog(self, msg, icon="exclamation-mark.png")
            if self.dialog_doorlock.exec_() == QtGui.QMessageBox.Ok:
                self.dialog_doorlock = None
                return

    def doorLockHandler(self, data):
        door_lock_disabled = False
        door_lock = False
        # door_sensor = False
        # door_lock_override = False

        if 'door_lock' in data:
            door_lock_disabled = data["door_lock"] == "disabled"
            door_lock = data["door_lock"] == 1
        # if 'door_sensor' in data:
        #     door_sensor = data["door_sensor"] == 1
        # if 'door_lock_override' in data:
        #     door_lock_override = data["door_lock_override"] == 1

        # if self.dialog_doorlock:
        #     self.dialog_doorlock.close()
        #     self.dialog_doorlock = None

        self.doorLockButton.setVisible(not door_lock_disabled)
        if not door_lock_disabled:
            # self.doorLockButton.setChecked(not door_lock)
            self.doorLockButton.setText('Lock Door' if not door_lock else 'Unlock Door')

            icon = 'doorLock' if not door_lock else 'doorUnlock'
            self.doorLockButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/" + icon + ".png")))
        else:
            return

    ''' +++++++++++++++++++++++++++ Firmware Update+++++++++++++++++++++++++++++++++++ '''

    isFirmwareUpdateInProgress = False

    def firmwareUpdateCheck(self):
        headers = {'X-Api-Key': apiKey}
        requests.get('http://{}/plugin/JuliaFirmwareUpdater/update/check'.format(ip), headers=headers)

    def firmwareUpdateStart(self):
        headers = {'X-Api-Key': apiKey}
        requests.get('http://{}/plugin/JuliaFirmwareUpdater/update/start'.format(ip), headers=headers)

    def firmwareUpdateStartProgress(self):
        self.stackedWidget.setCurrentWidget(self.firmwareUpdateProgressPage)
        # self.firmwareUpdateLog.setTextColor(QtCore.Qt.yellow)
        self.firmwareUpdateLog.setText("<span style='color: cyan'>Julia Firmware Updater<span>")
        self.firmwareUpdateLog.append("<span style='color: cyan'>---------------------------------------------------------------</span>")
        self.firmwareUpdateBackButton.setEnabled(False)

    def firmwareUpdateProgress(self, text, backEnabled=False):
        self.stackedWidget.setCurrentWidget(self.firmwareUpdateProgressPage)
        # self.firmwareUpdateLog.setTextColor(QtCore.Qt.yellow)
        self.firmwareUpdateLog.append(str(text))
        self.firmwareUpdateBackButton.setEnabled(backEnabled)

    def firmwareUpdateBack(self):
        self.isFirmwareUpdateInProgress = False
        self.firmwareUpdateBackButton.setEnabled(False)
        self.stackedWidget.setCurrentWidget(self.homePage)

    def firmwareUpdateHandler(self, data):
        if "type" not in data or data["type"] != "status":
            return

        if "status" not in data:
            return

        status = data["status"]
        subtype = data["subtype"] if "subtype" in data else None

        if status == "update_check":    # update check
            if subtype == "error":  # notify error in ok diag
                self.isFirmwareUpdateInProgress = False
                if "message" in data:
                    dialog.WarningOk(self, "Firmware Updater Error: " + str(data["message"]), overlay=True)
            elif subtype == "success":
                if dialog.SuccessYesNo(self, "Firmware update found.\nPress yes to update now!", overlay=True):
                    self.isFirmwareUpdateInProgress = True
                    self.firmwareUpdateStart()
        elif status == "update_start":  # update started
            if subtype == "success":    # update progress
                self.isFirmwareUpdateInProgress = True
                self.firmwareUpdateStartProgress()
                if "message" in data:
                    message = "<span style='color: yellow'>{}</span>".format(data["message"])
                    self.firmwareUpdateProgress(message)
            else:   # show error
                self.isFirmwareUpdateInProgress = False
                # self.firmwareUpdateProgress(data["message"] if "message" in data else "Unknown error!", backEnabled=True)
                if "message" in data:
                    dialog.WarningOk(self, "Firmware Updater Error: " + str(data["message"]), overlay=True)
        elif status == "flasherror" or status == "progress":    # show software update dialog and update textview
            if "message" in data:
                message = "<span style='color: {}'>{}</span>".format("teal" if status == "progress" else "red", data["message"])
                self.firmwareUpdateProgress(message, backEnabled=(status == "flasherror"))
        elif status == "success":    # show ok diag to show done
            self.isFirmwareUpdateInProgress = False
            message = data["message"] if "message" in data else "Flash successful!"
            message = "<span style='color: green'>{}</span>".format(message)
            message = message + "<br/><br/><span style='color: white'>Press back to continue...</span>"
            self.firmwareUpdateProgress(message, backEnabled=True)

    ''' +++++++++++++++++++++++++++++++++OTA Update+++++++++++++++++++++++++++++++++++ '''

    def getFirmwareVersion(self):
        try:
            headers = {'X-Api-Key': apiKey}
            req = requests.get('http://{}/plugin/JuliaFirmwareUpdater/hardware/version'.format(ip), headers=headers)
            data = req.json()
            # print(data)
            if req.status_code == requests.codes.ok:
                info = u'\u2713' if not data["update_available"] else u"\u2717"    # icon
                info += " Firmware: "
                info += "Unknown" if not data["variant_name"] else data["variant_name"]
                info += "\n"
                if data["variant_name"]:
                    info += "   Installed: "
                    info += "Unknown" if not data["version_board"] else data["version_board"]
                info += "\n"
                info += "" if not data["version_repo"] else "   Available: " + data["version_repo"]
                return info
        except:
            print("Error accessing /plugin/JuliaFirmwareUpdater/hardware/version")
            pass
        return u'\u2713' + "Firmware: Unknown\n"

    def displayVersionInfo(self):
        self.updateListWidget.clear()
        updateAvailable = False
        self.performUpdateButton.setDisabled(True)

        self.updateListWidget.addItem(self.getFirmwareVersion())

        data = octopiclient.getSoftwareUpdateInfo()
        if data:
            for item in data["information"]:
                # print(item)
                plugin = data["information"][item]
                info = u'\u2713' if not plugin["updateAvailable"] else u"\u2717"    # icon
                info += plugin["displayName"] + "  " + plugin["displayVersion"] + "\n"
                info += "   Available: "
                if "information" in plugin and "remote" in plugin["information"] and plugin["information"]["remote"]["value"] is not None:
                    info += plugin["information"]["remote"]["value"]
                else:
                    info += "Unknown"
                self.updateListWidget.addItem(info)

                if plugin["updateAvailable"]:
                    updateAvailable = True

                # if not updatable:
                #     self.updateListWidget.addItem(u'\u2713' + data["information"][item]["displayName"] +
                #                                   "  " + data["information"][item]["displayVersion"] + "\n"
                #                                   + "   Available: " +
                #                                   )
                # else:
                #     updateAvailable = True
                #     self.updateListWidget.addItem(u"\u2717" + data["information"][item]["displayName"] +
                #                                   "  " + data["information"][item]["displayVersion"] + "\n"
                #                                   + "   Available: " +
                #                                   data["information"][item]["information"]["remote"]["value"])
        if updateAvailable:
            self.performUpdateButton.setDisabled(False)
        self.stackedWidget.setCurrentWidget(self.OTAUpdatePage)

    def softwareUpdateResult(self, data):
        messageText = ""
        for item in data:
            messageText += item + ": " + data[item][0] + ".\n"
        messageText += "Restart required"
        self.askAndReboot(messageText)

    def softwareUpdateProgress(self, data):
        self.stackedWidget.setCurrentWidget(self.softwareUpdateProgressPage)
        self.logTextEdit.setTextColor(QtCore.Qt.red)
        self.logTextEdit.append("---------------------------------------------------------------\n"
                                "Updating " + data["name"] + " to " + data["version"] + "\n"
                                                                                        "---------------------------------------------------------------")

    def softwareUpdateProgressLog(self, data):
        self.logTextEdit.setTextColor(QtCore.Qt.white)
        for line in data:
            self.logTextEdit.append(line["line"])

    def updateFailed(self, data):
        self.stackedWidget.setCurrentWidget(self.settingsPage)
        messageText = (data["name"] + " failed to update\n")
        if dialog.WarningOkCancel(self, messageText, overlay=True):
            pass

    def softwareUpdate(self):
        data = octopiclient.getSoftwareUpdateInfo()
        updateAvailable = False
        if data:
            for item in data["information"]:
                if data["information"][item]["updateAvailable"]:
                    updateAvailable = True
        if updateAvailable:
            print('Update Available')
            if dialog.SuccessYesNo(self, "Update Available! Update Now?", overlay=True):
                octopiclient.performSoftwareUpdate()

        else:
            if dialog.SuccessOk(self, "System is Up To Date!", overlay=True):
                print('Update Unavailable')

    ''' +++++++++++++++++++++++++++++++++Wifi Config+++++++++++++++++++++++++++++++++++ '''

    def acceptWifiSettings(self):
        wlan0_config_file = io.open("/etc/wpa_supplicant/wpa_supplicant.conf", "r+", encoding='utf8')
        wlan0_config_file.truncate()
        ascii_ssid = self.wifiSettingsComboBox.currentText()
        # unicode_ssid = ascii_ssid.decode('string_escape').decode('utf-8')
        wlan0_config_file.write(u"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
        wlan0_config_file.write(u"update_config=1\n")
        wlan0_config_file.write(u"country=IN\n")
        wlan0_config_file.write(u"network={\n")
        wlan0_config_file.write(u'ssid="' + str(ascii_ssid) + '"\n')
        if self.hiddenCheckBox.isChecked():
            wlan0_config_file.write(u'scan_ssid=1\n')
        if str(self.wifiPasswordLineEdit.text()) != "":
            wlan0_config_file.write(u'psk="' + str(self.wifiPasswordLineEdit.text()) + '"\n')
        wlan0_config_file.write(u'}')
        wlan0_config_file.close()
        signal = 'WIFI_RECONNECT_RESULT'
        self.restartWifiThreadObject = ThreadRestartNetworking(ThreadRestartNetworking.WLAN, signal)
        self.restartWifiThreadObject.start()
        self.connect(self.restartWifiThreadObject, QtCore.SIGNAL(signal), self.wifiReconnectResult)
        self.wifiMessageBox = dialog.dialog(self,
                                            "Restarting networking, please wait...",
                                            icon="exclamation-mark.png",
                                            buttons=QtGui.QMessageBox.Cancel)
        if self.wifiMessageBox.exec_() in {QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel}:
            self.stackedWidget.setCurrentWidget(self.networkSettingsPage)

    def wifiReconnectResult(self, x):
        self.wifiMessageBox.setStandardButtons(QtGui.QMessageBox.Ok)
        if x is not None:
            self.wifiMessageBox.setLocalIcon('success.png')
            self.wifiMessageBox.setText('Connected, IP: ' + x)
            self.wifiMessageBox.setStandardButtons(QtGui.QMessageBox.Ok)
            self.ipStatus.setText(x) #sets the IP addr. in the status bar

        else:
            self.wifiMessageBox.setText("Not able to connect to WiFi")

    def networkInfo(self):
        ipWifi = getIP(ThreadRestartNetworking.WLAN)
        ipEth = getIP(ThreadRestartNetworking.ETH)

        self.hostname.setText(getHostname())
        self.wifiAp.setText(getWifiAp())
        self.wifiIp.setText("Not connected" if not ipWifi else ipWifi)
        self.ipStatus.setText("Not connected" if not ipWifi else ipWifi)
        self.lanIp.setText("Not connected" if not ipEth else ipEth)
        self.wifiMac.setText(getMac(ThreadRestartNetworking.WLAN))
        self.lanMac.setText(getMac(ThreadRestartNetworking.ETH))
        self.stackedWidget.setCurrentWidget(self.networkInfoPage)

    def wifiSettings(self):
        self.stackedWidget.setCurrentWidget(self.wifiSettingsPage)
        self.wifiSettingsComboBox.clear()
        self.wifiSettingsComboBox.addItems(self.scan_wifi())

    def scan_wifi(self):
        '''
        uses linux shell and WIFI interface to scan available networks
        :return: dictionary of the SSID and the signal strength
        '''
        # scanData = {}
        # print "Scanning available wireless signals available to wlan0"
        scan_result = \
            subprocess.Popen("iwlist wlan0 scan | grep 'ESSID'", stdout=subprocess.PIPE, shell=True).communicate()[0]
        # Processing STDOUT into a dictionary that later will be converted to a json file later
        scan_result = scan_result.split('ESSID:')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
        scan_result = [s.strip() for s in scan_result]
        scan_result = [s.strip('"') for s in scan_result]
        scan_result = filter(None, scan_result)
        return scan_result

    @run_async
    def setIPStatus(self):
        '''
        Function to update IP address of printer on the status bar. Refreshes at a particular interval.
        '''
        while(True):
            try:
                if getIP("eth0"):
                    self.ipStatus.setText(getIP("eth0"))
                elif getIP("wlan0"):
                    self.ipStatus.setText(getIP("wlan0"))
                else:
                    self.ipStatus.setText("Not connected")

            except:
                self.ipStatus.setText("Not connected")
            time.sleep(60)


    ''' +++++++++++++++++++++++++++++++++Ethernet Settings+++++++++++++++++++++++++++++ '''

    def ethSettings(self):
        self.stackedWidget.setCurrentWidget(self.ethSettingsPage)
        # self.ethStaticCheckBox.setChecked(True)
        self.ethNetworkInfo()

    def ethStaticChanged(self, state):
        self.ethStaticSettings.setVisible(self.ethStaticCheckBox.isChecked())
        self.ethStaticSettings.setEnabled(self.ethStaticCheckBox.isChecked())
        # if state == QtCore.Qt.Checked:
        #     self.ethStaticSettings.setVisible(True)
        # else:
        #     self.ethStaticSettings.setVisible(False)

    def ethNetworkInfo(self):
        txt = subprocess.Popen("cat /etc/dhcpcd.conf", stdout=subprocess.PIPE, shell=True).communicate()[0]

        reEthGlobal = r"interface\s+eth0\s?(static\s+[a-z0-9./_=\s]+\n)*"
        reEthAddress = r"static\s+ip_address=([\d.]+)(/[\d]{1,2})?"
        reEthGateway = r"static\s+routers=([\d.]+)(/[\d]{1,2})?"

        mtEthGlobal = re.search(reEthGlobal, txt)

        cbStaticEnabled = False
        txtEthAddress = ""
        txtEthGateway = ""

        if mtEthGlobal:
            sz = len(mtEthGlobal.groups())
            cbStaticEnabled = (sz == 1)

            if sz == 1:
                mtEthAddress = re.search(reEthAddress, mtEthGlobal.group(0))
                if mtEthAddress and len(mtEthAddress.groups()) == 2:
                    txtEthAddress = mtEthAddress.group(1)
                mtEthGateway = re.search(reEthGateway, mtEthGlobal.group(0))
                if mtEthGateway and len(mtEthGateway.groups()) == 2:
                    txtEthGateway = mtEthGateway.group(1)

        self.ethStaticCheckBox.setChecked(cbStaticEnabled)
        self.ethStaticSettings.setVisible(cbStaticEnabled)
        self.ethStaticIpLineEdit.setText(txtEthAddress)
        self.ethStaticGatewayLineEdit.setText(txtEthGateway)

    def isIpErr(self, ip):
        return (re.search(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$", ip) is None)

    def showIpErr(self, var):
        return dialog.WarningOk(self, "Invalid input: {0}".format(var))

    def ethSaveStaticNetworkInfo(self):
        cbStaticEnabled = self.ethStaticCheckBox.isChecked()
        txtEthAddress = str(self.ethStaticIpLineEdit.text())
        txtEthGateway = str(self.ethStaticGatewayLineEdit.text())

        if cbStaticEnabled:
            if self.isIpErr(txtEthAddress):
                return self.showIpErr("IP Address")
            if self.isIpErr(txtEthGateway):
                return self.showIpErr("Gateway")

        txt = subprocess.Popen("cat /etc/dhcpcd.conf", stdout=subprocess.PIPE, shell=True).communicate()[0]
        op = ""

        reEthGlobal = r"interface\s+eth0"
        mtEthGlobal = re.search(reEthGlobal, txt)

        if cbStaticEnabled:
            if not mtEthGlobal:
                txt = txt + "\n" + "interface eth0" + "\n"
            op = "interface eth0\nstatic ip_address={0}/24\nstatic routers={1}\nstatic domain_name_servers=8.8.8.8 8.8.4.4\n\n".format(
                txtEthAddress, txtEthGateway)

        res = re.sub(r"interface\s+eth0\s?(static\s+[a-z0-9./_=\s]+\n)*", op, txt)
        try:
            file = open("/etc/dhcpcd.conf", "w")
            file.write(res)
            file.close()
        except:
            if dialog.WarningOk(self, "Failed to change Ethernet Interface configuration."):
                pass

        signal = 'ETH_RECONNECT_RESULT'
        self.restartEthThreadObject = ThreadRestartNetworking(ThreadRestartNetworking.ETH, signal)
        self.restartEthThreadObject.start()
        self.connect(self.restartEthThreadObject, QtCore.SIGNAL(signal), self.ethReconnectResult)
        self.ethMessageBox = dialog.dialog(self,
                                           "Restarting networking, please wait...",
                                           icon="exclamation-mark.png",
                                           buttons=QtGui.QMessageBox.Cancel)
        if self.ethMessageBox.exec_() in {QtGui.QMessageBox.Ok, QtGui.QMessageBox.Cancel}:
            self.stackedWidget.setCurrentWidget(self.networkSettingsPage)

    def ethReconnectResult(self, x):
        self.ethMessageBox.setStandardButtons(QtGui.QMessageBox.Ok)
        if x is not None:
            self.ethMessageBox.setLocalIcon('success.png')
            self.ethMessageBox.setText('Connected, IP: ' + x)
        else:

            self.ethMessageBox.setText("Not able to connect to Ethernet")

    def ethShowKeyboard(self, textbox):
        self.startKeyboard(textbox.setText, onlyNumeric=True, noSpace=True, text=str(textbox.text()))

    ''' ++++++++++++++++++++++++++++++++Display Settings+++++++++++++++++++++++++++++++ '''

    def touchCalibration(self):
        os.system('sudo /home/pi/setenv.sh')

    def showRotateDisplaySettingsPage(self):
        txt = subprocess.Popen("cat /boot/config.txt", stdout=subprocess.PIPE, shell=True).communicate()[0]

        reRot = r"dtoverlay\s*=\s*waveshare35a(\s*:\s*rotate\s*=\s*([0-9]{1,3})){0,1}"
        mtRot = re.search(reRot, txt)
        # print(mtRot.group(0))

        if mtRot and len(mtRot.groups()) == 2 and str(mtRot.group(2)) == "270":
            self.rotateDisplaySettingsComboBox.setCurrentIndex(1)
        else:
            self.rotateDisplaySettingsComboBox.setCurrentIndex(0)

        self.stackedWidget.setCurrentWidget(self.rotateDisplaySettingsPage)

    def saveRotateDisplaySettings(self):
        txt1 = subprocess.Popen("cat /boot/config.txt", stdout=subprocess.PIPE, shell=True).communicate()[0]

        reRot = r"dtoverlay\s*=\s*waveshare35a(\s*:\s*rotate\s*=\s*([0-9]{1,3})){0,1}"
        if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
            op1 = "dtoverlay=waveshare35a:rotate=270"
        else:
            op1 = "dtoverlay=waveshare35a"
        res1 = re.sub(reRot, op1, txt1)

        try:
            file1 = open("/boot/config.txt", "w")
            file1.write(res1)
            file1.close()
        except:
            if dialog.WarningOk(self, "Failed to change rotation settings", overlay=True):
                return

        txt2 = subprocess.Popen("cat /etc/X11/xorg.conf.d/99-calibration.conf", stdout=subprocess.PIPE,
                                shell=True).communicate()[0]

        reTouch = r"Option\s+\"TransformationMatrix\"\s+\"([\d\s-]+)\""
        if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
            op2 = "Option \"TransformationMatrix\"  \"0 1 0 -1 0 1 0 0 1\""
        else:
            op2 = "Option \"TransformationMatrix\"  \"0 -1 1 1 0 0 0 0 1\""
        res2 = re.sub(reTouch, op2, txt2, flags=re.I)

        try:
            file2 = open("/etc/X11/xorg.conf.d/99-calibration.conf", "w")
            file2.write(res2)
            file2.close()
        except:
            if dialog.WarningOk(self, "Failed to change touch settings", overlay=True):
                return

        self.askAndReboot()
        self.stackedWidget.setCurrentWidget(self.displaySettingsPage)

    ''' +++++++++++++++++++++++++++++++++Change Filament+++++++++++++++++++++++++++++++ '''

    def unloadFilament(self):
        if self.changeFilamentComboBox.findText("Loaded Filament") == -1:
            octopiclient.setToolTemperature({"tool1": filaments[str(
                self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
                {"tool0": filaments[str(self.changeFilamentComboBox.currentText())]})
        self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
        self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
        self.changeFilamentNameOperation.setText("Unloading {}".format(str(self.changeFilamentComboBox.currentText())))
        # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
        self.changeFilamentHeatingFlag = True
        self.loadFlag = False

    def loadFilament(self):
        if self.changeFilamentComboBox.findText("Loaded Filament") == -1:
            octopiclient.setToolTemperature({"tool1": filaments[str(
                self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
                {"tool0": filaments[str(self.changeFilamentComboBox.currentText())]})
        self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
        self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
        self.changeFilamentNameOperation.setText("Loading {}".format(str(self.changeFilamentComboBox.currentText())))
        # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
        self.changeFilamentHeatingFlag = True
        self.loadFlag = True

    def changeFilament(self):
        self.stackedWidget.setCurrentWidget(self.changeFilamentPage)
        self.changeFilamentComboBox.clear()
        self.changeFilamentComboBox.addItems(filaments.keys())
        if self.tool0TargetTemperature > 0 and self.printerStatusText in ["Printing","Paused"]:
            self.changeFilamentComboBox.addItem("Loaded Filament")
            index = self.changeFilamentComboBox.findText("Loaded Filament")
            if index >= 0 :
                self.changeFilamentComboBox.setCurrentIndex(index)

    def changeFilamentCancel(self):
        self.changeFilamentHeatingFlag = False
        self.firmwareUpdateCheck()
        self.coolDownAction()
        self.control()

    ''' +++++++++++++++++++++++++++++++++Job Operations+++++++++++++++++++++++++++++++ '''

    def stopActionMessageBox(self):
        '''
        Displays a message box asking if the user is sure if he wants to turn off the print
        '''
        if dialog.WarningYesNo(self, "Are you sure you want to stop the print?"):
            octopiclient.cancelPrint()

    def playPauseAction(self):
        '''
        Toggles Play/Pause of a print depending on the status of the print
        '''
        if self.printerStatusText == "Operational":
            if self.playPauseButton.isChecked:
                octopiclient.startPrint()
        elif self.printerStatusText == "Printing":
            octopiclient.pausePrint()
        elif self.printerStatusText == "Paused":
            octopiclient.resumePrint()

    def fileListLocal(self):
        '''
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page
        '''
        self.stackedWidget.setCurrentWidget(self.fileListLocalPage)
        files = []
        for file in octopiclient.retrieveFileInformation()['files']:
            if file["type"] == "machinecode":
                files.append(file)

        self.fileListWidget.clear()
        files.sort(key=lambda d: d['date'], reverse=True)
        # for item in [f['name'] for f in files] :
        #     self.fileListWidget.addItem(item)
        self.fileListWidget.addItems([f['name'] for f in files])
        self.fileListWidget.setCurrentRow(0)

    def fileListUSB(self):
        '''
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page
        ToDO: Add deapth of folders recursively get all gcodes
        '''
        self.stackedWidget.setCurrentWidget(self.fileListUSBPage)
        self.fileListWidgetUSB.clear()
        files = subprocess.Popen("ls /media/usb0 | grep gcode", stdout=subprocess.PIPE, shell=True).communicate()[0]
        files = files.split('\n')
        files = filter(None, files)
        # for item in files:
        #     self.fileListWidgetUSB.addItem(item)
        self.fileListWidgetUSB.addItems(files)
        self.fileListWidgetUSB.setCurrentRow(0)

    def printSelectedLocal(self):

        '''
        gets information about the selected file from octoprint server,
        as well as sets the current page to the print selected page.
        This function also selects the file to print from octoprint
        '''
        try:
            self.fileSelected.setText(self.fileListWidget.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)
            file = octopiclient.retrieveFileInformation(self.fileListWidget.currentItem().text())
            try:
                self.fileSizeSelected.setText(size(file['size']))
            except KeyError:
                self.fileSizeSelected.setText('-')
            try:
                self.fileDateSelected.setText(datetime.fromtimestamp(file['date']).strftime('%d/%m/%Y %H:%M:%S'))
            except KeyError:
                self.fileDateSelected.setText('-')
            try:
                m, s = divmod(file['gcodeAnalysis']['estimatedPrintTime'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.filePrintTimeSelected.setText("%dd:%dh:%02dm:%02ds" % (d, h, m, s))
            except KeyError:
                self.filePrintTimeSelected.setText('-')
            try:
                self.filamentVolumeSelected.setText(
                    ("%.2f cm" % file['gcodeAnalysis']['filament']['tool0']['volume']) + unichr(179))
            except KeyError:
                self.filamentVolumeSelected.setText('-')

            try:
                self.filamentLengthFileSelected.setText(
                    "%.2f mm" % file['gcodeAnalysis']['filament']['tool0']['length'])
            except KeyError:
                self.filamentLengthFileSelected.setText('-')
            # uncomment to select the file when selectedd in list
            # octopiclient.selectFile(self.fileListWidget.currentItem().text(), False)
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)

            '''
            If image is available from server, set it, otherwise display default image
            '''
            img = octopiclient.getImage(self.fileListWidget.currentItem().text().replace(".gcode", ".png"))
            if img:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(img)
                self.printPreviewSelected.setPixmap(pixmap)

            else:
                self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))
        except:
            print "Log: Nothing Selected"
            # Set image fot print preview:
            # self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))
            # print self.fileListWidget.currentItem().text().replace(".gcode","")
            # self.printPreviewSelected.setPixmap(QtGui.QPixmap(_fromUtf8("/home/pi/.octoprint/uploads/{}.png".format(self.FileListWidget.currentItem().text().replace(".gcode","")))))

            # Check if the PNG file exists, and if it does display it, or diplay a default picture.

    def printSelectedUSB(self):
        '''
        Sets the screen to the print selected screen for USB, on which you can transfer to local drive and view preview image.
        :return:
        '''
        try:
            self.fileSelectedUSBName.setText(self.fileListWidgetUSB.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedUSBPage)
            file = '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text().replace(".gcode", ".png"))
            try:
                exists = os.path.exists(file)
            except:
                exists = False

            if exists:
                self.printPreviewSelectedUSB.setPixmap(QtGui.QPixmap(_fromUtf8(file)))
            else:
                self.printPreviewSelectedUSB.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))
        except:
            print "Log: Nothing Selected"

            # Set Image from USB

    def transferToLocal(self, prnt=False):
        '''
        Transfers a file from USB mounted at /media/usb0 to octoprint's watched folder so that it gets automatically detected bu Octoprint.
        Warning: If the file is read-only, octoprint API for reading the file crashes.
        '''

        file = '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text())

        self.uploadThread = ThreadFileUpload(file, prnt=prnt)
        self.uploadThread.start()
        if prnt:
            self.stackedWidget.setCurrentWidget(self.homePage)

    def printFile(self):
        '''
        Prints the file selected from printSelected()
        '''
        octopiclient.selectFile(self.fileListWidget.currentItem().text(), True)
        # octopiclient.startPrint()
        self.stackedWidget.setCurrentWidget(self.homePage)

    def deleteItem(self):
        '''
        Deletes a gcode file, and if associates, its image file from the memory
        '''
        octopiclient.deleteFile(self.fileListWidget.currentItem().text())
        octopiclient.deleteFile(self.fileListWidget.currentItem().text().replace(".gcode", ".png"))

        # delete PNG also
        self.fileListLocal()

    ''' +++++++++++++++++++++++++++++++++Printer Status+++++++++++++++++++++++++++++++ '''

    def updateTemperature(self, temperature):
        '''
        Slot that gets a signal originating from the thread that keeps polling for printer status
        runs at 1HZ, so do things that need to be constantly updated only. This also controls the cooling fan depending on the temperatures
        :param temperature: dict containing key:value pairs with keys being the tools, bed and their values being their corresponding temperratures
        '''

        if temperature['tool0Target'] == 0:
            self.tool0TempBar.setMaximum(390)
            self.tool0TempBar.setStyleSheet(styles.bar_heater_cold)
        elif temperature['tool0Actual'] <= temperature['tool0Target']:
            self.tool0TempBar.setMaximum(temperature['tool0Target'])
            self.tool0TempBar.setStyleSheet(styles.bar_heater_heating)
        else:
            self.tool0TempBar.setMaximum(temperature['tool0Actual'])
        self.tool0TempBar.setValue(temperature['tool0Actual'])
        self.tool0ActualTemperature.setText(str(int(temperature['tool0Actual'])))  # + unichr(176)
        self.tool0TargetTemperature.setText(str(int(temperature['tool0Target'])))

        if temperature['tool1Target'] == 0:
            self.tool1TempBar.setMaximum(390)
            self.tool1TempBar.setStyleSheet(styles.bar_heater_cold)
        elif temperature['tool1Actual'] <= temperature['tool0Target']:
            self.tool1TempBar.setMaximum(temperature['tool0Target'])
            self.tool1TempBar.setStyleSheet(styles.bar_heater_heating)
        else:
            self.tool1TempBar.setMaximum(temperature['tool1Actual'])
        self.tool1TempBar.setValue(temperature['tool1Actual'])
        self.tool1ActualTemperature.setText(str(int(temperature['tool1Actual'])))  # + unichr(176)
        self.tool1TargetTemperature.setText(str(int(temperature['tool1Target'])))

        if temperature['bedTarget'] == 0:
            self.bedTempBar.setMaximum(150)
            self.bedTempBar.setStyleSheet(styles.bar_heater_cold)
        elif temperature['bedActual'] <= temperature['bedTarget']:
            self.bedTempBar.setMaximum(temperature['bedTarget'])
            self.bedTempBar.setStyleSheet(styles.bar_heater_heating)
        else:
            self.bedTempBar.setMaximum(temperature['bedActual'])
        self.bedTempBar.setValue(temperature['bedActual'])
        self.bedActualTemperatute.setText(str(int(temperature['bedActual'])))  # + unichr(176))
        self.bedTargetTemperature.setText(str(int(temperature['bedTarget'])))  # + unichr(176))

        if temperature['chamberTarget'] == 0:
            self.chamberTempBar.setMaximum(70)
            self.chamberTempBar.setStyleSheet(styles.bar_heater_cold)
        elif temperature['chamberActual'] <= temperature['chamberTarget']:
            self.chamberTempBar.setMaximum(temperature['chamberTarget'])
            self.chamberTempBar.setStyleSheet(styles.bar_heater_heating)
        else:
            self.chamberTempBar.setMaximum(temperature['chamberActual'])
        self.chamberTempBar.setValue(temperature['chamberActual'])
        self.chamberActualTemperatute.setText(str(int(temperature['chamberActual'])))  # + unichr(176))
        self.chamberTargetTemperature.setText(str(int(temperature['chamberTarget'])))  # + unichr(176))

        if temperature['filboxTarget'] == 0:
            self.filboxTempBar.setMaximum(50)
            self.filboxTempBar.setStyleSheet(styles.bar_heater_cold)
        elif temperature['filboxActual'] <= temperature['filboxTarget']:
            self.filboxTempBar.setMaximum(temperature['filboxTarget'])
            self.filboxTempBar.setStyleSheet(styles.bar_heater_heating)
        else:
            self.filboxTempBar.setMaximum(temperature['filboxActual'])
        self.filboxTempBar.setValue(temperature['filboxActual'])
        self.filboxActualTemperatute.setText(str(int(temperature['filboxActual'])))  # + unichr(176))
        self.filboxTargetTemperature.setText(str(int(temperature['filboxTarget'])))  # + unichr(176))


        # updates the progress bar on the change filament screen
        if self.changeFilamentHeatingFlag:
            if self.activeExtruder == 0:
                if temperature['tool0Target'] == 0:
                    self.changeFilamentProgress.setMaximum(390)
                elif temperature['tool0Target'] - temperature['tool0Actual'] > 1:
                    self.changeFilamentProgress.setMaximum(temperature['tool0Target'])
                else:
                    self.changeFilamentProgress.setMaximum(temperature['tool0Actual'])
                    self.changeFilamentHeatingFlag = False
                    if self.loadFlag:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                    else:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                        octopiclient.extrude(5)     # extrudes some amount of filament to prevent plugging

                self.changeFilamentProgress.setValue(temperature['tool0Actual'])
            elif self.activeExtruder == 1:
                if temperature['tool1Target'] == 0:
                    self.changeFilamentProgress.setMaximum(390)
                elif temperature['tool1Target'] - temperature['tool1Actual'] > 1:
                    self.changeFilamentProgress.setMaximum(temperature['tool1Target'])
                else:
                    self.changeFilamentProgress.setMaximum(temperature['tool1Actual'])
                    self.changeFilamentHeatingFlag = False
                    if self.loadFlag:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                    else:
                        self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                        octopiclient.extrude(5)     # extrudes some amount of filament to prevent plugging

                self.changeFilamentProgress.setValue(temperature['tool1Actual'])

    def updatePrintStatus(self, file):
        '''
        displays infromation of a particular file on the home page,is a slot for the signal emited from the thread that keeps pooling for printer status
        runs at 1HZ, so do things that need to be constantly updated only
        :param file: dict of all the attributes of a particualr file
        '''
        if file is None:
            self.currentFile = None
            self.currentImage = None
            self.timeLeft.setText("-")
            self.fileName.setText("-")
            self.printProgressBar.setValue(0)
            self.printTime.setText("-")
            self.playPauseButton.setDisabled(True)  # if file available, make play buttom visible

        else:
            self.playPauseButton.setDisabled(False)  # if file available, make play buttom visible
            self.fileName.setText(file['job']['file']['name'])
            self.currentFile = file['job']['file']['name']
            if file['progress']['printTime'] is None:
                self.printTime.setText("-")
            else:
                m, s = divmod(file['progress']['printTime'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.printTime.setText("%d:%d:%02d:%02d" % (d, h, m, s))

            if file['progress']['printTimeLeft'] is None:
                self.timeLeft.setText("-")
            else:
                m, s = divmod(file['progress']['printTimeLeft'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.timeLeft.setText("%d:%d:%02d:%02d" % (d, h, m, s))

            if file['progress']['completion'] is None:
                self.printProgressBar.setValue(0)
            else:
                self.printProgressBar.setValue(file['progress']['completion'])

            '''
            If image is available from server, set it, otherwise display default image.
            If the image was already loaded, dont load it again.
            '''
            if self.currentImage != self.currentFile:
                self.currentImage = self.currentFile
                img = octopiclient.getImage(file['job']['file']['name'].replace(".gcode", ".png"))
                if img:
                    pixmap = QtGui.QPixmap()
                    pixmap.loadFromData(img)
                    self.printPreviewMain.setPixmap(pixmap)
                else:
                    self.printPreviewMain.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))

    def updateStatus(self, status):
        '''
        Updates the status bar, is a slot for the signal emited from the thread that constantly polls for printer status
        this function updates the status bar, as well as enables/disables relavent buttons
        :param status: String of the status text
        '''

        self.printerStatusText = status
        self.printerStatus.setText(status)

        if status == "Printing":  # Green
            self.printerStatusColour.setStyleSheet(styles.printer_status_green)
        elif status == "Offline":  # Red
            self.printerStatusColour.setStyleSheet(styles.printer_status_red)
        elif status == "Paused":  # Amber
            self.printerStatusColour.setStyleSheet(styles.printer_status_amber)
        elif status == "Operational":  # Amber
            self.printerStatusColour.setStyleSheet(styles.printer_status_blue)

        '''
        Depending on Status, enable and Disable Buttons
        '''
        if status == "Printing":
            self.playPauseButton.setChecked(True)
            self.stopButton.setDisabled(False)
            self.motionTab.setDisabled(True)
            self.changeFilamentButton.setDisabled(True)
            self.menuCalibrateButton.setDisabled(True)
            self.menuPrintButton.setDisabled(True)
            self.doorLockButton.setDisabled(False)

        elif status == "Paused":
            self.playPauseButton.setChecked(False)
            self.stopButton.setDisabled(False)
            self.motionTab.setDisabled(False)
            self.changeFilamentButton.setDisabled(False)
            self.menuCalibrateButton.setDisabled(True)
            self.menuPrintButton.setDisabled(True)
            self.doorLockButton.setDisabled(True)

        else:
            self.stopButton.setDisabled(True)
            self.playPauseButton.setChecked(False)
            self.motionTab.setDisabled(False)
            self.changeFilamentButton.setDisabled(False)
            self.menuCalibrateButton.setDisabled(False)
            self.menuPrintButton.setDisabled(False)
            self.doorLockButton.setDisabled(True)

    ''' ++++++++++++++++++++++++++++Active Extruder/Tool Change++++++++++++++++++++++++ '''

    def selectToolChangeFilament(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        '''

        if self.toolToggleChangeFilamentButton.isChecked():
            self.setActiveExtruder(1)
            octopiclient.selectTool(1)
        else:
            self.setActiveExtruder(0)
            octopiclient.selectTool(0)

    def selectToolMotion(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        '''

        if self.toolToggleMotionButton.isChecked():
            self.setActiveExtruder(1)
            octopiclient.selectTool(1)

        else:
            self.setActiveExtruder(0)
            octopiclient.selectTool(0)

    def selectToolTemperature(self):
        '''
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text.it also updates the status of the other toggle buttons
        '''
        # self.toolToggleTemperatureButton.setText(
        #     "1") if self.toolToggleTemperatureButton.isChecked() else self.toolToggleTemperatureButton.setText("0")
        if self.toolToggleTemperatureButton.isChecked():
            print "extruder 1 Temperature"
            self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
        else:
            print "extruder 0 Temperature"
            self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))

    def setActiveExtruder(self, activeNozzle):
        activeNozzle = int(activeNozzle)
        if activeNozzle == 0:
            self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/activeNozzle.png")))
            self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/Nozzle.png")))
            self.toolToggleChangeFilamentButton.setChecked(False)
            # self.toolToggleChangeFilamentButton.setText("0")
            self.toolToggleMotionButton.setChecked(False)
            self.toolToggleMotionButton.setText("0")
            self.activeExtruder = 0
        elif activeNozzle == 1:
            self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/Nozzle.png")))
            self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/activeNozzle.png")))
            self.toolToggleChangeFilamentButton.setChecked(True)
            # self.toolToggleChangeFilamentButton.setText("1")
            self.toolToggleMotionButton.setChecked(True)
            self.toolToggleMotionButton.setText("1")
            self.activeExtruder = 1

            # set button states
            # set octoprint if mismatch


    ''' +++++++++++++++++++++++++++++++++Control Screen+++++++++++++++++++++++++++++++ '''

    def control(self):
        self.stackedWidget.setCurrentWidget(self.controlPage)
        if self.toolToggleTemperatureButton.isChecked():
            self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
        else:
            self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))
        self.bedTempSpinBox.setProperty("value", float(self.bedTargetTemperature.text()))
        self.chamberTempSpinBox.setProperty("value", float(self.chamberTargetTemperature.text()))
        self.filboxTempSpinBox.setProperty("value", float(self.filboxTargetTemperature.text()))

    def setStep(self, stepRate):
        '''
        Sets the class variable "Step" which would be needed for movement and joging
        :param step: step multiplier for movement in the move
        :return: nothing
        '''

        if stepRate == 100:
            self.step100Button.setFlat(True)
            self.step1Button.setFlat(False)
            self.step10Button.setFlat(False)
            self.step = 100
        if stepRate == 1:
            self.step100Button.setFlat(False)
            self.step1Button.setFlat(True)
            self.step10Button.setFlat(False)
            self.step = 1
        if stepRate == 10:
            self.step100Button.setFlat(False)
            self.step1Button.setFlat(False)
            self.step10Button.setFlat(True)
            self.step = 10

    def setToolTemp(self):
        if self.toolToggleTemperatureButton.isChecked():
            octopiclient.gcode(command='M104 T1 S' + str(self.toolTempSpinBox.value()))
            # octopiclient.setToolTemperature({"tool1": self.toolTempSpinBox.value()})
        else:
            octopiclient.gcode(command='M104 T0 S' + str(self.toolTempSpinBox.value()))
            # octopiclient.setToolTemperature({"tool0": self.toolTempSpinBox.value()})

    def coolDownAction(self):
        ''''
        Turns all heaters and fans off
        '''
        octopiclient.gcode(command='M107')
        octopiclient.gcode(command='M104 T0 S0')
        octopiclient.gcode(command='M104 T1 S0')
        octopiclient.gcode(command='M104 T2 S0')
        octopiclient.gcode(command='M104 T3 S0')
        # octopiclient.setToolTemperature({"tool0": 0})
        octopiclient.setBedTemperature(0)
        #octopiclient.gcode(command='M141 S0')
        self.toolTempSpinBox.setProperty("value", 0)
        self.bedTempSpinBox.setProperty("value", 0)
        self.chamberTempSpinBox.setProperty("value", 0)
        self.filboxTempSpinBox.setProperty("value", 0)


    ''' +++++++++++++++++++++++++++++++++++Calibration++++++++++++++++++++++++++++++++ '''

    def setZToolOffset(self, offset, setOffset=False):
        '''
        Sets the home offset after the caliberation wizard is done, which is a callback to
        the response of M114 that is sent at the end of the Wizard in doneStep()
        :param offset: the value off the offset to set. is a str is coming from M114, and is float if coming from the nozzleOffsetPage
        :param setOffset: Boolean, is true if the function call is from the nozzleOFfsetPage
        :return:

        #TODO can make this simpler, asset the offset value to string float to begin with instead of doing confitionals
        '''
        self.currentZPosition = offset #gets the current z position, used to set new tool offsets. clean this shit up.
        #fuck you past vijay for not cleaning this up
        if self.setNewToolZOffsetFromCurrentZBool:
            newToolOffsetZ = float(self.toolOffsetZ) - float(self.currentZPosition)
            octopiclient.gcode(command='M218 T1 Z{}'.format(newToolOffsetZ))  # restore eeprom settings to get Z home offset, mesh bed leveling back
            self.setNewToolZOffsetFromCurrentZBool =False
            octopiclient.gcode(command='M500')  # store eeprom settings to get Z home offset, mesh bed leveling back

    def showProbingFailed(self):
        self.tellAndReboot("Bed position is not calibrated. Please run calibration wizard after restart.")

    def updateEEPROMProbeOffset(self, offset):
        '''
        Sets the spinbox value to have the value of the Z offset from the printer.
        the value is -ve so as to be more intuitive.
        :param offset:
        :return:
        '''
        self.nozzleOffsetDoubleSpinBox.setValue(float(offset))

    def setZProbeOffset(self, offset):
        '''
        Sets Z Probe offset from spinbox

        #TODO can make this simpler, asset the offset value to string float to begin with instead of doing confitionals
        '''

        octopiclient.gcode(command='M851 Z{}'.format(offset))
        octopiclient.gcode(command='M500')

    def requestEEPROMProbeOffset(self):
        '''
        Updates the value of probe offset in the nozzle offset spinbox. Sends M503 so that the pritner returns the value as a websocket calback
        :return:
        '''
        octopiclient.gcode(command='M503')
        self.stackedWidget.setCurrentWidget(self.nozzleOffsetPage)

    def nozzleOffset(self):
        '''
        Updates the value of M206 Z in the nozzle offset spinbox. Sends M503 so that the pritner returns the value as a websocket calback
        :return:
        '''
        octopiclient.gcode(command='M503')
        self.stackedWidget.setCurrentWidget(self.nozzleOffsetPage)

    def toolOffsetXY(self):
        octopiclient.gcode(command='M503')
        self.stackedWidget.setCurrentWidget(self.toolOffsetXYPage)

    def toolOffsetZ(self):
        octopiclient.gcode(command='M503')
        self.stackedWidget.setCurrentWidget(self.toolOffsetZpage)

    def setToolOffsetX(self):
        octopiclient.gcode(command='M218 T1 X{}'.format(self.toolOffsetXDoubleSpinBox.value()))  # restore eeprom settings to get Z home offset, mesh bed leveling back
        octopiclient.gcode(command='M500')

    def setToolOffsetY(self):
        octopiclient.gcode(command='M218 T1 Y{}'.format(self.toolOffsetYDoubleSpinBox.value()))  # restore eeprom settings to get Z home offset, mesh bed leveling back
        octopiclient.gcode(command='M500')
        octopiclient.gcode(command='M500')

    def setToolOffsetZ(self):
        octopiclient.gcode(command='M218 T1 Z{}'.format(self.toolOffsetZDoubleSpinBox.value()))  # restore eeprom settings to get Z home offset, mesh bed leveling back
        octopiclient.gcode(command='M500')

    def getToolOffset(self, M218Data):
        if 'T1' in M218Data:
            if 'Z' in M218Data:
                self.toolOffsetZ = M218Data[M218Data.index('Z') + 1:].split(' ', 1)[0]
                self.toolOffsetZDoubleSpinBox.setValue(float(self.toolOffsetZ))
            if 'X' in M218Data:
                self.toolOffsetX = M218Data[M218Data.index('X') + 1:].split(' ', 1)[0]
                self.toolOffsetXDoubleSpinBox.setValue(float(self.toolOffsetX))
            if 'Y' in M218Data:
                self.toolOffsetY = M218Data[M218Data.index('Y') + 1:].split(' ', 1)[0]
                self.toolOffsetYDoubleSpinBox.setValue(float(self.toolOffsetY))




    def quickStep1(self):
        '''
        Shows welcome message.
        Homes to MAX
        goes to position where leveling screws can be opened
        :return:
        '''
        self.toolZOffsetCaliberationPageCount = 0
        octopiclient.gcode(command='M104 S200')
        octopiclient.gcode(command='M104 T1 S200')
        octopiclient.gcode(command='M211 S0')  # Disable software endstop
        octopiclient.gcode(command='T0')  # Set active tool to t0
        octopiclient.gcode(command='M503')  # makes sure internal value of Z offset and Tool offsets are stored before erasing
        octopiclient.gcode(command='M420 S0')  # Dissable mesh bed leveling for good measure
        self.stackedWidget.setCurrentWidget(self.quickStep1Page)
        octopiclient.home(['x', 'y', 'z'])
        octopiclient.jog(x=40, y=40, absolute=True, speed=2000)

    def quickStep2(self):
        '''
        levels first position (RIGHT)
        :return:
        '''
        self.stackedWidget.setCurrentWidget(self.quickStep2Page)
        octopiclient.jog(x=calibrationPosition['X1'], y=calibrationPosition['Y1'], absolute=True, speed=2000)
        octopiclient.jog(z=0, absolute=True, speed=1500)

    def quickStep3(self):
        '''
        levels second leveling position (LEFT)
        '''
        self.stackedWidget.setCurrentWidget(self.quickStep3Page)
        octopiclient.jog(z=10, absolute=True, speed=1500)
        octopiclient.jog(x=calibrationPosition['X2'], y=calibrationPosition['Y2'], absolute=True, speed=2000)
        octopiclient.jog(z=0, absolute=True, speed=1500)

    def quickStep4(self):
        '''
        levels third leveling position  (BACK)
        :return:
        '''
        # sent twice for some reason
        self.stackedWidget.setCurrentWidget(self.quickStep4Page)
        octopiclient.jog(z=10, absolute=True, speed=1500)
        octopiclient.jog(x=calibrationPosition['X3'], y=calibrationPosition['Y3'], absolute=True, speed=2000)
        octopiclient.jog(z=0, absolute=True, speed=1500)

    def nozzleHeightStep1(self):
        if self.toolZOffsetCaliberationPageCount == 0 :
            self.toolZOffsetLabel.setText("Move the bed up or down to the First Nozzle , testing height using paper")
            self.stackedWidget.setCurrentWidget(self.nozzleHeightStep1Page)
            octopiclient.jog(z=10, absolute=True, speed=1500)
            octopiclient.jog(x=calibrationPosition['X4'], y=calibrationPosition['Y4'], absolute=True, speed=2000)
            octopiclient.jog(z=1, absolute=True, speed=1500)
            self.toolZOffsetCaliberationPageCount = 1
        elif self.toolZOffsetCaliberationPageCount == 1:
            self.toolZOffsetLabel.setText("Move the bed up or down to the Second Nozzle , testing height using paper")
            octopiclient.gcode(command='G92 Z0')#set the current Z position to zero
            octopiclient.jog(z=1, absolute=True, speed=1500)
            octopiclient.gcode(command='T1')
            self.toolZOffsetCaliberationPageCount = 2
        else:
            self.doneStep()

    def doneStep(self):
        '''
        Exits leveling
        :return:
        '''
        self.setNewToolZOffsetFromCurrentZBool = True
        octopiclient.gcode(command='M114')
        octopiclient.jog(z=4, absolute=True, speed=1500)
        octopiclient.gcode(command='T0')
        octopiclient.gcode(command='M211 S1')  # Disable software endstop
        self.stackedWidget.setCurrentWidget(self.calibratePage)
        octopiclient.home(['x', 'y', 'z'])
        octopiclient.gcode(command='M104 S0')
        octopiclient.gcode(command='M500')  # store eeprom settings to get Z home offset, mesh bed leveling back

    def cancelStep(self):
        self.stackedWidget.setCurrentWidget(self.calibratePage)
        octopiclient.home(['x', 'y', 'z'])
        octopiclient.gcode(command='M104 S0')

    def testPrint(self,tool0Diameter,tool1Diameter,gcode):
        '''
        Prints a test print
        :param tool0Diameter: Diameter of tool 0 nozzle.04,06 or 08
        :param tool1Diameter: Diameter of tool 1 nozzle.40,06 or 08
        :param gcode: type of gcode to print, dual nozzle calibration, bed leveling, movement or samaple prints in
        single and dual. bedLevel, dualCalibration, movementTest, dualTest, singleTest
        :return:
        '''
        if gcode is 'bedLevel':
            self.printFromPath('gcode/' + tool0Diameter + '_BedLeveling.gcode', True)
        elif gcode is 'dualCalibration':
            self.printFromPath(
                'gcode/' + tool0Diameter + '_' + tool1Diameter + '_dual_extruder_calibration_Volterra.gcode',
                True)
        elif gcode is 'movementTest':
            self.printFromPath('gcode/movementTest.gcode', True)
        elif gcode is 'dualTest':
            self.printFromPath(
                'gcode/' + tool0Diameter + '_' + tool1Diameter + '_Fracktal_logo_Volterra.gcode',
                True)
        elif gcode is 'singleTest':
            self.printFromPath('gcode/' + tool0Diameter + '_Fracktal_logo_Volterra.gcode',True)

        else:
            print 'gcode not found'

    def printFromPath(self,path,prnt=True):
        '''
        Transfers a file from a specific to octoprint's watched folder so that it gets automatically detected by Octoprint.
        Warning: If the file is read-only, octoprint API for reading the file crashes.
        '''

        self.uploadThread = ThreadFileUpload(path, prnt=prnt)
        self.uploadThread.start()
        if prnt:
            self.stackedWidget.setCurrentWidget(self.homePage)


    ''' +++++++++++++++++++++++++++++++++++Keyboard++++++++++++++++++++++++++++++++ '''

    def startKeyboard(self, returnFn, onlyNumeric=False, noSpace=False, text=""):
        '''
        starts the keyboard screen for entering Password
        '''
        keyBoardobj = keyboard.Keyboard(onlyNumeric=onlyNumeric, noSpace=noSpace, text=text)
        self.connect(keyBoardobj, QtCore.SIGNAL('KEYBOARD'), returnFn)
        keyBoardobj.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        keyBoardobj.show()

    ''' ++++++++++++++++++++++++++++++Restore Defaults++++++++++++++++++++++++++++ '''

    def restoreFactoryDefaults(self):
        if dialog.WarningYesNo(self, "Are you sure you want to restore machine state to factory defaults?\nWarning: Doing so will also reset printer profiles, WiFi & Ethernet config.",
                               overlay=True):
            os.system('sudo cp -f config/dhcpcd.conf /etc/dhcpcd.conf')
            os.system('sudo cp -f config/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf')
            os.system('sudo rm -rf /home/pi/.octoprint/users.yaml')
            os.system('sudo rm -rf /home/pi/.octoprint/printerProfiles/*')
            os.system('sudo rm -rf /home/pi/.octoprint/scripts/gcode')
            os.system('sudo cp -f config/config_Volterra400Dual.yaml /home/pi/.octoprint/config.yaml')
            self.tellAndReboot("Settings restored. Rebooting...")

    def restorePrintDefaults(self):
        if dialog.WarningYesNo(self, "Are you sure you want to restore default print settings?\nWarning: Doing so will erase offsets and bed leveling info",
                               overlay=True):
            octopiclient.gcode(command='M502')
            octopiclient.gcode(command='M500')

    ''' +++++++++++++++++++++++++++++++++++ Misc ++++++++++++++++++++++++++++++++ '''

    def tellAndReboot(self, msg="Rebooting...", overlay=True):
        if dialog.WarningOk(self, msg, overlay=overlay):
            os.system('sudo reboot now')
            return True
        return False

    def askAndReboot(self, msg="Are you sure you want to reboot?", overlay=True):
        if dialog.WarningYesNo(self, msg, overlay=overlay):
            os.system('sudo reboot now')
            return True
        return False

    def handleStartupError(self):
        print('Shutting Down. Unable to connect')
        if dialog.WarningOk(self, "Error. Contact Support. Shutting down...", overlay=True):
            os.system('sudo shutdown now')

    def pairPhoneApp(self):
        if getIP(ThreadRestartNetworking.ETH) is not None:
            qrip = getIP(ThreadRestartNetworking.ETH)
        elif getIP(ThreadRestartNetworking.WLAN) is not None:
            qrip = getIP(ThreadRestartNetworking.WLAN)
        else:
            if dialog.WarningOk(self, "Network Disconnected"):
                return
        self.QRCodeLabel.setPixmap(
            qrcode.make("http://"+ qrip, image_factory=Image).pixmap())
        self.stackedWidget.setCurrentWidget(self.QRCodePage)


class QtWebsocket(QtCore.QThread):
    '''
    https://pypi.python.org/pypi/websocket-client
    https://wiki.python.org/moin/PyQt/Threading,_Signals_and_Slots
    '''

    def __init__(self):
        super(QtWebsocket, self).__init__()

        # ws://0.0.0.0:5000/sockjs/websocket
        url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(
            ip,  # host + port + prefix, but no protocol
            random.randrange(0, stop=999),  # server_id
            uuid.uuid4()  # session_id
        )
        # websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(url,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        # print("WS connected: " + str(self.ws.connected))
        self.ws.on_open = self.on_open
        self.ws.on_close = self.on_close

    def run(self):
        print("ws run")
        self.ws.run_forever()

    def on_message(self, ws, message):

        message_type = message[0]
        if message_type == "h":
            # "heartbeat" message
            return
        elif message_type == "o":
            # "open" message
            return
        elif message_type == "c":
            # "close" message
            return

        message_body = message[1:]
        if not message_body:
            return
        data = json.loads(message_body)[0]

        if message_type == "m":
            data = [data, ]

        if message_type == "a":
            self.process(data)

    @run_async
    def process(self, data):

        if "event" in data:
            if data["event"]["type"] == "Connected":
                self.emit(QtCore.SIGNAL('CONNECTED'))
        if "plugin" in data:
            # if data["plugin"]["plugin"] == 'VolterraFilamentSensor':
            #     # print(data["plugin"]["data"])
            #     if "type" in data["plugin"]["data"] and data["plugin"]["data"]["type"] == "hmi_msg":
            #         self.emit(QtCore.SIGNAL('FILAMENT_SENSOR_TRIGGERED'), data["plugin"]["data"])

            if data["plugin"]["plugin"] == 'VolterraServices':
                self.emit(QtCore.SIGNAL('FILAMENT_SENSOR_TRIGGERED'), data["plugin"]["data"])

            # if data["plugin"]["plugin"] == 'VolterraVAS':
            #     # print(json.dumps(data["plugin"]["data"]))
            #     # print(data["plugin"]["data"]["type"])
            #     if "type" in data["plugin"]["data"]:
            #         if data["plugin"]["data"]["type"] == "door_state":
            #             self.emit(QtCore.SIGNAL('DOOR_LOCK_STATE'), data["plugin"]["data"])
            #         elif data["plugin"]["data"]["type"] == "hmi_msg":
            #             self.emit(QtCore.SIGNAL('DOOR_LOCK_MSG'), data["plugin"]["data"])

            if data["plugin"]["plugin"] == 'JuliaFirmwareUpdater':
                self.emit(QtCore.SIGNAL('FIRMWARE_UPDATER'), data["plugin"]["data"])

            elif data["plugin"]["plugin"] == 'softwareupdate':
                if data["plugin"]["data"]["type"] == "updating":
                    self.emit(QtCore.SIGNAL('UPDATE_STARTED'), data["plugin"]["data"]["data"])
                elif data["plugin"]["data"]["type"] == "loglines":
                    self.emit(QtCore.SIGNAL('UPDATE_LOG'), data["plugin"]["data"]["data"]["loglines"])
                elif data["plugin"]["data"]["type"] == "restarting":
                    self.emit(QtCore.SIGNAL('UPDATE_LOG_RESULT'), data["plugin"]["data"]["data"]["results"])
                elif data["plugin"]["data"]["type"] == "update_failed":
                    self.emit(QtCore.SIGNAL('UPDATE_FAILED'), data["plugin"]["data"]["data"])

        if "current" in data:
            if data["current"]["messages"]:
                for item in data["current"]["messages"]:
                    if 'M206' in item:
                        self.emit(QtCore.SIGNAL('Z_HOME_OFFSET'), item[item.index('Z') + 1:].split(' ', 1)[0])
                    if 'Count' in item:  # can get thris throught the positionUpdate event
                        self.emit(QtCore.SIGNAL('SET_Z_TOOL_OFFSET'), item[item.index('Z') + 2:].split(' ', 1)[0],
                                  False)
                    if 'M218' in item:
                        self.emit(QtCore.SIGNAL('TOOL_OFFSET'), item[item.index('M218'):])
                    if 'Active Extruder' in item:  # can get thris throught the positionUpdate event
                        self.emit(QtCore.SIGNAL('ACTIVE_EXTRUDER'), item[-1])
                    
                    if 'M851' in item:
                        self.emit(QtCore.SIGNAL('Z_PROBE_OFFSET'), item[item.index('Z') + 1:].split(' ', 1)[0])
                    if 'PROBING_FAILED' in item:
                        self.emit(QtCore.SIGNAL('Z_PROBING_FAILED'))

            if data["current"]["state"]["text"]:
                self.emit(QtCore.SIGNAL('STATUS'), data["current"]["state"]["text"])

            fileInfo = {"job": data["current"]["job"], "progress": data["current"]["progress"]}
            if fileInfo['job']['file']['name'] is not None:
                self.emit(QtCore.SIGNAL('PRINT_STATUS'), fileInfo)
            else:
                self.emit(QtCore.SIGNAL('PRINT_STATUS'), None)

            def temp(data, tool, temp):
                try:
                    return data["current"]["temps"][0][tool][temp]
                except:
                    return 0

            if data["current"]["temps"] and len(data["current"]["temps"]) > 0:
                try:
                    temperatures = {'tool0Actual': temp(data, "tool0", "actual"),
                                    'tool0Target': temp(data, "tool0", "target"),
                                    'tool1Actual': temp(data, "tool1", "actual"),
                                    'tool1Target': temp(data, "tool1", "target"),
                                    'bedActual': temp(data, "bed", "actual"),
                                    'bedTarget': temp(data, "bed", "target"),
                                    'chamberActual': temp(data, "tool2", "actual"),
                                    'chamberTarget': temp(data, "tool2", "target"),
                                    'filboxActual': temp(data, "tool3", "actual"),
                                    'filboxTarget': temp(data, "tool3", "target")}
                    self.emit(QtCore.SIGNAL('TEMPERATURES'), temperatures)
                except KeyError:
                    # temperatures = {'tool0Actual': 0,
                    #                 'tool0Target': 0,
                    #                 'tool1Actual': 0,
                    #                 'tool1Target': 0,
                    #                 'bedActual': 0,
                    #                 'bedTarget': 0}
                    pass

    def on_open(self, ws):
        print('Websocket opened')
        pass

    def on_close(self, ws):
        print('Websocket closed')
        pass

    def on_error(self, ws, error):
        print(error)
        pass


class ThreadSanityCheck(QtCore.QThread):
    def __init__(self):
        super(ThreadSanityCheck, self).__init__()
        self.MKSPort = None
        self.virtual = False

    def run(self):
        global octopiclient
        shutdown_flag = False
        # get the first value of t1 (runtime check)
        uptime = 0
        # keep trying untill octoprint connects
        while (True):
            # Start an object instance of octopiAPI
            try:
                if (uptime > 30):
                    shutdown_flag = True
                    self.emit(QtCore.SIGNAL('STARTUP_ERROR'))
                    break
                octopiclient = octoprintAPI(ip, apiKey)
                result = subprocess.Popen("dmesg | grep 'ttyUSB'", stdout=subprocess.PIPE, shell=True).communicate()[0]
                result = result.split('\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
                result = [s.strip() for s in result]
                for line in result:
                    if 'ch341-uart' in line:
                        self.MKSPort = line[line.index('ttyUSB'):line.index('ttyUSB') + 7]
                        print
                        self.MKSPort
                    elif 'FTDI' in line:
                        self.MKSPort = line[line.index('ttyUSB'):line.index('ttyUSB') + 7]
                        print
                        self.MKSPort

                if not self.MKSPort:
                    octopiclient.connectPrinter(port="VIRTUAL", baudrate=115200)
                    self.virtual = True
                    print("Connecting to VIRTUAL")
                else:
                    octopiclient.connectPrinter(port="/dev/" + self.MKSPort, baudrate=115200)
                    self.virtual = False
                    print("Connecting to " + str(self.MKSPort))
                break
            except:
                time.sleep(1)
                uptime = uptime + 1
                print("Not Connected!")
        if not shutdown_flag:
            self.emit(QtCore.SIGNAL('LOADED'), self.virtual)


class ThreadFileUpload(QtCore.QThread):
    def __init__(self, file, prnt=False):
        super(ThreadFileUpload, self).__init__()
        self.file = file
        self.prnt = prnt

        try:
            exists = os.path.exists(self.file.replace(".gcode", ".png"))
        except:
            exists = False
        if exists:
            octopiclient.uploadImage(self.file.replace(".gcode", ".png"))
        if self.prnt:
            octopiclient.uploadGcode(file=self.file, select=True, prnt=True)
        else:
            octopiclient.uploadGcode(file=self.file, select=False, prnt=False)


class ThreadRestartNetworking(QtCore.QThread):
    WLAN = "wlan0"
    ETH = "eth0"

    def __init__(self, interface, signal):
        super(ThreadRestartNetworking, self).__init__()
        self.interface = interface
        self.signal = signal

    def run(self):
        self.restart_interface()
        attempt = 0
        while attempt < 3:
            if getIP(self.interface):
                self.emit(QtCore.SIGNAL(self.signal), getIP(self.interface))
                break
            else:
                attempt += 1
                time.sleep(2)
        if attempt >= 3:
            self.emit(QtCore.SIGNAL(self.signal), None)

    def restart_interface(self):
        '''
        restars wlan0 wireless interface to use new changes in wpa_supplicant.conf file
        :return:
        '''
        if self.interface == "wlan0":
            subprocess.call(["wpa_cli","-i",  self.interface, "reconfigure"], shell=False)
        if self.interface == "eth0":
            subprocess.call(["ifconfig",  self.interface, "down"], shell=False)
            time.sleep(1)
            subprocess.call(["ifconfig", self.interface, "up"], shell=False)

        time.sleep(5)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    # Intialize the library (must be called once before other functions).
    # Creates an object of type MainUiClass
    MainWindow = MainUiClass()
    MainWindow.show()
    # MainWindow.showFullScreen()
    # MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    # Create NeoPixel object with appropriate configuration.
    # charm = FlickCharm()
    # charm.activateOn(MainWindow.FileListWidget)
sys.exit(app.exec_())
