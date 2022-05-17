#!/usr/bin/env python


#############################################################################
##
## Copyright (C) 2013 Riverbank Computing Limited.
## Copyright (C) 2013 Digia Plc and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################

from PyQt5.Qt import QTextOption
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel,
        QFileInfo, qFuzzyCompare, QMetaObject, QModelIndex, QObject, Qt,
        QThread, QTime, QUrl, QSize, QEvent, QCoreApplication)
from PyQt5.QtGui import QColor, qGray, QImage, QPainter, QPalette, QIcon, QKeyEvent
from PyQt5.QtMultimedia import (QAbstractVideoBuffer, QMediaContent,
        QMediaMetaData, QMediaPlayer, QMediaPlaylist, QVideoFrame, QVideoProbe)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
        QFormLayout, QHBoxLayout, QLabel, QListView, QMessageBox, QPushButton,
        QSizePolicy, QSlider, QStyle, QToolButton, QVBoxLayout, QWidget, QLineEdit, QPlainTextEdit,
        QTableWidget, QTableWidgetItem, QSplitter, QAbstractItemView, QStyledItemDelegate, QHeaderView, QFrame, QProgressBar)
from io import TextIOWrapper
import re
from inspect import currentframe

def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno


class VideoWidget(QVideoWidget):

    def __init__(self, parent=None):
        super(VideoWidget, self).__init__(parent)

        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)

        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self.setFullScreen(False)
            event.accept()
        elif event.key() == Qt.Key_Enter and event.modifiers() & Qt.Key_Alt:
            self.setFullScreen(not self.isFullScreen())
            event.accept()
        else:
            super(VideoWidget, self).keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.setFullScreen(not self.isFullScreen())
        event.accept()

class PlaylistModel(QAbstractItemModel):

    Title, ColumnCount = range(2)

    def __init__(self, parent=None):
        super(PlaylistModel, self).__init__(parent)

        self.m_playlist = None

    def rowCount(self, parent=QModelIndex()):
        return self.m_playlist.mediaCount() if self.m_playlist is not None and not parent.isValid() else 0

    def columnCount(self, parent=QModelIndex()):
        return self.ColumnCount if not parent.isValid() else 0

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column) if self.m_playlist is not None and not parent.isValid() and row >= 0 and row < self.m_playlist.mediaCount() and column >= 0 and column < self.ColumnCount else QModelIndex()

    def parent(self, child):
        return QModelIndex()

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            if index.column() == self.Title:
                location = self.m_playlist.media(index.row()).canonicalUrl()
                return QFileInfo(location.path()).fileName()

            return self.m_data[index]

        return None

    def playlist(self):
        return self.m_playlist

    def setPlaylist(self, playlist):
        if self.m_playlist is not None:
            self.m_playlist.mediaAboutToBeInserted.disconnect(
                    self.beginInsertItems)
            self.m_playlist.mediaInserted.disconnect(self.endInsertItems)
            self.m_playlist.mediaAboutToBeRemoved.disconnect(
                    self.beginRemoveItems)
            self.m_playlist.mediaRemoved.disconnect(self.endRemoveItems)
            self.m_playlist.mediaChanged.disconnect(self.changeItems)

        self.beginResetModel()
        self.m_playlist = playlist

        if self.m_playlist is not None:
            self.m_playlist.mediaAboutToBeInserted.connect(
                    self.beginInsertItems)
            self.m_playlist.mediaInserted.connect(self.endInsertItems)
            self.m_playlist.mediaAboutToBeRemoved.connect(
                    self.beginRemoveItems)
            self.m_playlist.mediaRemoved.connect(self.endRemoveItems)
            self.m_playlist.mediaChanged.connect(self.changeItems)

        self.endResetModel()

    def beginInsertItems(self, start, end):
        self.beginInsertRows(QModelIndex(), start, end)

    def endInsertItems(self):
        self.endInsertRows()

    def beginRemoveItems(self, start, end):
        self.beginRemoveRows(QModelIndex(), start, end)

    def endRemoveItems(self):
        self.endRemoveRows()

    def changeItems(self, start, end):
        self.dataChanged.emit(self.index(start, 0),
                self.index(end, self.ColumnCount))

