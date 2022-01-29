# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 13:32:41 2020

@author: andmra2
"""

from tkinter import Tk, Canvas, NW, Button, Label, Toplevel, Entry, messagebox, LEFT,filedialog
from PIL import ImageTk, Image, ImageDraw, ImageOps, ImageFont
#from numpy import sin, arcsin
from math import atan2, pi
from os.path import isfile, isdir, join
from os import mkdir
from win32api import GetSystemMetrics
import json
from sklearn.cluster import AgglomerativeClustering, KMeans
from numpy import array, sqrt, square, mean, where, ones, append, reshape


class ImageMeasurer(object):
    
    def __init__(self, root):
        self.displayX = GetSystemMetrics(0)
        self.displayY = GetSystemMetrics(1)
        self.root = root
        self.root.geometry('%dx%d+%d+%d' % (self.displayX, self.displayY, 0, 0))
        self.root.iconbitmap('ImageMeasure.ico')
        self.root.title('ImageMeasure')
        self.canvas = Canvas(self.root, width = self.displayX, height = self.displayY-10)
        self.Bcanvas = Canvas(self.root, width = self.displayX, height = 10)
        self.filename = ""
        self.workingDir = "/"
        self.saveDir = "/measurements"
        self.PILImage = Image.new('RGB', (self.displayX,self.displayY))#Image.open(self.filename).convert('RGB')
        self.PILImageTmp = Image.new('RGB', (self.displayX,self.displayY))#Image.open(self.filename).convert('RGB')
        self.imageDraw = ImageDraw.Draw(self.PILImage)
        self.tempImage = ImageDraw.Draw(self.PILImageTmp)
        #self.tempImagePrev = ImageDraw.Draw(self.PILImageTmpPrev)
        self.root.geometry(str(self.PILImage.width)+"x"+str(self.PILImage.height)) 
        self.updateImage() 
        self.root.resizable(True, True) 
        self.lines = []
        self.lineMeas = []
        self.linePos = [0, 0]
        self.shiftV = [0, 1]
        self.updateTmp = False
        self.drawLine = False
        self.delete = False
        
        self.calibration = False
        self.scale = 1
        self.openButton = Button(self.Bcanvas, text ="Odpri sliko", command=self.openFile)
        self.openButton.pack(side=LEFT)
        self.calibrateButton = Button(self.Bcanvas, text ="Določi skalo", command=self.startCalibration)
        self.calibrateButton.pack(side=LEFT)
        self.deliteButton = Button(self.Bcanvas, text ="Pobriši meritev", command=self.deliteFun)
        self.deliteButton.pack(side=LEFT)
        self.saveButton = Button(self.Bcanvas, text ="Shrani meritve", command=self.saveFun)
        self.saveButton.pack(side=LEFT)
        self.Bcanvas.pack()
        self.canvas.pack()
        
        self.root.bind('<Motion>', self.motion)
        self.root.bind('<Button-1>', self.measure1)
        self.root.bind('<Button-3>', self.cancelMeas)


    def motion(self, event):
        
        self.mX, self.mY = event.x, event.y
        if self.updateTmp:
            self.PILImageTmp = self.PILImage.copy()
            self.tempImage = ImageDraw.Draw(self.PILImageTmp)
            if self.drawLine:
                self.calcLinePos()
                self.drawLineFun(self.tempImage)
                
            else:
                self.PILImageTmp = self.PILImage.copy()
                self.tempImage = ImageDraw.Draw(self.PILImageTmp)
                self.tempImage.line((self.lines[-1][0][0], self.lines[-1][0][1]) + (self.mX, self.mY), fill=(255,0,0,128))
            self.updateImageTmp()
        #print('{}, {}'.format(x, y))
        
    def drawLineFun(self, drawFun):
        x = self.linePos[0]
        y = self.linePos[1]
        drawFun.line((x, y) + (x+self.xShift, y+self.yShift), fill=(255,0,0,128))
        
    def saveLine(self, saveObj, saveMeas=None):
        saveObj.append([self.linePos[0], self.linePos[1]])
        saveObj.append([self.linePos[0]+self.xShift, self.linePos[1]+self.yShift])
        if saveMeas:
            saveMeas.append()
        
        
    def savePoint(self, saveObj):
        saveObj.append([self.mX, self.mY])
        
    def calShift(self):
        self.xShift = self.lines[-1][0][0] - self.lines[-1][1][0]
        self.yShift = self.lines[-1][0][1] - self.lines[-1][1][1]
        l = (self.yShift**2 + self.xShift**2)**(1/2)
        self.shiftV = [-self.yShift/l, self.xShift/l]
        
    def calcLen(self, vector):
        return (vector[0]**2+vector[1]**2)**(1/2)
        
    def calcLineAngle(self, lines=None):
        currV = self.calcVec(lines)
        currVl = self.calcLen(currV)
        if currVl == 0:
            return 1e100
        else:
            return (currV[0]*self.shiftV[0] + currV[1]*self.shiftV[1])/currVl
    
    def calcVec(self, lines=None):
        if lines is None:
            return [self.mX-self.lines[-1][1][0], self.mY - self.lines[-1][1][1]]
        else:
            return [lines[0][0] - lines[1][0], lines[0][1] - lines[1][1]]
    
    def calcProj(self):
        currV = self.calcVec()
        #print('currV:', currV)
        #print('lineAngle:', self.calcLineAngle()*180./3.14)
        #print('shiftV:', self.shiftV, (self.shiftV[0]**2+self.shiftV[1]**2)**(1/2))
        return (currV[0]**2+currV[1]**2)**(1/2)*self.calcLineAngle()#abs((self.shiftV[0]*currV[0]+self.shiftV[1]*currV[1]))*self.calcLineAngle()
    
    def calcLinePos(self):
        proj = self.calcProj()
        #print('proj:',proj)
        #print('----------------')
        self.linePos = [self.lines[-1][-1][0]+proj*self.shiftV[0], self.lines[-1][-1][1]+proj*self.shiftV[1]]
        
        
    def measure1(self, event):
        #print(self.lines)
        if not self.delete:
            if len(self.lines): # če že obstajajo meritve
                if len(self.lines[-1]) > 3: # če je zadnja meritev zaključena (uporabnik pravkar kliknil za začetek druge meritve)
                    self.lines.append([[self.mX, self.mY]])
                    self.updateTmp = True
                    self.drawLine = False
                elif len(self.lines[-1]) > 1: # če je narisana samo 1 črta (uporabnik pravkar kliknil za izris druge)
                    self.drawLineFun(self.imageDraw)
                    self.saveLine(self.lines[-1])
                    self.updateTmp = False
                    if self.calibration:
                        self.calibrateWindow(self.calcProj())
                        self.lineMeas.append(abs(self.calcProj()))
                        self.calibration = False
                    else:
                        self.lineMeas.append(abs(self.calcProj()))
                        self.drawMeasurementLine(self.lines[-1], self.lineMeas[-1])
                    #print(abs(round(self.calcProj()*self.scale,2)))
                else: # če je narisana samo 1 točka (uporabnik pravkar kliknil za izris 1. črte)
                    self.imageDraw.line((self.lines[-1][0][0], self.lines[-1][0][1]) + (self.mX, self.mY), fill=(255,0,0,128))
                    self.savePoint(self.lines[-1])
                    self.updateTmp = True
                    self.drawLine = True
                    self.calShift()
                    self.updateImage()
            else: # če meritve ne obstajajo nariši prvo točko prve meritve
                self.lines.append([[self.mX, self.mY]])
                self.updateTmp = True
        
        #print(self.lines)
        
    def drawMeasurementLine(self, line, meas):
        arrLen = 10
        textDistY = -19
        if meas*self.scale<10:
            textDistX = -14
        elif meas*self.scale<100:
            textDistX = -20
        else:
            textDistX = -28
        cosA = 0.94 #~20 stopinj
        sinA = 1 - cosA**2
        startPoint = ((line[0][0]+line[1][0])/2, (line[0][1]+line[1][1])/2)
        endPoint = ((line[2][0]+line[3][0])/2, (line[2][1]+line[3][1])/2)
        midPoint = ((startPoint[0] + endPoint[0])/2, (startPoint[1] + endPoint[1])/2)
        stPoArr = (endPoint[0] - startPoint[0], endPoint[1] - startPoint[1])
        stPoArrLen = self.calcLen(stPoArr)
        stPoArr = (stPoArr[0]/stPoArrLen, stPoArr[1]/stPoArrLen)
        enPoArr = (-stPoArr[0], -stPoArr[1])
        textPos = (int(midPoint[0] - stPoArr[1]*textDistY + stPoArr[0]*textDistX), int(midPoint[1] + stPoArr[0]*textDistY + stPoArr[1]*textDistX))
        stPoArr1 = (startPoint[0]+(cosA*stPoArr[0] - sinA*stPoArr[1])*arrLen, startPoint[1]+(sinA*stPoArr[0] + cosA*stPoArr[1])*arrLen)
        stPoArr2 = (startPoint[0]+(cosA*stPoArr[0] + sinA*stPoArr[1])*arrLen, startPoint[1]+(-sinA*stPoArr[0] + cosA*stPoArr[1])*arrLen)
        enPoArr1 = (endPoint[0]+(cosA*enPoArr[0] - sinA*enPoArr[1])*arrLen, endPoint[1]+(sinA*enPoArr[0] + cosA*enPoArr[1])*arrLen)
        enPoArr2 = (endPoint[0]+(cosA*enPoArr[0] + sinA*enPoArr[1])*arrLen, endPoint[1]+(-sinA*enPoArr[0] + cosA*enPoArr[1])*arrLen)
        self.imageDraw.line(startPoint + endPoint, fill=(255,0,0,128), width=2)
        self.imageDraw.line(startPoint + stPoArr1, fill=(255,0,0,128), width=3)
        self.imageDraw.line(startPoint + stPoArr2, fill=(255,0,0,128), width=3)
        self.imageDraw.line(endPoint + enPoArr1, fill=(255,0,0,128), width=3)
        self.imageDraw.line(endPoint + enPoArr2, fill=(255,0,0,128), width=3)
        #self.imageDraw.line(midPoint + textPos, fill=(255,0,0,128), width=1)
        txt=Image.new('L', (self.displayX,self.displayY))
        d = ImageDraw.Draw(txt)
        #d.line((500,0) + (500,1000), fill=255, width=1)
        #d.line((0,500) + (1000,500), fill=255, width=1)
        font = ImageFont.truetype("arial.ttf",14)
        d.text( (int(self.displayX/2),int(self.displayY/2)), str(round(meas*self.scale,2)), fill=255, font=font)
        w=txt.rotate(atan2(-stPoArr[1], stPoArr[0])/pi*180)#,  expand=1)
        self.PILImage.paste( ImageOps.colorize(w, (0,0,0), (0,0,255)), (textPos[0]-int(self.displayX/2),textPos[1]-int(self.displayY/2)),  w)
        #self.PILImage.paste(w, (textPos[0]-500,textPos[0]-500),  w)
        self.PILImageTmp = self.PILImage.copy()
        self.tempImage = ImageDraw.Draw(self.PILImageTmp)
        #self.imageDraw.text(textPos, "10.45", fill=(255,0,0,128))
        self.updateImage()
        
    def deleteMeasByN(self, n):
        del self.lines[n]
        del self.lineMeas[n]
        self.rewriteMeasurements()
        self.updateTmp = False
        self.drawLine = False
        
    def rewriteMeasurements(self):
        self.loadImage()
        for line, meas in zip(self.lines, self.lineMeas):
            #print(line, meas)
            self.rewriteMeasurement(line, meas)
        self.PILImageTmp = self.PILImage.copy()
        self.updateImage()
            
    def rewriteMeasurement(self, line, meas):
        self.imageDraw.line(tuple(line[0]) + tuple(line[1]), fill=(255,0,0,128), width=1)
        self.imageDraw.line(tuple(line[2]) + tuple(line[3]), fill=(255,0,0,128), width=1)
        self.drawMeasurementLine(line, meas)
        #self.PILImageTmp = self.PILImage.copy()
        #self.updateImage()
        
        
    def updateImage(self):
        self.img = ImageTk.PhotoImage(self.PILImage)  
        self.canvas.create_image(0, 0, anchor=NW, image=self.img)
        
    def updateImageTmp(self):
        self.img = ImageTk.PhotoImage(self.PILImageTmp)  
        self.canvas.create_image(0, 0, anchor=NW, image=self.img)
        
    def startCalibration(self, *args):
        #print('startCal')
        del self.lines[-1]
        self.updateTmp = False
        self.drawLine = False
        self.calibration = True
    
    def calibrateWindow(self, currProj):
        
        self.currProj = currProj
        self.calW = Toplevel(self.root)
        self.calW.wm_title("Določi skalo")
        l = Label(self.calW, text="Vpiši realno vrednost meritve")
        l.pack(side="top", fill="both", expand=True)
        self.scaleEntry = Entry(self.calW)
        self.scaleEntry.pack()
        self.scaleEntry.focus_set()
        self.scaleEntry.bind('<Return>', self.closeCalW)
        OKbtn = Button(self.calW, text="Potrdi", command=self.closeCalW)
        OKbtn.pack()



    def closeCalW(self, *args):
        #try:
            length = abs(float(self.scaleEntry.get().replace(',','.')))
            self.scale = abs(length/self.currProj)
            self.calW.destroy()
            self.deleteMeasByN(-1)
#        except Exception as e:
#            print(e)
#            messagebox.showinfo( "Napaka pri vnosu", "vpisan tekst ni število")
            
    def deliteFun(self, *args):
        del self.lines[-1]
        self.updateTmp = False
        self.drawLine = False
        self.root.unbind("<Button 1>")
        self.root.bind('<Button-1>', self.deleteMeas)
        #self.root.unbind("<Button 3>")
        #self.root.bind('<Button-3>', self.measFun)
        self.delete = True
        
    def measFun(self, *args):
        self.delete = False
        self.root.unbind("<Button 1>")
        self.root.unbind("<Button 3>")
        self.root.bind('<Button-1>', self.measure1)
        self.root.bind('<Button-3>', self.cancelMeas)
        
    def deleteMeas(self, *args):
        n = None
        dist = 1000
        for i, line in enumerate(self.lines):
            if len(line) > 3:
                lineX = (line[0][0] + line[1][0] + line[2][0] + line[3][0])/4
                lineY = (line[0][1] + line[1][1] + line[2][1] + line[3][1])/4
                d = self.calcLen((lineX-self.mX, lineY-self.mY))
                if d < dist:
                    dist = d
                    n = i
        if dist < 50:
            self.deleteMeasByN(n)
            self.measFun()
            
    def cancelMeas(self, *args):
        self.updateTmp = False
        self.drawLine = False
        if not self.delete:
            if len(self.lineMeas) < len(self.lines):
                self.lineMeas.append(0)
            self.deleteMeasByN(-1)
        self.delete = False
        self.root.unbind("<Button-1>")
        self.root.bind('<Button-1>', self.measure1)

    def writeMeasFile(self, IMfile, fileName):
        if isfile(IMfile):
            with open(IMfile, 'r') as file:
                measFileCont = json.loads(file.read())
            measurements = measFileCont["measurements"]
            maxMeas = 0

            fileNames = {}
            for fileName in measurements:
                X = []
                scaled = []
                for i, lines in enumerate(measurements[fileName]["lines"]):
                    # sPoint = [(lines[0][0]+lines[1][0])/2, (lines[0][1]+lines[1][1])/2]
                    # ePoint = [(lines[2][0]+lines[3][0])/2, (lines[2][1]+lines[3][1])/2]
                    mPoint = [(lines[0][0]+lines[1][0] + lines[2][0]+lines[3][0])/4,
                              (lines[0][1] + lines[1][1] + lines[2][1]+lines[3][1])/4]
                    scaledMeas = measurements[fileName]["rawMeas"][i]*measurements[fileName]["scale"]
                    angle = self.calcLineAngle(lines)
                    #print(angle)
                    #X.append([sPoint[0], sPoint[1], ePoint[0], ePoint[1],
                    X.append([scaledMeas, mPoint[0], mPoint[1], angle])
                    scaled.append(scaledMeas)
                    #fileNames.append(fileName)
                fileNames[fileName] = [scaled, self.sortMeas(X, measFileCont, fileName)]
                if i + 1 > maxMeas:
                    maxMeas = i + 1
            with open(join(self.saveDir, 'measurements.txt'), 'w') as file:
                for fileName in fileNames:
                    file.write(fileName)
                    print("------")
                    print(fileName)
                    print('sort:', fileNames[fileName][1])
                    for i in range(maxMeas):
                        file.write('\t')
                        if i in fileNames[fileName][1]:

                            print("index:", i, fileNames[fileName][1].index(i))
                            loc = fileNames[fileName][1].index(i)
                            file.write(str(round(fileNames[fileName][0][loc], 2)))
                    file.write('\n')

    def sortMeas(self, measChar, measFileCont, fileName):
        weights = array([5, 1, 1, 3])
        sortList = [None for char in measChar]
        if "centers" in measFileCont:
            centers = array(measFileCont["centers"])
            included = measFileCont["included"]
        else:
            centers = measChar
            included = [fileName]
            with open(self.saveDir + 'measurements.im', 'w') as file:
                measFileCont["centers"] = centers
                measFileCont["included"] = included
                file.write(json.dumps(measFileCont, sort_keys=True, indent=4))
            centers = array(centers)
        if len(centers.shape) == 1:
            nItems = centers.shape[0]
            nItems = int(nItems/4)
            centers = reshape(centers, (nItems, 4))
        centersW = centers.copy()
        print(centersW)
        centersW[:, -1] = ones(len(centersW))
        errors = [sqrt(mean(square((char - centers)/centersW*weights), axis=1)) for char in array(measChar)]
        usedPos = array([], dtype="int8")
        mask = ones(len(centers), bool)
        for c in range(min(len(centers), len(measChar))):
            currMinErr = 1e10
            minErrLoc = None
            currPos = None

            for i, error in enumerate(errors):
                if sortList[i] is None:
                    if c:
                        minErr = min(error[mask])
                    else:
                        minErr = min(error)
                    if minErr < currMinErr:
                        for pos in where(error == minErr)[0]:
                            if pos not in usedPos:
                                break
                        if True:# not in usedPos:
                            currMinErr = minErr
                            minErrLoc = i
                            currPos = pos
            mask[currPos] = 0
            print(mask)
            sortList[minErrLoc] = currPos
            usedPos = append(usedPos, [currPos])
        currMax = len(centers)
        for i in range(len(sortList)):
            if sortList[i] is None:
                sortList[i] = currMax
                currMax += 1
        if fileName not in included:
            l = len(included)
            cLen = len(centers)
            sLen = len(sortList)
            for i in range(max(cLen, sLen)):
                if i < cLen:
                    if i in sortList:
                        centers[i] = (centers[i]*l + measChar[sortList.index(i)])/(l + 1)
                else:
                    centers = append(centers, [measChar[i]])

            included.append(fileName)
            measFileCont["centers"] = centers.tolist()
            measFileCont["included"] = included
            with open(self.saveDir + 'measurements.im', 'w') as file:
                file.write(json.dumps(measFileCont, sort_keys=True, indent=4))


        print('sort:', sortList)
        return sortList



            




    def writeIMFile(self, IMfile, fileName, n):
        if not isfile(IMfile):
            with open(IMfile, 'w') as file:
                measurements = {"measurements": {},}
                file.write(json.dumps(measurements, sort_keys=True, indent=4))
        else:
            with open(IMfile, 'r') as file:
                #print(file.read())
                measurements = json.loads(file.read())
        if n:
            fileName += "_" + str(n)

        measurements["measurements"][fileName] = {}
        measurements["measurements"][fileName]["scale"] = self.scale
        measurements["measurements"][fileName]["lines"] = self.lines
        measurements["measurements"][fileName]["rawMeas"] = self.lineMeas


        with open(IMfile, 'w') as file:
            file.write(json.dumps(measurements, sort_keys=True, indent=4))



    def saveFun(self, *args):
        del self.lines[-1]
        self.updateTmp = False
        self.drawLine = False
        n = self.filename.rsplit('.', 1)

        fileName = n[0].rsplit('/', 1)[1]
        # if isfile(measFile):
        #     with open(measFile, 'a') as file:
        #         self.writeMeasFile(file, fileName)
        # else:
        #     with open(measFile, 'w') as file:
        #         self.writeMeasFile(file, fileName)

        if not isdir(self.saveDir):
            mkdir(self.saveDir)
        #measFile = join(self.saveDir, "measurements.txt")
        IMFile = join(self.saveDir, "measurements.im")
        for i in range(99):
            if i:
                filename = self.saveDir + fileName + '_measure_' + str(i) + '.' + n[1]
            else:
                filename = self.saveDir + fileName + '_measure.' +n[1]
            if not isfile(filename) or i == 100:
                #self.PILImage.save(filename)
                self.writeIMFile(IMFile, fileName, i)
                self.writeMeasFile(IMFile, fileName)
                font = ImageFont.truetype("arial.ttf", 20)
                self.tempImage.text((0, 0), "Created with ImageMeasure by A. Mrak", fill=(0, 255, 0, 255), font=font)
                self.PILImageTmp.save(filename, quality=200)
                self.PILImageTmp = self.PILImage.copy()
                self.tempImage = ImageDraw.Draw(self.PILImageTmp)
                messagebox.showinfo("Obvestilo", "Datoteka shranjena kot "+filename)
                break
            
    def openFile(self, *args):
        del self.lines[-1]
        self.updateTmp = False
        self.drawLine = False
        for i in range(10):
            self.filename = filedialog.askopenfilename(initialdir = self.workingDir ,title = "Izberi sliko")#,
                                       #filetypes = (("png datoteke","*.png")("jpeg datoteke","*.jpg"),("vse datoteke","*.*")))
            self.workingDir = self.filename.rsplit('/', 1)[0]
            self.saveDir = join(self.workingDir + "/measurements/")
            if len(self.filename.split('.'))<2:
                break
            else:
                #print(self.filename.split('.')[-1].lower())
                if self.filename.split('.')[-1].lower() in ['jpg', 'png', 'jpeg']:
                    self.loadImage()
                    self.lineMeas = []
                    self.lines = []
                    self.updateImage()
                    break
                else:
                    messagebox.showinfo( "Obvestilo", "Neveljaven format datoteke")
            
    def loadImage(self):
        if self.filename:
            self.PILImage = Image.open(self.filename).convert('RGB')
            self.PILImageTmp = Image.open(self.filename).convert('RGB')
        else:
            self.PILImage = Image.new('RGB', (self.displayX,self.displayY))
            self.PILImageTmp = Image.new('RGB', (self.displayX,self.displayY))
        if self.PILImage.width/self.displayX > self.PILImage.height/self.displayY:
            if self.PILImage.width > self.displayX:
                self.PILImage = self.PILImage.resize((self.displayX, int(self.PILImage.height/self.PILImage.width*self.displayX)))
        else:
            Y = self.displayY-10
            if self.PILImage.height > Y:
                self.PILImage = self.PILImage.resize((int(self.PILImage.width/self.PILImage.height*Y), Y))
        self.imageDraw = ImageDraw.Draw(self.PILImage)
        self.tempImage = ImageDraw.Draw(self.PILImageTmp)          
            



 

#root.geometry(str(PILImage.width)+"x"+str(PILImage.height)) 



if __name__ == "__main__":
    root = Tk() 
    im = ImageMeasurer(root)
    root.mainloop() 
