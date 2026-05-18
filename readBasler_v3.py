# script captures images from Basler cameras

# by: M. Trzeciak, 2026
#============================================================================================
# IMPORT LIBRARIES
#--------------------------------------------------------------------------------------------
import pypylon.pylon as py
import pypylon.genicam as geni
import numpy as np
import time
import sys
from datetime import datetime
from PIL import Image, ImageChops
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout,\
    QHBoxLayout, QGridLayout, QPushButton, QFrame, QLineEdit, QSlider, QProgressBar, QComboBox, QListWidget,\
    QRadioButton, QCheckBox, QMessageBox
from PySide6.QtCore import Qt, QThread, QRunnable, QThreadPool, Slot, QObject, Signal
import threading
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

#============================================================================================
# DATA ACQUISITION THREAD 
#--------------------------------------------------------------------------------------------
class WorkerSignals(QObject):
    finished = Signal(str)

class Worker(QRunnable):
    def __init__(self, callback_func, *args, **kwargs):
        super().__init__()
        self.callback_func = callback_func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        # This runs in the background thread
        result = self.callback_func(*self.args, **self.kwargs)
        # Emit result back to the main thread
        self.signals.finished.emit(result)

#============================================================================================
# GRAPHICAL USER INTERFACE DEFINITION
#--------------------------------------------------------------------------------------------
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle('Photoelastic Ice Shearing Device Control')
        self.camtop = None
        self.camhor = None
        self.cmap = 'gray'
        self.outputpath = 'D:/ZoetLab/FringeShear/data/'

        self.thread_pool = QThreadPool()

        #--------------------------------------------------------------------------------------------
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        exitAction = fileMenu.addAction('Exit')
        exitAction.triggered.connect(self.closeUI)
        #--------------------------------------------------------------------------------------------
        # 1 -- main container
        container = QWidget()
        self.setCentralWidget(container)
        layout = QGridLayout(container)
        #--------------------------------------------------------------------------------------------
        # 1.1 -- camera settings container
        cam_container = QFrame()
        cam_container.setFrameShape(QFrame.Box)
        cam_layout = QGridLayout(cam_container)
        cam_label = QLabel('CAMERA CONTROL')
        cam_label.setAlignment(Qt.AlignCenter)
        cam_label.setStyleSheet("font-family: Helvetica; font-size: 18px; font-weight: bold; color: blue")
        #--------------------------------------------------------------------------------------------
        # 1.1.1 -- initiliaze cameras push button
        self.cam_button1 = QPushButton('Init Cameras')
        self.cam_button1.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.cam_button1.clicked.connect(self.initCameras)
        #--------------------------------------------------------------------------------------------
        # 1.1.2 -- shot cameras push button
        self.cam_button2 = QPushButton('Shot Cameras')
        self.cam_button2.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.cam_button2.clicked.connect(self.shotCameras)
        #--------------------------------------------------------------------------------------------
        # 1.1.3 -- top camera parameters label
        camtop_edits_lab = QLabel('Top camera parameters:')
        camtop_edits_lab.setStyleSheet("color: black; font-weight: bold")
        #--------------------------------------------------------------------------------------------
        # 1.1.4 -- set gain label and line edit
        camtop_edit1_cont = QWidget()
        camtop_edit1_lay  = QHBoxLayout(camtop_edit1_cont)
        camtop_edit1_lab = QLabel('Gain: ')
        self.camtop_lineedit1 = QLineEdit()
        self.camtop_lineedit1.returnPressed.connect(self.setGainTop)
        camtop_edit1_lay.addWidget(camtop_edit1_lab)
        camtop_edit1_lay.addWidget(self.camtop_lineedit1)
        #--------------------------------------------------------------------------------------------
        # 1.1.5 -- set gamma label and line edit
        camtop_edit2_cont = QWidget()
        camtop_edit2_lay  = QHBoxLayout(camtop_edit2_cont)
        camtop_edit2_lab = QLabel('Gamma: ')
        self.camtop_lineedit2 = QLineEdit()
        self.camtop_lineedit2.returnPressed.connect(self.setGammaTop)
        camtop_edit2_lay.addWidget(camtop_edit2_lab)
        camtop_edit2_lay.addWidget(self.camtop_lineedit2)
        #--------------------------------------------------------------------------------------------
        # 1.1.6 -- set exposure time label and line edit
        camtop_edit3_cont = QWidget()
        camtop_edit3_lay  = QHBoxLayout(camtop_edit3_cont)
        camtop_edit3_lab = QLabel('Exp time: ')
        self.camtop_lineedit3 = QLineEdit()
        self.camtop_lineedit3.returnPressed.connect(self.setExpTimeTop)
        camtop_edit3_lay.addWidget(camtop_edit3_lab)
        camtop_edit3_lay.addWidget(self.camtop_lineedit3)
        #--------------------------------------------------------------------------------------------
        # 1.1.7 -- Horizontal Camera parameters label
        camhor_edits_lab = QLabel('Horizontal camera parameters:')
        camhor_edits_lab.setStyleSheet("color: black; font-weight: bold")
        #--------------------------------------------------------------------------------------------
        # 1.1.8 -- set gain label and line edit
        camhor_edit1_cont = QWidget()
        camhor_edit1_lay  = QHBoxLayout(camhor_edit1_cont)
        camhor_edit1_lab = QLabel('Gain: ')
        self.camhor_lineedit1 = QLineEdit()
        self.camhor_lineedit1.returnPressed.connect(self.setGainHor)
        camhor_edit1_lay.addWidget(camhor_edit1_lab)
        camhor_edit1_lay.addWidget(self.camhor_lineedit1)
        #--------------------------------------------------------------------------------------------
        # 1.1.9 -- set gamma label and line edit
        camhor_edit2_cont = QWidget()
        camhor_edit2_lay  = QHBoxLayout(camhor_edit2_cont)
        camhor_edit2_lab = QLabel('Gamma: ')
        self.camhor_lineedit2 = QLineEdit()
        self.camhor_lineedit2.returnPressed.connect(self.setGammaHor)
        camhor_edit2_lay.addWidget(camhor_edit2_lab)
        camhor_edit2_lay.addWidget(self.camhor_lineedit2)
        #--------------------------------------------------------------------------------------------
        # 1.1.10 -- set exposure time label and line edit
        camhor_edit3_cont = QWidget()
        camhor_edit3_lay  = QHBoxLayout(camhor_edit3_cont)
        camhor_edit3_lab = QLabel('Exp time: ')
        self.camhor_lineedit3 = QLineEdit()
        self.camhor_lineedit3.returnPressed.connect(self.setExpTimeHor)
        camhor_edit3_lay.addWidget(camhor_edit3_lab)
        camhor_edit3_lay.addWidget(self.camhor_lineedit3)

        #----------------------------------------------------------------------------------------        
        # 1.1.11 -- plot parameters label
        cam_plots_lab = QLabel('Plot parameters:')
        cam_plots_lab.setStyleSheet("color: black; font-weight: bold")
        #----------------------------------------------------------------------------------------        
        # 1.1.12 -- list colormaps
        cam_combo1_cont = QWidget()
        cam_combo1_lay  = QHBoxLayout(cam_combo1_cont)
        cam_combo1_lab = QLabel('ColorMap: ')
        self.cam_combobox1 = QComboBox()
        self.cam_combobox1.setCurrentText(self.cmap)
        for cmp in list(colormaps):
            self.cam_combobox1.addItem(cmp)
        self.cam_combobox1.currentIndexChanged.connect(self.setColormap)

        cam_combo1_lay.addWidget(cam_combo1_lab)
        cam_combo1_lay.addWidget(self.cam_combobox1)
        #--------------------------------------------------------------------------------------------
        # 1.1.9 -- canvas for captured images
        self.cam_fig = Figure()
        self.cam_canvas = FigureCanvas(self.cam_fig)
        #--------------------------------------------------------------------------------------------
        # 1.1 -- add widgets to camera layout
        cam_layout.addWidget(cam_label,        0, 0,  1, 1)
        cam_layout.addWidget(self.cam_button1, 1, 1,  1, 1)
        cam_layout.addWidget(self.cam_button2, 2, 1,  1, 1)
        cam_layout.addWidget(camtop_edits_lab,        3, 1,  1, 1)
        cam_layout.addWidget(camtop_edit1_cont,       4, 1,  1, 1)
        cam_layout.addWidget(camtop_edit2_cont,       5, 1,  1, 1)
        cam_layout.addWidget(camtop_edit3_cont,       6, 1,  1, 1)
        cam_layout.addWidget(camhor_edits_lab,        7, 1,  1, 1)
        cam_layout.addWidget(camhor_edit1_cont,       8, 1,  1, 1)
        cam_layout.addWidget(camhor_edit2_cont,       9, 1,  1, 1)
        cam_layout.addWidget(camhor_edit3_cont,      10, 1,  1, 1)

        cam_layout.addWidget(cam_plots_lab,        11, 1,  1, 1)
        cam_layout.addWidget(cam_combo1_cont,      12, 1,  1, 1)
        cam_layout.addWidget(self.cam_canvas,      1, 0, 16, 1)
        cam_layout.setColumnStretch(0,3)
        cam_layout.setColumnStretch(1,1)
        #--------------------------------------------------------------------------------------------
        # 1.2 -- hardware settings container
        hdr_container = QFrame()
        hdr_container.setFrameShape(QFrame.Box)
        hdr_layout = QGridLayout(hdr_container)
        hdr_label = QLabel('HARDWARE CONTROL')
        hdr_label.setAlignment(Qt.AlignCenter)
        hdr_label.setStyleSheet("font-family: Helvetica; font-size: 18px; font-weight: bold; color: blue")
        



        # 1.2.1 -- initialize read arduino push button
        self.hdr_button1 = QPushButton('Read Arduino')
        self.hdr_button1.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.hdr_button1.clicked.connect(self.readArduino)
        #--------------------------------------------------------------------------------------------
        # 1.2.2 -- shot cameras push button
        self.hdr_button2 = QPushButton('Home carriage')
        self.hdr_button2.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.hdr_button2.clicked.connect(self.homeCarriage)
        #--------------------------------------------------------------------------------------------
        # 1.2.3 -- carriage parameters label
        hdr_edits_lab = QLabel('Carriage parameters:')
        hdr_edits_lab.setStyleSheet("color: black; font-weight: bold")

        #--------------------------------------------------------------------------------------------
        # 1.2.4 -- set speed label and line edit
        hdr_edit1_cont = QWidget()
        hdr_edit1_lay  = QHBoxLayout(hdr_edit1_cont)
        hdr_edit1_lab = QLabel('Speed [m/y]: ')
        self.hdr_lineedit1 = QLineEdit()
        self.hdr_lineedit1.returnPressed.connect(self.setSpeed)
        hdr_edit1_lay.addWidget(hdr_edit1_lab)
        hdr_edit1_lay.addWidget(self.hdr_lineedit1)
        #--------------------------------------------------------------------------------------------
        # 1.2.5 -- set ----- label and line edit
        hdr_edit2_cont = QWidget()
        hdr_edit2_lay  = QHBoxLayout(hdr_edit2_cont)
        hdr_edit2_lab = QLabel('Direction [left/right]: ')
        self.hdr_lineedit2 = QLineEdit()
        self.hdr_lineedit2.returnPressed.connect(self.setDirection)
        hdr_edit2_lay.addWidget(hdr_edit2_lab)
        hdr_edit2_lay.addWidget(self.hdr_lineedit2)

        #--------------------------------------------------------------------------------------------
        # 1.2.6 -- set ----- label and line edit
        # edit3_cont = QWidget()
        # edit3_lay  = QHBoxLayout(edit3_cont)
        # edit3_lab = QLabel('Exp time: ')
        # self.cam_lineedit3 = QLineEdit()
        # self.cam_lineedit3.returnPressed.connect(self.setExpTime)
        # edit3_lay.addWidget(edit3_lab)
        # edit3_lay.addWidget(self.cam_lineedit3)
        #----------------------------------------------------------------------------------------        
        # 1.1.7 -- plot parameters label
        hdr_plots_lab = QLabel('Plot parameters:')
        hdr_plots_lab.setStyleSheet("color: black; font-weight: bold")
        #----------------------------------------------------------------------------------------        

        #--------------------------------------------------------------------------------------------
        # 1.2.9 -- canvas for data plotting
        self.hdr_fig = Figure()
        self.hdr_canvas = FigureCanvas(self.hdr_fig)
        #--------------------------------------------------------------------------------------------
        # 1.2 -- add widgets to hardware layout
        hdr_layout.addWidget(hdr_label,        0, 0,  1, 1)
        hdr_layout.addWidget(self.hdr_button1, 1, 1,  1, 1)
        hdr_layout.addWidget(self.hdr_button2, 2, 1,  1, 1)
        hdr_layout.addWidget(hdr_edits_lab,        3, 1,  1, 1)
        hdr_layout.addWidget(hdr_edit1_cont,       4, 1,  1, 1)
        hdr_layout.addWidget(hdr_edit2_cont,       5, 1,  1, 1)
        # hdr_layout.addWidget(edit3_cont,       6, 1,  1, 1)
        # hdr_layout.addWidget(hdr_plots_lab,        7, 1,  1, 1)
        hdr_layout.addWidget(self.hdr_canvas,      1, 0, 16, 1)
        hdr_layout.setColumnStretch(0,3)
        hdr_layout.setColumnStretch(1,1)


        #--------------------------------------------------------------------------------------------
        # 1.3 -- experimental execution settings container
        exe_container = QFrame()
        exe_container.setFrameShape(QFrame.Box)

        exe_layout = QGridLayout(exe_container)
        exe_label = QLabel('EXPERIMENT ACQUISITION SETUP')
        exe_label.setAlignment(Qt.AlignCenter)
        exe_label.setStyleSheet("font-family: Helvetica; font-size: 18px; font-weight: bold; color: blue")
       

        self.exe_button1 = QPushButton('Start recording')
        self.exe_button1.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.exe_button1.clicked.connect(self.startRecording)

        self.exe_button2 = QPushButton('Stop recording')
        self.exe_button2.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.exe_button2.clicked.connect(self.stopRecording)

        exe_layout.addWidget(exe_label,        0, 0,  1, 1)
        exe_layout.addWidget(self.exe_button1, 1, 1,  1, 1)
        exe_layout.addWidget(self.exe_button2, 2, 1,  1, 1)


        #--------------------------------------------------------------------------------------------
        # 1 -- add widgets to main container
        layout.addWidget(cam_container, 0, 0, 2, 1)
        layout.addWidget(hdr_container, 0, 1, 1, 1)
        layout.addWidget(exe_container, 1, 1, 1, 1)
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,1)
        
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': software opened')

    #--------------------------------------------------------------------------------------------
    # FUNCTION and CALLBACK DEFINITIONS
    def initCameras(self):

        tlf = py.TlFactory.GetInstance()
        di = py.DeviceInfo()
        devs = tlf.EnumerateDevices([di,])

        if (devs[0].GetSerialNumber == '40008690'):
            self.camtop = py.InstantCamera(tlf.CreateDevice(devs[0]))
            self.camhor = py.InstantCamera(tlf.CreateDevice(devs[1]))
        else:
            self.camtop = py.InstantCamera(tlf.CreateDevice(devs[1]))
            self.camhor = py.InstantCamera(tlf.CreateDevice(devs[0]))    

        for cam in [self.camtop, self.camhor]:
            cam.Open()
            cam.ChunkModeActive.Value = True
            cam.ChunkSelector.Value = "LineStatusAll"
            cam.ChunkEnable.Value = True
            cam.ExposureAuto.SetValue('Off')
            cam.ExposureTime.SetValue(999999.0)
            cam.Gain.SetValue(10.0)
            cam.Gamma.SetValue(0.5)

        self.cam_button1.setEnabled(False)
        self.cam_button1.setText('Cameras initialized')
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),':',devs[0].GetModelName(),' (',devs[0].GetSerialNumber(),') detected')
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),':',devs[1].GetModelName(),' (',devs[1].GetSerialNumber(),') detected')

    def plotPictures(self):
        ax1 = self.cam_fig.add_axes([0, 0.50, 1, .47])
        ax1.imshow(self.img1, cmap = self.cmap)
        ax1.axis('off')
        ax1.set_title('Top camera')
        ax2 = self.cam_fig.add_subplot([0, 0, 1, .47])
        ax2.imshow(self.img2, cmap = self.cmap)
        ax2.axis('off')
        ax2.set_title('Horizontal camera')
        self.cam_canvas.draw()
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': New camera shots printed to screen')

    def shotCameras(self):
        res1 = self.camtop.GrabOne(1500)
        res2 = self.camhor.GrabOne(1500)
        if res1.GrabSucceeded() and res2.GrabSucceeded():
            self.img1 = Image.fromarray(res1.Array)
            self.img1 = self.img1.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.img2 = Image.fromarray(res2.Array)
        self.plotPictures()

    def setGainTop(self):
        gain = float(self.camtop_lineedit1.text())
        gainmax = self.camtop.Gain.GetMax()
        gainmin = self.camtop.Gain.GetMin()
        if (gain > gainmax):
            gain = gainmax
        if (gain < gainmin):
            gain = gainmin
        self.camtop.Gain.SetValue(gain)
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Top camera gain set to', gain)

    def setGainHor(self):
        gain = float(self.camhor_lineedit1.text())
        gainmax = self.camhor.Gain.GetMax()
        gainmin = self.camhor.Gain.GetMin()
        if (gain > gainmax):
            gain = gainmax
        if (gain < gainmin):
            gain = gainmin
        self.camhor.Gain.SetValue(gain)
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Horizontal camera gain set to', gain)

    def setGammaTop(self):
        gamma = float(self.camtop_lineedit2.text())
        self.camtop.Gamma.SetValue(gamma)
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Top camera gamma set to', gamma)

    def setGammaHor(self):
        gamma = float(self.camhor_lineedit2.text())
        self.camhor.Gamma.SetValue(gamma) 
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Horizontal camera gamma set to', gamma)

    def setExpTimeTop(self):
        exptime = float(self.camtop_lineedit3.text())
        self.camtop.ExposureTime.SetValue(exptime) 
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Exposure time set to', exptime)

    def setExpTimeHor(self):
        exptime = float(self.camhor_lineedit3.text())
        self.camhor.ExposureTime.SetValue(exptime)
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Exposure time set to', exptime)

    def setColormap(self):
        cmap = self.cam_combobox1.currentText()
        self.cmap = cmap
        self.plotPictures()
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Colormap updated to',cmap)

    def setSpeed(self):
        speed = float(self.hdr_lineedit1.text())
        self.speed = speed
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Speed set to', speed,'[m/y]')

    def setDirection(self):
        direction = self.hdr_lineedit2.text()
        if (direction == 'left'):
            self.direction = 1
            print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Carriage will move to the',direction)
        elif (direction == 'right'):
            self.direction = 0
            print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Carriage will move to the',direction)
        else:
            print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': INCORRECT DIRECTION! Check and set to "left" or "right"')

    def readArduino(self):
        print()

    def homeCarriage(self):
        print()

    def savePictures(self):
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),': Image recording started')
        self.camtop.StartGrabbing()
        self.camhor.StartGrabbing()
        while(self.camtop.IsGrabbing() and self.camhor.IsGrabbing()):
            res1 = self.camtop.RetrieveResult(2000)
            now1 = datetime.now().strftime("%Y-%m-%dh%H_%M_%S")
            res2 = self.camhor.RetrieveResult(2000)
            now2 = datetime.now().strftime("%Y-%m-%dh%H_%M_%S")
            path1 = self.outputpath +'imgtop_'+now1+'.tiff' 
            path2 = self.outputpath +'imghor_'+now2+'.tiff' 
            self.img1.AttachGrabResultBuffer(res1)
            self.img1.Save(py.ImageFileFormat_Tiff, path1 )
            print('image '+path1+' saved')
            self.img2.AttachGrabResultBuffer(res2)
            self.img2.Save(py.ImageFileFormat_Tiff, path2 )
            print('image '+path2+' saved')            


    def startRecording(self):
        self.img1 = py.PylonImage()
        self.img2 = py.PylonImage()

        self.camtop.AcquisitionFrameRateEnable.SetValue(True)
        self.camtop.AcquisitionFrameRate.SetValue(1.0)
        self.camhor.AcquisitionFrameRateEnable.SetValue(True)
        self.camhor.AcquisitionFrameRate.SetValue(1.0)

        self.exe_button1.setEnabled(False)
        self.exe_button1.setText('Image acquisition in progress...')

        worker = Worker(self.savePictures)
        worker.signals.finished.connect(self.onRecordingFinished)

        self.thread_pool.start(worker)

    def stopRecording(self):
        self.camtop.StopGrabbing()
        self.camhor.StopGrabbing()   

    def onRecordingFinished(self):
        self.exe_button1.setEnabled(True)
        self.exe_button1.setText('Start recording')

    def closeUI(self):
        self.camtop.Close()
        self.camhor.Close()    
        self.close()
#============================================================================================
# EXECUTE SCRIPT
#--------------------------------------------------------------------------------------------
app = QApplication()
window = MainWindow()
window.showMaximized()
app.exec()