class PlayerControls(QWidget):

    play = pyqtSignal()
    pause = pyqtSignal()
    stop = pyqtSignal()
    next = pyqtSignal()
    previous = pyqtSignal()
    changeVolume = pyqtSignal(int)
    changeMuting = pyqtSignal(bool)
    changeRate = pyqtSignal(float)

    def __init__(self, parent=None):
        super(PlayerControls, self).__init__(parent)

        self.playerState = QMediaPlayer.StoppedState
        self.playerMuted = False

        self.playButton = QToolButton(clicked=self.playClicked)
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        self.stopButton = QToolButton(clicked=self.stop)
        self.stopButton.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stopButton.setEnabled(False)

        self.nextButton = QToolButton(clicked=self.next)
        self.nextButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaSkipForward))

        self.previousButton = QToolButton(clicked=self.previous)
        self.previousButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaSkipBackward))

        self.muteButton = QToolButton(clicked=self.muteClicked)
        self.muteButton.setIcon(
                self.style().standardIcon(QStyle.SP_MediaVolume))

        self.volumeSlider = QSlider(Qt.Horizontal,
                sliderMoved=self.changeVolume)
        self.volumeSlider.setRange(0, 100)

        self.rateBox = QComboBox(activated=self.updateRate)
        self.rateBox.addItem("0.5x", 0.5)
        self.rateBox.addItem("1.0x", 1.0)
        self.rateBox.addItem("2.0x", 2.0)
        self.rateBox.setCurrentIndex(1)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stopButton)
        layout.addWidget(self.previousButton)
        layout.addWidget(self.playButton)
        layout.addWidget(self.nextButton)
        layout.addWidget(self.muteButton)
        layout.addWidget(self.volumeSlider)
        layout.addWidget(self.rateBox)
        self.setLayout(layout)

    def state(self):
        return self.playerState

    def setState(self,state):
        if state != self.playerState:
            self.playerState = state

            if state == QMediaPlayer.StoppedState:
                self.stopButton.setEnabled(False)
                self.playButton.setIcon(
                        self.style().standardIcon(QStyle.SP_MediaPlay))
            elif state == QMediaPlayer.PlayingState:
                self.stopButton.setEnabled(True)
                self.playButton.setIcon(
                        self.style().standardIcon(QStyle.SP_MediaPause))
            elif state == QMediaPlayer.PausedState:
                self.stopButton.setEnabled(True)
                self.playButton.setIcon(
                        self.style().standardIcon(QStyle.SP_MediaPlay))

    def volume(self):
        return self.volumeSlider.value()

    def setVolume(self, volume):
        self.volumeSlider.setValue(volume)

    def isMuted(self):
        return self.playerMuted

    def setMuted(self, muted):
        if muted != self.playerMuted:
            self.playerMuted = muted

            self.muteButton.setIcon(
                    self.style().standardIcon(
                            QStyle.SP_MediaVolumeMuted if muted else QStyle.SP_MediaVolume))

    def playClicked(self):
        if self.playerState in (QMediaPlayer.StoppedState, QMediaPlayer.PausedState):
            self.play.emit()
        elif self.playerState == QMediaPlayer.PlayingState:
            self.pause.emit()

    def muteClicked(self):
        self.changeMuting.emit(not self.playerMuted)

    def playbackRate(self):
        return self.rateBox.itemData(self.rateBox.currentIndex())

    def setPlaybackRate(self, rate):
        for i in range(self.rateBox.count()):
            if qFuzzyCompare(rate, self.rateBox.itemData(i)):
                self.rateBox.setCurrentIndex(i)
                return

        self.rateBox.addItem("%dx" % rate, rate)
        self.rateBox.setCurrentIndex(self.rateBox.count() - 1)

    def updateRate(self):
        self.changeRate.emit(self.playbackRate())

class DoubleSlider(QSlider):

    # create our our signal that we can connect to if necessary
    doubleValueChanged = pyqtSignal(float)

    def __init__(self, decimals=3, *args, **kargs):
        super(DoubleSlider, self).__init__( *args, **kargs)
        self._multi = 10 ** decimals

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super(DoubleSlider, self).value())/self._multi
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super(DoubleSlider, self).value()) / self._multi

    def setMinimum(self, value):
        return super(DoubleSlider, self).setMinimum(value * self._multi)

    def setMaximum(self, value):
        return super(DoubleSlider, self).setMaximum(value * self._multi)

    def setSingleStep(self, value):
        return super(DoubleSlider, self).setSingleStep(value * self._multi)

    def singleStep(self):
        return float(super(DoubleSlider, self).singleStep()) / self._multi

    def setValue(self, value):
        super(DoubleSlider, self).setValue(int(value * self._multi))

class Player(QWidget): # forward declaration
    pass

class SubDataTableWidget(QTableWidget):
    pass

