# program open a GUI to control the Photoelastic Ice Shearing Device

# by: M. Trzeciak, 2026
#============================================================================================
# IMPORT LIBRARIES
#--------------------------------------------------------------------------------------------
import pypylon.pylon as py
import pypylon.genicam as geni
import numpy as np
import time
import schedule
from datetime import datetime
from PIL import Image
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget,\
    QHBoxLayout, QGridLayout, QPushButton, QFrame, QLineEdit, QComboBox
from PySide6.QtCore import Qt, QRunnable, QThreadPool, Slot, QObject, Signal
import matplotlib.pyplot as plt
from matplotlib import colormaps
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

import serial
import serial.tools.list_ports as listports
#============================================================================================
# DATA ACQUISITION WORKERS DEFINITION
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

        self.ser = None
        self.isStepperRunning = False
        self.lead = 0.005
        self.gearratio = 2500
        self.microstep = 400
        self.frequency = 1000

        self.hpos = []
        self.vpos = []
        self.curr = []
        self.tvec = []
        self.it = 0
        self.N = 100

        self.outputpath = 'D:/ZoetLab/FringeShear/data/'
        logFileName = self.outputpath + datetime.now().strftime("%Y%m%d_%H%M%S")+".log"
        datFileName = self.outputpath + datetime.now().strftime("%Y%m%d_%H%M%S")+".dat"
        
        self.log = open(logFileName,'w')
        self.dat = open(datFileName,'w')

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
        # 1.1.3 -- shot cameras push button
        self.cam_button3 = QPushButton('Save Pictures')
        self.cam_button3.setStyleSheet("color: rgb(15, 100, 220); font-weight: bold")
        self.cam_button3.clicked.connect(self.saveSinglePictures)
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
        # 1.1.13 -- canvas for captured images
        self.cam_fig = Figure()
        self.cam_canvas = FigureCanvas(self.cam_fig)
        #--------------------------------------------------------------------------------------------
        # 1.1.14 -- picture recording push buttons buttons      
        self.exe_button1 = QPushButton('Start picture recording')
        self.exe_button1.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.exe_button1.clicked.connect(self.startPictureRecording)

        self.exe_button2 = QPushButton('Stop picture recording')
        self.exe_button2.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.exe_button2.clicked.connect(self.stopPictureRecording)
        #--------------------------------------------------------------------------------------------
        # 1.1 -- add widgets to camera layout
        cam_layout.addWidget(cam_label,        0, 0,  1, 1)
        cam_layout.addWidget(self.cam_button1, 1, 1,  1, 1)
        cam_layout.addWidget(self.cam_button2, 2, 1,  1, 1)
        cam_layout.addWidget(self.cam_button3, 3, 1,  1, 1)
        cam_layout.addWidget(camtop_edits_lab,        4, 1,  1, 1)
        cam_layout.addWidget(camtop_edit1_cont,       5, 1,  1, 1)
        cam_layout.addWidget(camtop_edit2_cont,       6, 1,  1, 1)
        cam_layout.addWidget(camtop_edit3_cont,       7, 1,  1, 1)
        cam_layout.addWidget(camhor_edits_lab,        8, 1,  1, 1)
        cam_layout.addWidget(camhor_edit1_cont,       9, 1,  1, 1)
        cam_layout.addWidget(camhor_edit2_cont,       10, 1,  1, 1)
        cam_layout.addWidget(camhor_edit3_cont,      11, 1,  1, 1)

        cam_layout.addWidget(cam_plots_lab,        12, 1,  1, 1)
        cam_layout.addWidget(cam_combo1_cont,      13, 1,  1, 1)

        cam_layout.addWidget(self.exe_button1,     14, 1,  1, 1)
        cam_layout.addWidget(self.exe_button2,     15, 1,  1, 1)

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
        self.hdr_button1 = QPushButton('Init Arduino')
        self.hdr_button1.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.hdr_button1.clicked.connect(self.initArduino)
        #--------------------------------------------------------------------------------------------
        # 1.2.2 -- move carriage left/right push buttons
        hdr_mov_cont = QWidget()
        hdr_mov_lay  = QHBoxLayout(hdr_mov_cont)
        self.hdr_button2 = QPushButton('<--Move left')
        self.hdr_button2.setStyleSheet("color: rgb(15, 100, 220); font-weight: bold")
        self.hdr_button2.clicked.connect(self.moveLeft)

        self.hdr_button3 = QPushButton('Move right-->')
        self.hdr_button3.setStyleSheet("color: rgb(15, 100, 220); font-weight: bold")
        self.hdr_button3.clicked.connect(self.moveRight)

        hdr_mov_lay.addWidget(self.hdr_button2)
        hdr_mov_lay.addWidget(self.hdr_button3)
        #--------------------------------------------------------------------------------------------
        # 1.2.4 -- stop carriage push button
        self.hdr_button4 = QPushButton('STOP carriage')
        self.hdr_button4.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.hdr_button4.clicked.connect(self.stopStepper)
        #--------------------------------------------------------------------------------------------
        # 1.2.5 -- set speed label and line edit
        hdr_edit1_cont = QWidget()
        hdr_edit1_lay  = QHBoxLayout(hdr_edit1_cont)
        hdr_edit1_lab = QLabel('Speed [m/y]: ')
        self.hdr_lineedit1 = QLineEdit()
        self.hdr_lineedit1.returnPressed.connect(self.setFrequency)
        hdr_edit1_lay.addWidget(hdr_edit1_lab)
        hdr_edit1_lay.addWidget(self.hdr_lineedit1)
        #--------------------------------------------------------------------------------------------
        # 1.2.6 -- read and plot data push button
        self.hdr_button5 = QPushButton('Start data recording')
        self.hdr_button5.setStyleSheet("color: rgb(30, 160, 0); font-weight: bold")
        self.hdr_button5.clicked.connect(self.startDataRecording)
        #--------------------------------------------------------------------------------------------
        # 1.2.6 -- read and plot data push button
        self.hdr_button6 = QPushButton('Stop data recording')
        self.hdr_button6.setStyleSheet("color: rgb(255, 0, 0); font-weight: bold")
        self.hdr_button6.clicked.connect(self.stopDataRecording)
        #----------------------------------------------------------------------------------------        
        # 1.2.7 -- plot parameters label
        hdr_plots_lab = QLabel('Plot parameters:')
        hdr_plots_lab.setStyleSheet("color: black; font-weight: bold")        
        #--------------------------------------------------------------------------------------------
        # 1.2.9 -- canvas for data plotting
        self.hdr_fig = Figure()
        self.hdr_canvas = FigureCanvas(self.hdr_fig)
        self.hdr_ax1 = self.hdr_fig.add_subplot(3,1,1)
        self.hdr_ax2 = self.hdr_fig.add_subplot(3,1,2)
        self.hdr_ax3 = self.hdr_fig.add_subplot(3,1,3)

        self.hdr_ax1.set_title('Horizontal position')
        self.hdr_ax2.set_title('Vertical position')
        self.hdr_ax3.set_title('Current')
        #--------------------------------------------------------------------------------------------
        # 1.2 -- add widgets to hardware layout
        hdr_layout.addWidget(hdr_label,        0, 0,  1, 1)
        hdr_layout.addWidget(self.hdr_button1, 1, 1,  1, 1)
        hdr_layout.addWidget(hdr_edit1_cont,   3, 1,  1, 1)
        hdr_layout.addWidget(hdr_mov_cont,     4, 1,  1, 1)
        hdr_layout.addWidget(self.hdr_button4, 5, 1,  1, 1)
        hdr_layout.addWidget(self.hdr_button5, 7, 1,  1, 1)
        hdr_layout.addWidget(self.hdr_button6, 8, 1,  1, 1)
        
        hdr_layout.addWidget(self.hdr_canvas,      1, 0, 16, 1)
        hdr_layout.setColumnStretch(0,3)
        hdr_layout.setColumnStretch(1,1)
        #--------------------------------------------------------------------------------------------
        # 1 -- add widgets to main container
        layout.addWidget(cam_container, 0, 0, 2, 1)
        layout.addWidget(hdr_container, 0, 1, 2, 1)
        layout.setColumnStretch(0,1)
        layout.setColumnStretch(1,1)
        
        self.printMsg('software opened', self.log)
    #--------------------------------------------------------------------------------------------
    # FUNCTION and CALLBACK DEFINITIONS
    def printMsg(self, msg, fid):
        message = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")+': '+msg
        print(message)
        fid.write(message+'\n')
    
    def initCameras(self):

        tlf = py.TlFactory.GetInstance()
        di = py.DeviceInfo()
        devs = tlf.EnumerateDevices([di,])

        if (devs[0].GetSerialNumber == '40008690'):
            self.camtop = py.InstantCamera(tlf.CreateDevice(devs[1]))
            self.camhor = py.InstantCamera(tlf.CreateDevice(devs[0]))
        else:
            self.camtop = py.InstantCamera(tlf.CreateDevice(devs[0]))
            self.camhor = py.InstantCamera(tlf.CreateDevice(devs[1]))    

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
        
        self.printMsg(devs[0].GetModelName()+' ('+devs[0].GetSerialNumber()+') detected', self.log)
        self.printMsg(devs[1].GetModelName()+' ('+devs[1].GetSerialNumber()+') detected', self.log)

    def plotPictures(self):
        ax1 = self.cam_fig.add_axes([0, 0.50, 1, .47])
        ax1.imshow(self.img1, cmap = self.cmap)
        ax1.axis('off')
        ax1.set_title('Unpolarized camera')
        ax2 = self.cam_fig.add_axes([0, 0, 1, .47])
        ax2.imshow(self.img2, cmap = self.cmap)
        ax2.axis('off')
        ax2.set_title('Polarized camera')
        self.cam_canvas.draw()
        self.printMsg('New camera shots printed to screen', self.log)

    def shotCameras(self):
        res1 = self.camtop.GrabOne(1500)
        res2 = self.camhor.GrabOne(1500)
        if res1.GrabSucceeded() and res2.GrabSucceeded():
            self.img1 = Image.fromarray(res1.Array)
            self.img1 = self.img1.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.img2 = Image.fromarray(res2.Array)
        self.plotPictures()

    def saveSinglePictures(self):
        now = datetime.now().strftime("%Y-%m-%dh%H_%M_%S")
        path1 = self.outputpath +'imgunpol_'+now+'.tiff' 
        path2 = self.outputpath +'imgpol_'  +now+'.tiff' 
        self.img1.save(path1)
        self.printMsg('image '+path1+' saved', self.log)
        self.img2.save(path2)
        self.printMsg('image '+path2+' saved', self.log)            


    def setGainTop(self):
        gain = float(self.camtop_lineedit1.text())
        gainmax = self.camtop.Gain.GetMax()
        gainmin = self.camtop.Gain.GetMin()
        if (gain > gainmax):
            gain = gainmax
        if (gain < gainmin):
            gain = gainmin
        self.camtop.Gain.SetValue(gain)
        self.printMsg('Top camera gain set to '+str(gain), self.log)

    def setGainHor(self):
        gain = float(self.camhor_lineedit1.text())
        gainmax = self.camhor.Gain.GetMax()
        gainmin = self.camhor.Gain.GetMin()
        if (gain > gainmax):
            gain = gainmax
        if (gain < gainmin):
            gain = gainmin
        self.camhor.Gain.SetValue(gain)
        self.printMsg('Horizontal camera gain set to ' + str(gain), self.log)

    def setGammaTop(self):
        gamma = float(self.camtop_lineedit2.text())
        self.camtop.Gamma.SetValue(gamma)
        self.printMsg('Top camera gamma set to ' + str(gamma), self.log)

    def setGammaHor(self):
        gamma = float(self.camhor_lineedit2.text())
        self.camhor.Gamma.SetValue(gamma) 
        self.printMsg('Horizontal camera gamma set to ' + str(gamma), self.log)

    def setExpTimeTop(self):
        exptime = float(self.camtop_lineedit3.text())
        self.camtop.ExposureTime.SetValue(exptime) 
        self.printMsg('Exposure time set to ' + str(exptime), self.log)

    def setExpTimeHor(self):
        exptime = float(self.camhor_lineedit3.text())
        self.camhor.ExposureTime.SetValue(exptime)
        self.printMsg('Exposure time set to ' + str(exptime), self.log)

    def setColormap(self):
        cmap = self.cam_combobox1.currentText()
        self.cmap = cmap
        self.plotPictures()
        self.printMsg('Colormap updated to '+cmap, self.log)

    def initArduino(self):
        self.hdr_button1.setEnabled(False)
        self.hdr_button1.setText('Initializing...')
        time.sleep(0.01)    
        ports = listports.comports()
        self.foundArduino = False
        for port in ports:
            if port.serial_number == "36171C2D36323632F6BC33334B572F53":
                comport = port.device
                self.foundArduino = True
                time.sleep(3)
        if self.foundArduino:
            self.printMsg('Arduino found at '+comport, self.log)
        else:
            self.printMsg('Arduino not found!', self.log)

        with serial.Serial(comport, baudrate = 115200, timeout = 2) as ser:
            if ser.is_open:
                ser.close()

        self.ser = serial.Serial(comport,baudrate = 115200, timeout = 2)
        self.hdr_button1.setText('Arduino initialized')
        self.printMsg('PC-Arduino communication established', self.log)

    def moveLeft(self):
        if self.foundArduino:
            self.ser.write(b'L')
            arduinoReply = self.ser.readline().decode('ascii').rstrip()
            if arduinoReply == "moving left":
                self.isStepperRunning = True
                self.stepperDirection = 'left'
                self.printMsg('Carriage moving left', self.log)
            else:
                self.printMsg('Error', self.log)
        else:
            print('Connect and initialize Arduino first!')

    def moveRight(self):
        if self.foundArduino:
            self.ser.write(b'R')
            arduinoReply = self.ser.readline().decode('ascii').rstrip()
            if arduinoReply == "moving right":
                self.isStepperRunning = True
                self.stepperDirection = 'right'
                self.printMsg('Carriage moving right', self.log)
            else:
                self.printMsg('Error', self.log)
        else:
            print('Connect and initialize Arduino first!')

    def stopStepper(self):
        if self.isStepperRunning:
            self.ser.write(b'S')
            arduinoReply = self.ser.readline().decode('ascii').rstrip()
            if arduinoReply == "Stepper stopped":
                self.isStepperRunning = False
                self.printMsg('Carriage stopped', self.log)

    def setFrequency(self):
        speed = float(self.hdr_lineedit1.text())    # speed in meters/year
        speed_ms = speed/(365*24*3600)              # speed in meters/second
        self.frequency = speed_ms*self.gearratio*self.microstep/self.lead
        if self.foundArduino:
            self.ser.write(b'F')
            arduinoReply = self.ser.readline().decode('ascii').rstrip()
            if arduinoReply == 'F':
                self.ser.write(f"{self.frequency}\n".encode('ascii'))
                self.printMsg('Speed set to '+str(speed)+' meters/year', self.log)

    def plotData(self):
        if self.it==2:
            self.line1, = self.hdr_ax1.plot(self.tvec, self.hpos,'b-')
            self.line2, = self.hdr_ax2.plot(self.tvec, self.vpos,'b-')
            self.line3, = self.hdr_ax3.plot(self.tvec, self.curr,'b-')
            self.hdr_canvas.draw()
        elif self.it>2:
            self.line1.set_data(self.tvec, self.hpos)
            self.line2.set_data(self.tvec, self.vpos)
            self.line3.set_data(self.tvec, self.curr)
            self.hdr_ax1.set_xlim(self.tvec[0], self.tvec[-1])
            self.hdr_ax2.set_xlim(self.tvec[0], self.tvec[-1])
            self.hdr_ax3.set_xlim(self.tvec[0], self.tvec[-1])
            self.hdr_ax1.set_ylim(np.floor(min(self.hpos)), np.ceil(max(self.hpos)))
            self.hdr_ax2.set_ylim(np.floor(min(self.vpos)), np.ceil(max(self.vpos)))
            self.hdr_ax3.set_ylim(np.floor(min(self.curr)), np.ceil(max(self.curr)))
            self.hdr_canvas.draw()            

    def readData(self):
        if self.foundArduino:
            self.ser.write(b'D')
            arduinoReply = self.ser.readline().decode('ascii').rstrip().split(",")
            self.hpos.append(float(arduinoReply[0]))
            self.vpos.append(float(arduinoReply[1]))
            self.curr.append(float(arduinoReply[2]))
            self.tvec.append(self.it)
            self.it += 1
            if len(self.hpos)>self.N:
                self.hpos.pop(0)
                self.vpos.pop(0)
                self.curr.pop(0)
                self.tvec.pop(0)
            self.plotData()
            if self.it == 1:
                self.t0 = time.time()
                t_elapsed = 0
            else:
                t_elapsed = time.time() - self.t0
            self.dat.write("{:.3f}, ".format(t_elapsed))
            self.dat.write("{:.4f}, {:.4f}, {:.4f}".format(self.hpos[-1], self.vpos[-1], self.curr[-1])+'\n')

    def dataRecordingTask(self):
        schedule.every(1).seconds.do(self.readData)
        while(self.isRecordingData):
            schedule.run_pending()
            time.sleep(.05)

    def startDataRecording(self): 
        self.isRecordingData = True
        self.hdr_button5.setEnabled(False)
        self.hdr_button5.setText('Data recording in progress...')

        dataWorker = Worker(self.dataRecordingTask)
        dataWorker.signals.finished.connect(self.onDataRecordingFinished)

        self.thread_pool.start(dataWorker)
        self.printMsg('Data recording started', self.log)

    def stopDataRecording(self):
        self.isRecordingData = False
        self.printMsg('Data recording finished', self.log)
    def onDataRecordingFinished(self):
        self.hdr_button5.setEnabled(True)
        self.hdr_button5.setText('Start data recording')

    def savePictures(self):
        self.printMsg('Image recording started', self.log)
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

    def startPictureRecording(self): 
        self.img1 = py.PylonImage()
        self.img2 = py.PylonImage()

        self.camtop.AcquisitionFrameRateEnable.SetValue(True)
        self.camtop.AcquisitionFrameRate.SetValue(1.0)
        self.camhor.AcquisitionFrameRateEnable.SetValue(True)
        self.camhor.AcquisitionFrameRate.SetValue(1.0)

        self.exe_button1.setEnabled(False)
        self.exe_button1.setText('Image recording in progress...')

        pictureWorker = Worker(self.savePictures)
        pictureWorker.signals.finished.connect(self.onPictureRecordingFinished)

        self.thread_pool.start(pictureWorker)

    def stopPictureRecording(self):
        self.camtop.StopGrabbing()
        self.camhor.StopGrabbing()   

    def onPictureRecordingFinished(self):
        self.exe_button1.setEnabled(True)
        self.exe_button1.setText('Start recording')

    def closeUI(self):
        if self.camtop is not None:
            self.camtop.Close()
            self.camhor.Close()
        if self.ser is not None:
            self.ser.close()
        self.printMsg('software closed', self.log)
        self.log.close()
        self.dat.close() 
        self.close()
#============================================================================================
# EXECUTE SCRIPT
#--------------------------------------------------------------------------------------------
app = QApplication()
window = MainWindow()
window.showMaximized()
app.exec()