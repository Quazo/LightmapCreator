import maya.cmds as cmds
import re
from math import sqrt
from math import acos
from math import pi
import operator

class LightmapCreator():
    
    def __init__(self):
        self.title = "Lightmap Creator"
        self.name = "lightmapCreator"
        
        self.maps = {"32" : 3.2, "64" : 1.6, "128" : 0.8, "256" : 0.4, "512" : 0.2, "1024" : 0.1, "2048" : 0.05}
        
        self.createUI()
        
        
    def createUI(self):
        if cmds.window(self.name, q=True, exists=True):
            cmds.deleteUI(self.name)
        cmds.window(self.name, title=self.title, sizeable=False, mxb=False, mnb=False, toolbox=False)
        
        cmds.columnLayout("mainLayout", adj=True, rs=5, co=("both", 5), parent=self.name)
        
        cmds.separator(h=1, style="none")
        cmds.button("bCreateLightmap", label="Create Lightmap", w=100, h=30, parent="mainLayout", c=self.createLightmap)
        cmds.textFieldGrp("tTolerance", label="Arc Tolerance(DEG): ", cw=[(1, 100), (2, 60)], text="5", parent="mainLayout", annotation="Sets the tolerance between two faces. Two faces which have an normal difference of this value, are treated as looking in the same direction.")
        
        cmds.optionMenuGrp("omTexSize", label="Texture Size:            ", cw=[(1, 100), (2, 60)], annotation="Size of the texture for the object.")
        cmds.menuItem("32")
        cmds.menuItem("64")
        cmds.menuItem("128")
        cmds.menuItem("256")
        cmds.menuItem("512")
        cmds.menuItem("1024")
        cmds.menuItem("2048")
        cmds.optionMenuGrp("omTexSize", e=True, value="256")
        
        cmds.checkBox("cbDeleteHistory", l="Delete History", v=True, annotation="Delete object's history. In general in the process of creating the lightmap a lot of history is generated.")
        
        cmds.separator(h=1, style="none")
        
        cmds.showWindow(self.name)

    def createLightmap(self, *args):
               
        selection = cmds.ls(sl=True)
        if len(selection) == 0:
            return
        mesh = selection[0]
        
        if(cmds.checkBox("cbDeleteHistory", q=True, v=True) == True):
            cmds.delete(mesh, ch=True) 
        
        maxArc = cmds.textFieldGrp("tTolerance", q=True, text=True)
        if re.search('[a-zA-Z]', maxArc) != None:
            cmds.textFieldGrp("tTolerance", e=True, text="5")
        maxArc = int(cmds.textFieldGrp("tTolerance", q=True, text=True))
        
        # 1. Create a new UV Set
        if "lightmap" in cmds.polyUVSet(q=True, auv=True):
            cmds.polyUVSet(uvs="lightmap", delete=True)
        
        faceCount = cmds.polyEvaluate(mesh, f=True)
        cmds.polyUVSet(copy=True, nuv="lightmap")
        cmds.polyUVSet(mesh, cuv=True, uvs="lightmap")
    
        # 2. Cut every UV Edge
        edgeCount = cmds.polyEvaluate(mesh, e=True)
        cmds.polyMapCut(mesh + ".e[0:" + str(edgeCount - 1) + "]", cch=True, ch=False)
        
        
        cmds.progressWindow(title="Creating Lightmap...", progress=0, maxValue=faceCount+1, isInterruptable=True, status="Facecount: " + str(faceCount))
        # 3. Check if faces are connected and facing the same direction, if they do, then sew the uv edge
        i = 0
        while i < faceCount:
            if cmds.progressWindow( query=True, isCancelled=True ) :
                break
            
            face = mesh + ".f[" + str(i) + "]"
            adjacentFaces = self.getAdjacentFaces(mesh, i)
            
            normal1 = self.getFaceNormal(face)
            
            for adj in adjacentFaces:
                normal2 = self.getFaceNormal(adj)
                
                arc = self.getAngle(normal1, normal2)
                
                if arc < maxArc:
                    self.sewFaces(face, adj)
                
            cmds.progressWindow( edit=True, progress=i)
            i += 1
            
        cmds.select(mesh)
        
        # 4. unfold
        cmds.unfold(i=5000, ss=0.001, gb=False, gmb=0.5, ps=0, oa=0, us=True)
            
        # 5. layout 
        preset = self.maps[cmds.optionMenuGrp("omTexSize", q=True, value=True)]
        cmds.polyMultiLayoutUV(lm=1, sc=1, rbf=1, fr=True, l=2, ps=preset)
        
        cmds.progressWindow(endProgress=True)
        
        
    def sewFaces(self, faceA, faceB):
        cmds.select([faceA, faceB])
        cmds.polyMapSewMove((cmds.polyListComponentConversion(ff=True, te=True, internal=True)), ch=False, cch=True)
        cmds.select(d=True)
        
    def getAdjacentFaces(self, mesh, face):                
        # select face
        cmds.select(mesh + ".f[" + str(face) + "]", r=True)
        
        # convert to edges, to faces
        cmds.select(cmds.polyListComponentConversion(ff=True, te=True))
        cmds.select(cmds.polyListComponentConversion(fe=True, tf=True, border=True))
        adjacentFaces = cmds.ls(sl=True, fl=True)
        
        # deselect
        cmds.select(d=True)
        
        return adjacentFaces
            
    def getFaceNormal(self, face): 
        unparsed = cmds.polyInfo(face, fn=True)[0]
        unparsed = unparsed.partition(":")[2].partition("\n")[0]
        parsed = unparsed.split(" ", 3)
        return [parsed[1], parsed[2], parsed[3]]
    
    
    def getAngle(self, vectorA, vectorB):
        vector1 = [float(vectorA[0]), float(vectorA[1]), float(vectorA[2])]
        vector2 = [float(vectorB[0]), float(vectorB[1]), float(vectorB[2])]
        dotProduct = sum(map(operator.mul, vector1, vector2))
        
        lengthA = self.getVectorLength(vectorA)
        lengthB = self.getVectorLength(vectorB)
        
        cos = dotProduct / (lengthA * lengthB)
        
        return acos(cos) * 180 / pi
        
        
    def getVectorLength(self, vector):
        x = float(vector[0])
        y = float(vector[1])
        z = float(vector[2])
        return sqrt(x * x + y * y + z * z)
        