class SRTData(QThread):
    """
    Create a new subtitle data storage with associated display table
    """
    progress = pyqtSignal(int)
    complete = pyqtSignal()

    def __init__(self, table: SubDataTableWidget, mainWindow: Player = None):
        super(SRTData, self).__init__()
        self.rawdata = []
        self.table = table
        self.mainWindow = mainWindow
        self.total_lines = -1
        self.current_lines = 0
        self.stream = None
        if table.columnCount() != 3:
            table.setColumnCount(3)
        self.updateDisplayTable()

    def __del__(self):
        self.wait()

    def loadSRT(self, stream: TextIOWrapper):
        if stream is None:
            raise IOError('SRTData::loadSRT(): Invalid Stream')
        self.stream = stream
    
    def run(self):
        stream = self.stream
        self.total_lines = len(stream.readlines())
        stream.seek(0, 0)
        nextLineIsTS = False
        nextLineIsData = False
        data = None
        datastr = ''
        self.current_lines = 0
        for line in stream:
            self.current_lines += 1
            self.progress.emit(int(100 * (self.current_lines / self.total_lines)))
            if nextLineIsTS and re.match('[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9] --> [0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]', line):
                data = []
                data.append(self.strToTstamp(line.split('-->')[0]))
                data.append(self.strToTstamp(line.split('-->')[1]))
                nextLineIsData = True
                nextLineIsTS = False
                datastr = ''
                continue
            elif nextLineIsData:
                if line.strip() != '':
                    datastr += line
                else:
                    data.append(datastr)
                    self.addItem(data[0], data[1], data[2])
                    data = None
                    nextLineIsData = False
            elif re.match('^[0-9]*$', line):
                nextLineIsTS = True
                continue
        stream.close()
        self.current_lines = -1
        self.complete.emit()

    def storeSRT(self, stream: TextIOWrapper):
        if stream is None:
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage('LoadSRT: Stream is None')
            return
        for idx, data in enumerate(self.rawdata):
            stream.write('%d\n'%(idx + 1))
            stream.write('%s --> %s\n'%(self.tstampToStr(data[0]), self.tstampToStr(data[1])))
            stream.write('%s\n'%(data[2]))
            stream.write('\n')
            
    def addItem(self, start: int, stop: int, text: str):
        """
        Add a new subtitle entry.

        Parameters:
            start (int): Starting position of subtitle text in milliseconds
            stop (int): Stopping position of subtitle text in milliseconds
            text (str): Subtitle text
        """
        if start < 0:
            msg = '%d is invalid start'%(start)
            print(msg)
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage(msg)
            return
        if stop < 0 or stop <= start:
            msg = '%d is invalid stop, start %d'%(stop, start)
            print(msg)
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage(msg)
            return
        text = text.strip()
        if len(text) == 0:
            return
    
        self.rawdata.append([start, stop, text])
        self.rawdata.sort(key = self.getSortKey)
        self.updateDisplayTable(True)
        return
    
    def getItem(self, index: int) -> list:
        """
        Get the subtitle data at index.
        """
        if index >= 0 and index < len(self.rawdata):
            return self.rawdata[index]
        else:
            return []

    def getNumItems(self) -> int:
        """
        Get the number of subtitle items in the store.
        """
        return len(self.rawdata)
    
    def updateDisplayTable(self, init: bool = False):
        """
        Update the associated display table.
        """
        datalen = len(self.rawdata)
        if datalen != self.table.rowCount():
            self.table.setRowCount(datalen)
        for i, data in enumerate(self.rawdata):
            data = self.rawdata[i]
            self.table.setItem(i, 0, QTableWidgetItem(self.tstampToStr(data[0]))) # start
            self.table.setItem(i, 1, QTableWidgetItem(self.tstampToStr(data[1]))) # stop
            self.table.setItem(i, 2, QTableWidgetItem(data[2])) # text
        badIndex = self.validateData()
        for idx in badIndex:
            self.table.item(idx, 0).setBackground(QColor('red'))
            self.table.item(idx, 1).setBackground(QColor('red'))
            self.table.item(idx, 2).setBackground(QColor('red'))
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        return
    
    def storeDataToStream(self, stream: TextIOWrapper):
        """
        Store data to stream.
        """
        if stream is None:
            print('Output stream is None')
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage('Output stream is None.')
            return
        badIndex = self.validateData()
        if len(badIndex) > 0:
            errStr = 'Subtitle data invalid, offending indices: '
            for idx in badIndex:
                errStr += str(idx + 1) + ','
            errStr = errStr.rstrip(',')
            print(errStr)
            return
        else:
            for idx, data in enumerate(self.rawdata):
                stream.write(self.dataToLine(idx, data))
        return

    # privates
    @staticmethod
    def tstampToStr(currentInfo: int) -> str:
        if currentInfo < 0:
            return '--:--:--,---'
        currentInfo /= 1000.0
        currentTime = QTime((int(currentInfo)//3600)%60, (int(currentInfo)//60)%60,
                    int(currentInfo)%60, int(currentInfo*1000)%1000)
        format = 'hh:mm:ss,zzz'
        return currentTime.toString(format)
    
    def strToTstamp(self, currentStr: str) -> int: 
        currentStr = currentStr.strip()
        if re.match('[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]', currentStr) is None:
            # error
            print('%s is not a valid timestamp string'%(currentStr))
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage('%s is not a valid timestamp string'%(currentStr))
            return -1
        val = int(currentStr[0:2]) * 3600 + int(currentStr[3:5]) * 60 + int(currentStr[6:8]) # hh:mm:ss to ss
        val *= 1000 # ss to ms
        val += int(currentStr[-3:])
        return val

    def getSortKey(self, val: list) -> int:
        try:
            out = val[0]
        except Exception as e:
            msg = 'Error accessing object 0 of list %s, error %s'%(str(val), str(e))
            print(msg)
            if self.mainWindow is not None:
                self.mainWindow.showErrorMessage('%s is not a valid timestamp string'%(msg))
            return -1
        return out

    def validateData(self) -> list:
        datalen = len(self.rawdata)
        retval = []
        for i in range(datalen):
            if i > 0 and self.rawdata[i][0] < self.rawdata[i - 1][1]:
                retval.append(i - 1)
                retval.append(i)
        retval = list(set(retval))
        return retval

    def dataToLine(self, idx: int, data: list) -> str:
        output = '%d\n'%(idx)
        output += '%s --> %s\n'%(self.tstampToStr(data[0]), self.tstampToStr(data[1]))
        output += '%s\n\n'%(data[2])
        return output

class Delegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        self.index = index
        self.parent = parent
        if index.column() == 2:
            return super(Delegate, self).createEditor(parent, option, index)
        else:
            return None

    def setEditorData(self, item, index):
        row = index.row()
        col = index.column()
        # print('Before: [%d, %d]: %s -> %s'%(row, col, self.parent.parent().subtitleData.rawdata[row][col], item.text()))
        if col == 2 and item.text().strip() != '' and item.text() != self.parent.parent().subtitleData.rawdata[row][col]:
            self.parent.parent().subtitleData.rawdata[row][col] = item.text()
        # print('After: [%d, %d]: %s'%(row, col, self.parent.parent().subtitleData.rawdata[row][col]))
        # self.parent.parent().subtitleData.updateDisplayTable()

class SubDataTableWidget(QTableWidget):
    def __init__(self, parent: Player, stream: TextIOWrapper = None):
        super(SubDataTableWidget, self).__init__(parent)
        self.parent = parent
        self.subtitleData = SRTData(self, parent)
        self.selectedItem = None
        self.setHorizontalHeaderLabels(['Start', 'Stop', 'Text'])
        self.resizeColumnsToContents()
        self.resizeRowsToContents()
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clicked.connect(self.subTableSelectAction)
        self.delegate = Delegate(self)
        self.setItemDelegate(self.delegate)

    def setSubtitleData(self, subtitleData: SRTData):
        self.subtitleData = subtitleData

    def keyPressEvent(self, event):
        key = event.key()
        if self.subtitleData is None:
            return
        if key == Qt.Key_Return or key == Qt.Key_Enter and self.selectedItem is not None:
            # seek to point
            row = self.selectedItem.row()
            col = self.selectedItem.column()
            if col == 2:
                # print(row, col)
                self.subtitleData.rawdata[row][col] = self.item(row, col).text()
            self.parent.player.setPosition(self.subtitleData.getItem(row)[0])
            # print(self.subtitleData.rawdata)
        elif key == Qt.Key_Delete and self.selectedItem is not None:
            # delete data
            row = self.selectedItem.row()
            print('Delete:', row)
            try:
                del self.subtitleData.rawdata[row]
            except Exception:
                pass
        else:
            super(SubDataTableWidget, self).keyPressEvent(event)   
        self.subtitleData.updateDisplayTable()

    def subTableSelectAction(self, item):
        if self.subtitleData is None:
            return
        self.selectedItem = item
        row = item.row()
        col = item.column()
        self.parent.player.pause()
        self.parent.player.setPosition(self.subtitleData.getItem(row)[0])
        print('subTableSelectAction():', row, col, self.subtitleData.rawdata[row][2]) 
        self.subtitleData.updateDisplayTable()

    def addData(self, start: int, stop: int, text: str):
        if self.subtitleData is None:
            return
        self.subtitleData.addItem(start, stop, text)

class NumpadHelper(QObject):
    def __init__(self, parent=None):
        super(NumpadHelper, self).__init__(parent)
        self.m_widgets = []

    def appendWidget(self, widget):
        self.m_widgets.append(widget)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj in self.m_widgets and event.type() == QEvent.KeyPress:
            numpad_mod = int(event.modifiers()) & (Qt.KeypadModifier)
            if event.key() == Qt.Key_5 and numpad_mod:
                # play-pause
                if self.m_widgets[0].player.state() == QMediaPlayer.PlayingState:
                    self.m_widgets[0].player.pause()
                elif self.m_widgets[0].player.state() == QMediaPlayer.PausedState or self.m_widgets[0].player.state() == QMediaPlayer.StoppedState:
                    self.m_widgets[0].player.play()
                return True
            elif event.key() == Qt.Key_4 and numpad_mod:
                self.m_widgets[0].seekBackwardMS()
                return True
            elif event.key() == Qt.Key_6 and numpad_mod:
                self.m_widgets[0].seekForwardMS()
                return True
            elif event.key() == Qt.Key_7 and numpad_mod:
                self.m_widgets[0].markSubStart()
                return True
            elif event.key() == Qt.Key_9 and numpad_mod:
                self.m_widgets[0].markSubEnd()
                return True
            elif event.key() == Qt.Key_2 and numpad_mod:
                self.m_widgets[0].addCurrentSub()
                return True
            elif event.key() == Qt.Key_1 and numpad_mod:
                return True
            elif event.key() == Qt.Key_3 and numpad_mod:
                return True
            elif event.key() == Qt.Key_8 and numpad_mod:
                return True
        return super(NumpadHelper, self).eventFilter(obj, event)

class Player(QWidget):

    fullScreenChanged = pyqtSignal(bool)

    def __init__(self, playlist, parent=None):
        super(Player, self).__init__(parent)

        self.colorDialog = None
        self.errorMessageDialog = None
        self.errorMessageTextWidget = None
        self.trackInfo = ""
        self.statusInfo = ""
        self.duration = 0
        numpadHelper = NumpadHelper(self)
        numpadHelper.appendWidget(self)

        self.subStartPos = -1
        self.subEndPos = -1

        self.loadSubProgress = None
        self.loadSubProgressBar = None

        self.player = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.player.setPlaylist(self.playlist)

        self.player.durationChanged.connect(self.durationChanged)
        self.player.positionChanged.connect(self.positionChanged)
        self.player.metaDataChanged.connect(self.metaDataChanged)
        self.player.mediaStatusChanged.connect(self.statusChanged)
        self.player.bufferStatusChanged.connect(self.bufferingProgress)
        self.player.videoAvailableChanged.connect(self.videoAvailableChanged)
        self.player.error.connect(self.displayErrorMessage)

        self.videoWidget = VideoWidget()
        self.player.setVideoOutput(self.videoWidget)
        self.videoWidget.setMinimumWidth(320)
        self.videoWidget.setMinimumHeight(180)

        self.slider = DoubleSlider(orientation = Qt.Horizontal)
        self.slider.setRange(0, round(self.player.duration()))
        self.labelDuration = QLabel()
        self.slider.sliderMoved.connect(self.seek)

        # self.labelHistogram = QLabel()
        # self.labelHistogram.setText("Histogram:")
        # self.histogram = HistogramWidget()
        # histogramLayout = QHBoxLayout()
        # histogramLayout.addWidget(self.labelHistogram)
        # histogramLayout.addWidget(self.histogram, 1)

        self.probe = QVideoProbe()
        # self.probe.videoFrameProbed.connect(self.histogram.processFrame)
        self.probe.setSource(self.player)

        openButton = QPushButton("Open", clicked=self.open)

        controls = PlayerControls()
        controls.setState(self.player.state())
        controls.setVolume(self.player.volume())
        controls.setMuted(controls.isMuted())

        controls.play.connect(self.player.play)
        controls.pause.connect(self.player.pause)
        controls.stop.connect(self.player.stop)
        controls.next.connect(self.playlist.next)
        controls.previous.connect(self.previousClicked)
        controls.changeVolume.connect(self.player.setVolume)
        controls.changeMuting.connect(self.player.setMuted)
        controls.changeRate.connect(self.player.setPlaybackRate)
        controls.stop.connect(self.videoWidget.update)

        self.player.stateChanged.connect(controls.setState)
        self.player.volumeChanged.connect(controls.setVolume)
        self.player.mutedChanged.connect(controls.setMuted)

        self.fullScreenButton = QPushButton("FullScreen")
        self.fullScreenButton.setCheckable(True)

        self.colorButton = QPushButton("Color Options...")
        self.colorButton.setEnabled(True)
        self.colorButton.clicked.connect(self.showColorDialog)

        displaySplitter = QSplitter(Qt.Horizontal)
        displaySplitter.setChildrenCollapsible(False)
        displaySplitter.addWidget(self.videoWidget)

        controlLayout = QHBoxLayout()
        controlLayout.setContentsMargins(0, 0, 0, 0)
        controlLayout.addWidget(openButton)
        controlLayout.addStretch(1)
        controlLayout.addWidget(controls)
        controlLayout.addStretch(1)
        controlLayout.addWidget(self.fullScreenButton)
        controlLayout.addWidget(self.colorButton)
        
        self.forwardTimeMs = 5
        self.backwardTimeMs = 5

        moveForwardTimeInputText = QLabel()
        moveForwardTimeInputText.setText('Forward (ms): ')

        self.moveForwardTimeInput = QLineEdit(str(self.forwardTimeMs))
        numpadHelper.appendWidget(self.moveForwardTimeInput)
        self.moveForwardTimeInput.setEnabled(True)
        self.moveForwardTimeInput.setFixedWidth(50)
        self.moveForwardTimeInput.textChanged.connect(self.getMoveTimeMS)

        moveBackwardTimeInputText = QLabel()
        moveBackwardTimeInputText.setText('Backward (ms): ')
        
        self.moveBackwardTimeInput = QLineEdit(str(self.backwardTimeMs))
        numpadHelper.appendWidget(self.moveBackwardTimeInput)
        self.moveBackwardTimeInput.setFixedWidth(50)
        self.moveBackwardTimeInput.setEnabled(True)
        self.moveBackwardTimeInput.textChanged.connect(self.getMoveTimeMS)
        

        moveForwardButton = QPushButton('Step Forward', clicked = self.seekForwardMS)
        moveForwardButton.setEnabled(True)

        moveBackwardButton = QPushButton('Step Backward', clicked = self.seekBackwardMS)
        moveBackwardButton.setEnabled(True)

        self.currentPositionText = QLabel()
        self.currentPositionText.setText('Current: 00:00.000')

        subInputBoxLabel = QLabel()
        subInputBoxLabel.setText('Subtitle Text:')

        self.subInputBox = QPlainTextEdit()
        numpadHelper.appendWidget(self.subInputBox)
        self.subInputBox.setEnabled(True)
        self.subInputBox.setWordWrapMode(QTextOption.WordWrap)
        self.subInputBox.setMaximumHeight(50)

        self.subtitleDisplayTable = SubDataTableWidget(self) #QTableWidget(1, 4)
        self.subtitleDisplayTable.setMinimumWidth(320)
        self.subtitleDisplayTable.setMinimumHeight(180)
        self.subtitleDisplayTable.setEnabled(True)

        self.subtitleDisplayTable.subtitleData.progress.connect(self.updateLoadSrtProgressBar)
        self.subtitleDisplayTable.subtitleData.complete.connect(self.closeProgressBar)

        self.srtFileName = ''

        displaySplitter.addWidget(self.subtitleDisplayTable)
        displaySplitter.setSizes([340, 340])
        displaySplitter.setMinimumHeight(180)
        displaySplitter.setStretchFactor(1, 1) # videoWidget does not resize on windowresize

        # subtitle timer stuff
        self.endTimeDeltaMs = 100

        getSubStartPos = QPushButton('Mark Start', clicked = self.markSubStart)
        getSubStartPos.setEnabled(True)
        
        getSubEndPos = QPushButton('Mark End', clicked = self.markSubEnd)
        getSubEndPos.setEnabled(True)

        self.getEndTimeDeltaMs = QLineEdit(str(self.endTimeDeltaMs))
        self.moveBackwardTimeInput.setFixedWidth(50)
        self.moveBackwardTimeInput.setEnabled(True)
        self.moveBackwardTimeInput.textChanged.connect(self.getMoveTimeMS)

        subInputLayout = QHBoxLayout()
        subInputLayout_L = QVBoxLayout()
        
        subInputLayout_LH = QHBoxLayout()
        self.subStartPosText = QLabel('--:--:--,---')
        self.subStartPosText.setFixedWidth(80)
        self.subStartPosClear = QPushButton('Clear', clicked = self.clearSubStart)
        self.subStartPosClear.setEnabled(False)
        subInputLayout_LH.addWidget(getSubStartPos)
        subInputLayout_LH.addStretch(1)
        subInputLayout_LH.addWidget(self.subStartPosText)
        subInputLayout_LH.addStretch(1)
        subInputLayout_LH.addWidget(self.subStartPosClear)
        subInputLayout_L.addLayout(subInputLayout_LH)

        subInputLayout_LH = QHBoxLayout()
        self.subEndPosText = QLabel('--:--:--,---')
        self.subEndPosText.setFixedWidth(80)
        self.subEndPosClear = QPushButton('Clear', clicked = self.clearSubEnd)
        self.subEndPosClear.setEnabled(False)
        subInputLayout_LH.addWidget(getSubEndPos)
        subInputLayout_LH.addStretch(1)
        subInputLayout_LH.addWidget(self.subEndPosText)
        subInputLayout_LH.addStretch(1)
        subInputLayout_LH.addWidget(self.subEndPosClear)
        subInputLayout_L.addLayout(subInputLayout_LH)

        # subInputLayout_LH = QHBoxLayout()
        # endTimeDeltaMsLabel = QLabel()
        # endTimeDeltaMsLabel.setText('Default Length (ms):')
        # subInputLayout_LH.addWidget(endTimeDeltaMsLabel)
        # subInputLayout_LH.addWidget(self.getEndTimeDeltaMs)
        # subInputLayout_L.addLayout(subInputLayout_LH)
        subInputLayout_LH = QHBoxLayout()
        addSubToArray = QPushButton('Add Subtitle', clicked = self.addCurrentSub)
        subInputLayout_LH.addWidget(addSubToArray)
        subInputLayout_L.addLayout(subInputLayout_LH)

        subInputLayout_LH = QHBoxLayout()
        loadSubToSys = QPushButton('Load SRT', clicked = self.loadSRT)
        loadSubToSys.setEnabled(True)
        subInputLayout_LH.addWidget(loadSubToSys)
        subInputLayout_LH.addStretch(1)
        storeSubToSys = QPushButton('Save SRT', clicked = self.storeSRT)
        storeSubToSys.setEnabled(True)
        subInputLayout_LH.addWidget(storeSubToSys)
        subInputLayout_L.addLayout(subInputLayout_LH)

        subInputLayout.addLayout(subInputLayout_L, stretch = 1)

        subInputLayout_R = QVBoxLayout()

        subInputLayout_R.addWidget(subInputBoxLabel)
        subInputLayout_R.addWidget(self.subInputBox)

        subInputLayout.addLayout(subInputLayout_R, stretch = 2)

        hSepLine = QFrame()
        hSepLine.setFrameShape(QFrame.HLine)
        hSepLine.setFrameShadow(QFrame.Sunken)

        layout = QVBoxLayout()
        layout.addWidget(displaySplitter, 2)
        hLayout = QHBoxLayout()
        hLayout.addWidget(self.slider)
        hLayout.addWidget(self.labelDuration)
        layout.addLayout(hLayout)
        layout.addLayout(controlLayout)
        # layout.addLayout(histogramLayout)

        layout.addWidget(hSepLine)
        layout.addWidget(QLabel('Stepping Tools'))

        clayout = QHBoxLayout()
        clayout.addWidget(moveForwardTimeInputText)
        clayout.addWidget(self.moveForwardTimeInput)
        clayout.addWidget(moveForwardButton)
        clayout.addStretch(1)
        clayout.addWidget(self.currentPositionText)
        clayout.addStretch(1)
        clayout.addWidget(moveBackwardTimeInputText)
        clayout.addWidget(self.moveBackwardTimeInput)
        clayout.addWidget(moveBackwardButton)
        layout.addLayout(clayout)

        hSepLine1 = QFrame()
        hSepLine1.setFrameShape(QFrame.HLine)
        hSepLine1.setFrameShadow(QFrame.Sunken)

        layout.addWidget(hSepLine1)
        layout.addWidget(QLabel('Subtitle Tools'))

        layout.addLayout(subInputLayout)

        # layout.addWidget(subInputBoxLabel)
        # layout.addWidget(self.subInputBox)

        # layout.addWidget(self.subtitleDisplayTable)

        # subtitle input window

        self.setLayout(layout)

        if not self.player.isAvailable():
            QMessageBox.warning(self, "Service not available",
                    "The QMediaPlayer object does not have a valid service.\n"
                    "Please check the media service plugins are installed.")

            controls.setEnabled(False)
            openButton.setEnabled(False)
            self.colorButton.setEnabled(False)
            self.fullScreenButton.setEnabled(False)

        self.metaDataChanged()

        self.addToPlaylist(playlist)

    def open(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Files")
        self.addToPlaylist(fileName)
    
    def subTableKeyAction(self, key):
        print(key)

    def loadSRT(self):
        srtName, _ = QFileDialog.getOpenFileName(self, "Load SRT", filter = 'SubRip (*.srt)')
        fileInfo = QFileInfo(srtName)
        if fileInfo.exists():
            ifile = open(fileInfo.absoluteFilePath(), 'r')
            self.subtitleDisplayTable.subtitleData.loadSRT(ifile)
            self.showProgressBar()
            # time.sleep(1)
            self.subtitleDisplayTable.subtitleData.start()

    def storeSRT(self):
        srtName, _ = QFileDialog.getSaveFileName(self, "Save SRT", filter = 'SubRip (*.srt)')
        fileInfo = QFileInfo(srtName)
        try:
            ofile = open(fileInfo.absoluteFilePath(), 'w')
        except Exception as e:
            self.showErrorMessage('storeSRT(): %s'%(str(e)))
            return
        self.subtitleDisplayTable.subtitleData.storeSRT(ofile)
        ofile.close()
        return

    def markSubStart(self):
        self.player.pause()
        self.subStartPos = self.player.position()
        self.subStartPosText.setText(SRTData.tstampToStr(self.subStartPos))
        self.subStartPosClear.setEnabled(True)

    def clearSubStart(self):
        self.subStartPos = -1
        self.subStartPosText.setText(SRTData.tstampToStr(self.subStartPos))
        self.subStartPosClear.setEnabled(False)


    def markSubEnd(self):
        self.player.pause()
        self.subEndPos = self.player.position()
        self.subEndPosText.setText(SRTData.tstampToStr(self.subEndPos))
        self.subEndPosClear.setEnabled(True)

    def clearSubEnd(self):
        self.subEndPos = -1
        self.subEndPosText.setText(SRTData.tstampToStr(self.subEndPos))
        self.subEndPosClear.setEnabled(False)
    
    def addCurrentSub(self):
        if self.subStartPos >= 0 and self.subEndPos > self.subStartPos:
            # get subtitle data
            subStr = self.subInputBox.toPlainText()
            subStr = subStr.strip()
            if len(subStr) > 0:
                self.subtitleDisplayTable.addData(self.subStartPos, self.subEndPos, subStr)
                self.subInputBox.setPlainText('')
                self.subStartPos = -1
                self.subEndPos = -1
                self.subStartPosText.setText(SRTData.tstampToStr(self.subStartPos))
                self.subEndPosText.setText(SRTData.tstampToStr(self.subEndPos))
        return

    def addToPlaylist(self, name):
        fileInfo = QFileInfo(name)
        if fileInfo.exists():
            url = QUrl.fromLocalFile(fileInfo.absoluteFilePath())
            self.playlist.addMedia(QMediaContent(url))
            self.setWindowTitle('Subtitle Creator: %s'%(fileInfo.absoluteFilePath().split('/')[-1].rsplit('.', maxsplit = 1)[0]))

        else:
            url = QUrl(name)
            if url.isValid():
                self.playlist.addMedia(QMediaContent(url))
                self.setWindowTitle('Subtitle Creator: %s'%(name))

    def durationChanged(self, duration):
        duration /= 1000

        self.duration = duration
        self.slider.setMaximum(duration)

    def positionChanged(self, progress):
        progress /= 1000
        # print('Position Changed:', progress)
        if not self.slider.isSliderDown():
            self.slider.setValue(progress)

        self.updateDurationInfo(progress)

    def metaDataChanged(self):
        if self.player.isMetaDataAvailable():
            self.setTrackInfo("%s - %s" % (
                    self.player.metaData(QMediaMetaData.AlbumArtist),
                    self.player.metaData(QMediaMetaData.Title)))

    def previousClicked(self):
        # Go to the previous track if we are within the first 5 seconds of
        # playback.  Otherwise, seek to the beginning.
        if self.player.position() <= 5000:
            self.playlist.previous()
        else:
            self.player.setPosition(0)

    def jump(self, index):
        if index.isValid():
            self.playlist.setCurrentIndex(index.row())
            self.player.play()

    def playlistPositionChanged(self, position):
        self.playlistView.setCurrentIndex(
                self.playlistModel.index(position, 0))

    def seek(self, seconds):
        self.player.setPosition(seconds)

    def getMoveTimeMS(self):
        try:
            val = int(self.moveForwardTimeInput.text())
            if val > 1000:
                val = 1000
            if val <= 0:
                val = 1
            self.forwardTimeMs = val
            self.moveForwardTimeInput.setText(str(val))
        except Exception:
            print('Invalid value %s'%(self.moveForwardTimeInput.text()))
        try:
            val = int(self.moveBackwardTimeInput.text())
            if val > 1000:
                val = 1000
            if val <= 0:
                val = 1
            self.backwardTimeMs = val
            self.moveBackwardTimeInput.setText(str(val))
        except Exception:
            print('Invalid value %s'%(self.moveBackwardTimeInput.text()))

        try:
            val = int(self.getEndTimeDeltaMs.text())
            if val > 120000: # 2 minutes max
                val = 120000
            if val <= 0:
                val = 10
            self.endTimeDeltaMs = val
            self.getEndTimeDeltaMs.setText(str(val))
        except Exception:
            print('Invalid value %s'%(self.getEndTimeDeltaMs.text()))

    def seekForwardMS(self):
        self.player.pause()
        self.player.setPosition(self.player.position() + self.forwardTimeMs)
    
    def seekBackwardMS(self):
        self.player.pause()
        self.player.setPosition(self.player.position() - self.backwardTimeMs)

    def statusChanged(self, status):
        self.handleCursor(status)

        if status == QMediaPlayer.LoadingMedia:
            self.setStatusInfo("Loading...")
        elif status == QMediaPlayer.StalledMedia:
            self.setStatusInfo("Media Stalled")
        elif status == QMediaPlayer.EndOfMedia:
            QApplication.alert(self)
        elif status == QMediaPlayer.InvalidMedia:
            self.displayErrorMessage()
        else:
            self.setStatusInfo("")

    def handleCursor(self, status):
        if status in (QMediaPlayer.LoadingMedia, QMediaPlayer.BufferingMedia, QMediaPlayer.StalledMedia):
            self.setCursor(Qt.BusyCursor)
        else:
            self.unsetCursor()

    def bufferingProgress(self, progress):
        self.setStatusInfo("Buffering %d%" % progress)

    def videoAvailableChanged(self, available):
        if available:
            self.fullScreenButton.clicked.connect(
                    self.videoWidget.setFullScreen)
            self.videoWidget.fullScreenChanged.connect(
                    self.fullScreenButton.setChecked)

            if self.fullScreenButton.isChecked():
                self.videoWidget.setFullScreen(True)
        else:
            self.fullScreenButton.clicked.disconnect(
                    self.videoWidget.setFullScreen)
            self.videoWidget.fullScreenChanged.disconnect(
                    self.fullScreenButton.setChecked)

            self.videoWidget.setFullScreen(False)

        self.colorButton.setEnabled(available)

    def setTrackInfo(self, info):
        self.trackInfo = info

        # if self.statusInfo != "":
        #     self.setWindowTitle("%s | %s" % (self.trackInfo, self.statusInfo))
        # else:
        #     self.setWindowTitle(self.trackInfo)

    def setStatusInfo(self, info):
        self.statusInfo = info

        # if self.statusInfo != "":
        #     self.setWindowTitle("%s | %s" % (self.trackInfo, self.statusInfo))
        # else:
        #     self.setWindowTitle(self.trackInfo)

    def displayErrorMessage(self):
        self.setStatusInfo(self.player.errorString())

    def updateDurationInfo(self, currentInfo):
        duration = self.duration
        if currentInfo or duration:
            currentTime = QTime((int(currentInfo)//3600)%60, (int(currentInfo)//60)%60,
                    int(currentInfo)%60, int(currentInfo*1000)%1000)
            totalTime = QTime((int(duration)//3600)%60, (int(duration)//60)%60,
                    int(duration)%60, int(duration*1000)%1000)

            format = 'hh:mm:ss' if duration > 3600 else 'mm:ss'
            tStr = currentTime.toString(format) + " / " + totalTime.toString(format)
            ttStr = currentTime.toString(format + '.zzz')
        else:
            tStr = ""
            ttStr = "00:00.000"

        self.labelDuration.setText(tStr)
        self.currentPositionText.setText('Current: ' + ttStr)

    def showErrorMessage(self, errorMessageText: str):
        if self.errorMessageDialog is None:
            self.errorMessageDialog = QDialog(self)
            self.errorMessageDialog.setModal(True)
            self.errorMessageTextWidget = QLabel('Error: ' + errorMessageText)
            layout = QVBoxLayout()
            button = QPushButton("Close")
            button.setFixedWidth(40)
            layout.addWidget(self.errorMessageTextWidget, alignment = Qt.AlignCenter)
            layout.addWidget(button, alignment = Qt.AlignCenter)
            self.errorMessageDialog.setLayout(layout)
            self.errorMessageDialog.setWindowTitle("Error")
            self.errorMessageDialog.setMinimumWidth(100)
            self.errorMessageDialog.setMinimumWidth(300)
            button.clicked.connect(self.errorMessageDialog.close)

        self.errorMessageTextWidget.setText('Error: ' + errorMessageText)
        self.errorMessageDialog.show()

    def showProgressBar(self):
        if self.loadSubProgress is None:
            self.loadSubProgress = QDialog(self)
            self.loadSubProgress.setModal(True)
            self.loadSubProgress.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowTitleHint)
            self.loadSubProgressBar = QProgressBar()
            self.loadSubProgressBar.setFixedWidth(250)
            self.loadSubProgressBar.setFixedHeight(20)
            self.loadSubProgressBar.setTextVisible(True)
            self.loadSubProgressBar.setAlignment(Qt.AlignCenter)
            self.loadSubProgressBar.setFormat('Loading SRT (%v %)')
            layout = QVBoxLayout()
            layout.addWidget(self.loadSubProgressBar, alignment = Qt.AlignCenter)
            self.loadSubProgress.setLayout(layout)
            self.loadSubProgress.setWindowTitle('Loading SRT...')
            self.loadSubProgress.setMinimumWidth(300)
            self.loadSubProgress.setMinimumHeight(100)

        self.loadSubProgress.show()

    
    def closeProgressBar(self):
        if self.loadSubProgress is not None:
            self.loadSubProgress.hide()

    def updateLoadSrtProgressBar(self, progress: int):
        if self.loadSubProgressBar is not None:
            self.loadSubProgressBar.setValue(progress)

    def showColorDialog(self):
        if self.colorDialog is None:
            brightnessSlider = QSlider(Qt.Horizontal)
            brightnessSlider.setRange(-100, 100)
            brightnessSlider.setValue(self.videoWidget.brightness())
            brightnessSlider.sliderMoved.connect(
                    self.videoWidget.setBrightness)
            self.videoWidget.brightnessChanged.connect(
                    brightnessSlider.setValue)

            contrastSlider = QSlider(Qt.Horizontal)
            contrastSlider.setRange(-100, 100)
            contrastSlider.setValue(self.videoWidget.contrast())
            contrastSlider.sliderMoved.connect(self.videoWidget.setContrast)
            self.videoWidget.contrastChanged.connect(contrastSlider.setValue)

            hueSlider = QSlider(Qt.Horizontal)
            hueSlider.setRange(-100, 100)
            hueSlider.setValue(self.videoWidget.hue())
            hueSlider.sliderMoved.connect(self.videoWidget.setHue)
            self.videoWidget.hueChanged.connect(hueSlider.setValue)

            saturationSlider = QSlider(Qt.Horizontal)
            saturationSlider.setRange(-100, 100)
            saturationSlider.setValue(self.videoWidget.saturation())
            saturationSlider.sliderMoved.connect(
                    self.videoWidget.setSaturation)
            self.videoWidget.saturationChanged.connect(
                    saturationSlider.setValue)

            layout = QFormLayout()
            layout.addRow("Brightness", brightnessSlider)
            layout.addRow("Contrast", contrastSlider)
            layout.addRow("Hue", hueSlider)
            layout.addRow("Saturation", saturationSlider)

            button = QPushButton("Close")
            layout.addRow(button)

            self.colorDialog = QDialog(self)
            self.colorDialog.setWindowTitle("Color Options")
            self.colorDialog.setLayout(layout)

            button.clicked.connect(self.colorDialog.close)

        self.colorDialog.show()


if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    appIcon = QIcon('mplayer.ico')
    app.setWindowIcon(appIcon)

    player = Player(sys.argv[1] if len(sys.argv) > 1 else '')
    player.setWindowTitle('Subtitle Creator: No File Opened')
    player.show()

    sys.exit(app.exec_())