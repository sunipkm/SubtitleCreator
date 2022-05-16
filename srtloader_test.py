from io import TextIOWrapper
import re

class SRTData():
    def __init__(self):
        self.rawdata = []

    def loadSRT(self, stream: TextIOWrapper):
        if stream is None:
            print('LoadSRT: Stream is None')
            return
        nextLineIsTS = False
        nextLineIsData = False
        data = None
        datastr = ''
        for line in stream:
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

    def addItem(self, start: int, stop: int, text: str):
        """
        Add a new subtitle entry.

        Parameters:
            start (int): Starting position of subtitle text in milliseconds
            stop (int): Stopping position of subtitle text in milliseconds
            text (str): Subtitle text
        """
        if start < 0:
            # raise error
            return
        if stop < 0 or stop <= start:
            # raise error
            return
        text = text.strip()
        if len(text) == 0:
            return
    
        self.rawdata.append([start, stop, text])
        self.rawdata.sort(key = self.getSortKey)
        return

    def strToTstamp(self, currentStr: str) -> int:
        currentStr = currentStr.strip()
        if re.match('[0-9][0-9]:[0-9][0-9]:[0-9][0-9],[0-9][0-9][0-9]', currentStr) is None:
            # error
            print('%s is not a valid timestamp string'%(currentStr))
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
            return -1
        return out

     

srtData = SRTData()
ifile = open('Soul Food (1997).eng.srt', 'r')
srtData.loadSRT(ifile)
ifile.close()
print(len(srtData.rawdata))