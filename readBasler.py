# script captures images from Basler cameras

# by: M. Trzeciak, 2026
#============================================================================================
# IMPORT LIBRARIES
#--------------------------------------------------------------------------------------------
import pypylon.pylon as py
import pypylon.genicam as geni
import numpy as np
from PIL import Image, ImageChops
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QVBoxLayout,\
    QHBoxLayout, QGridLayout, QPushButton, QFrame, QLineEdit, QSlider, QProgressBar, QComboBox, QListWidget,\
    QRadioButton, QCheckBox, QMessageBox
from PySide6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

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
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        exitAction = fileMenu.addAction('Exit')
        exitAction.triggered.connect(self.close)
        
        container = QWidget()
        self.setCentralWidget(container)

        layout = QGridLayout(container)

        cam_container = QFrame()
        cam_container.setFrameShape(QFrame.Box)
        cam_layout = QGridLayout(cam_container)
        cam_label = QLabel('CAMERA SETTINGS')
        cam_label.setAlignment(Qt.AlignCenter)
        cam_label.setStyleSheet("font-family: Helvetica; font-size: 18px; font-weight: bold; color: blue")

        cam_button1 = QPushButton('Init Cameras')
        cam_button1.clicked.connect(self.initCameras)
        cam_button2 = QPushButton('Shot Cameras')
        cam_button2.clicked.connect(self.shotCameras)
        self.cam_lineedit1 = QLineEdit('set gain')
        self.cam_lineedit1.returnPressed.connect(self.setGain)
        self.cam_lineedit2 = QLineEdit('set gamma')
        self.cam_lineedit2.returnPressed.connect(self.setGamma)        
        self.cam_lineedit3 = QLineEdit('set exposure time')
        self.cam_lineedit3.returnPressed.connect(self.setExpTime)
        self.cam_combobox1 = QComboBox()
        
        for cmp in list(colormaps):
            self.cam_combobox1.addItem(cmp)
        self.cam_combobox1.currentIndexChanged.connect(self.setColormap)

        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)

        cam_layout.addWidget(cam_label,   0, 0,  1, 1)
        cam_layout.addWidget(cam_button1, 1, 1,  1, 1)
        cam_layout.addWidget(cam_button2, 2, 1,  1, 1)
        cam_layout.addWidget(self.cam_lineedit1, 3, 1, 1, 1)
        cam_layout.addWidget(self.cam_lineedit2, 4, 1, 1, 1)
        cam_layout.addWidget(self.cam_lineedit3, 5, 1, 1, 1)
        cam_layout.addWidget(self.cam_combobox1, 6, 1, 1, 1)
        cam_layout.addWidget(self.canvas, 1, 0, 16, 1)
        cam_layout.setColumnStretch(0,3)
        cam_layout.setColumnStretch(1,1)

        hdr_container = QFrame()
        hdr_container.setFrameShape(QFrame.Box)
        hdr_layout = QVBoxLayout(hdr_container)
        hdr_label = QLabel('HARDWARE SETTINGS')
        hdr_label.setAlignment(Qt.AlignCenter)
        hdr_label.setStyleSheet("font-family: Helvetica; font-size: 18px; font-weight: bold; color: blue")
        
        hdr_layout.addWidget(hdr_label)

        exe_container = QFrame()
        exe_container.setFrameShape(QFrame.Box)

        layout.addWidget(cam_container, 0, 0, 2, 1)
        layout.addWidget(hdr_container, 0, 1, 1, 1)
        layout.addWidget(exe_container, 1, 1, 1, 1)
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,1)
        
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
            cam.ExposureTime.SetValue = 999999
            cam.Gain.SetValue(10.0)
            cam.Gamma.SetValue(0.5)
    
        print(devs[0].GetModelName(),' (',devs[0].GetSerialNumber(),') detected')
        print(devs[1].GetModelName(),' (',devs[1].GetSerialNumber(),') detected')

    def shotCameras(self):
    
        res1 = self.camtop.GrabOne(1500)
        res2 = self.camhor.GrabOne(1500)
        if res1.GrabSucceeded() and res2.GrabSucceeded():
            img1 = Image.fromarray(res1.Array)
            img1 = img1.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            img2 = Image.fromarray(res2.Array)

        # ax1 = self.fig.add_subplot(2,1,1)
        ax1 = self.fig.add_axes([0, 0.55, 1, ])
        ax1.imshow(img1, cmap = self.cmap)
        ax1.axis('off')
        ax1.set_title('Top camera')
        ax2 = self.fig.add_subplot(2,1,2)
        ax2.imshow(img2, cmap = self.cmap)
        ax2.axis('off')
        ax2.set_title('Horizontal camera')
        self.canvas.draw()
        print('New camera shots printed to screen')

    def setGain(self):
        gain = float(self.cam_lineedit1.text())
        self.camtop.Gain.SetValue = gain 
        self.camhor.Gain.SetValue = gain
        print('Gain set to', gain)

    def setGamma(self):
        gamma = float(self.cam_lineedit2.text())
        self.camtop.Gamma.SetValue = gamma 
        self.camhor.Gamma.SetValue = gamma 
        print('Gamma set to', gamma)

    def setExpTime(self):
        exptime = int(self.cam_lineedit3.text())
        self.camtop.ExposureTime.SetValue = exptime 
        self.camhor.ExposureTime.SetValue = exptime
        print('Exposure time set to', exptime)

    def setColormap(self):
        cmap = self.cam_combobox1.currentText()
        self.cmap = cmap
        print('Colormap updated to',cmap)
#============================================================================================
# INITIALIZE CAMERAS
#--------------------------------------------------------------------------------------------
# camtop, camhor = initCameras()
# #============================================================================================
# # TAKE SINGLE PICTURES
# #--------------------------------------------------------------------------------------------
# img1 = grabSinglePicture(camtop, flip=True)
# img2 = grabSinglePicture(camhor, flip=False)
# #============================================================================================
# # PLOT IMAGES
# #--------------------------------------------------------------------------------------------
# plotPictures(img1, img2)



app = QApplication()

window = MainWindow()
window.showMaximized()

app.exec()