from math import pi, sin, cos

from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight
from panda3d.core import TransparencyAttrib
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import WindowProperties
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox, CollisionRay, CollisionHandlerQueue
from panda3d.core import Lens, OrthographicLens
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
from panda3d.core import WindowProperties
from panda3d.core import ClockObject
from panda3d.core import Camera
from panda3d.core import CollisionNode, CollisionBox, CollisionTraverser, CollisionHandlerQueue, BitMask32, CollisionHandlerFloor
from direct.gui.DirectGui import *

def degToRad(degrees):
    return degrees * (pi / 180.0)


class MyGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.selectedBlockType = 'grass'
        self.currentBlockName = 'balaxis bloki'

        self.clock = ClockObject.getGlobalClock()

        # Set the desired frame rate
        desired_frame_rate = 30  # Adjust this value to your desired frame rate
        self.clock.setMode(ClockObject.MLimited)
        self.clock.setFrameRate(desired_frame_rate)

        
        self.loadModels()
        self.setupLights()
        self.generateTerrain()
        self.setupCamera()
        self.setupSkybox()
        self.captureMouse()
        self.setupControls()
        self.fullscreen()
        #self.fillBlock(18, -20, 2, -20, -20, 2, self.selectedBlockType)

        taskMgr.add(self.update, 'update')
        self.text = self.label()
        self.text2 = self.blocksPlacedLabel()
        self.setCurrentBlock(self.currentBlockName)
        self.configBlockName(self.currentBlockName)


    def update(self, task):
        dt = globalClock.getDt() # Time passed since this method was called

        playerMoveSpeed = 10

        x_movement = 0
        y_movement = 0
        z_movement = 0

        if self.keyMap['forward']:
            x_movement -= dt * playerMoveSpeed * sin(degToRad(camera.getH()))
            y_movement += dt * playerMoveSpeed * cos(degToRad(camera.getH()))
        if self.keyMap['backward']:
            x_movement += dt * playerMoveSpeed * sin(degToRad(camera.getH()))
            y_movement -= dt * playerMoveSpeed * cos(degToRad(camera.getH()))
        if self.keyMap['left']:
            x_movement -= dt * playerMoveSpeed * cos(degToRad(camera.getH()))
            y_movement -= dt * playerMoveSpeed * sin(degToRad(camera.getH()))
        if self.keyMap['right']:
            x_movement += dt * playerMoveSpeed * cos(degToRad(camera.getH()))
            y_movement += dt * playerMoveSpeed * sin(degToRad(camera.getH()))
        if self.keyMap['up']:
            z_movement += dt * playerMoveSpeed
        if self.keyMap['down']:
            z_movement -= dt * playerMoveSpeed
        if self.keyMap['inventory']:
            self.toggleInventory()
        if self.keyMap['sprint']:
            self.sprint()

        self.camera.setPos(
            camera.getX() + x_movement,
            camera.getY() + y_movement,
            camera.getZ() + z_movement,
        )

        if self.cameraSwingActivated:
            md = self.win.getPointer(0)
            mouseX = md.getX()
            mouseY = md.getY()

            mouseChangeX = mouseX - self.lastMouseX
            mouseChangeY = mouseY - self.lastMouseY

            self.cameraSwingFactor = 10 # Sensitivity of mouse

            currentH = self.camera.getH()
            currentP = self.camera.getP()

            self.camera.setHpr(
                currentH - mouseChangeX * dt * self.cameraSwingFactor,
                min(90, max(-90, currentP - mouseChangeY * dt * self.cameraSwingFactor)),
                0
            )

            self.lastMouseX = mouseX
            self.lastMouseY = mouseY


        return task.cont
    
    inventoryVisible = False

    blocksBroken = 0
    blocksPlaced = 0

    fillBlockFirst = False
    fillBlockLast = False
    fillCounter = 0

    firstBlockPos = []
    lastBlockPos = []
    
    def setupControls(self):
        self.keyMap = {
            "forward": False,
            "backward": False,
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "inventory": False,
            "sprint": False,
        }

        self.accept('escape', self.releaseMouse)
        self.accept('mouse1', self.handleLeftClick)
        self.accept('mouse3', self.placeBlock)

        self.accept('w', self.updateKeyMap, ['forward', True])
        self.accept('w-up', self.updateKeyMap, ['forward', False])
        self.accept('a', self.updateKeyMap, ['left', True])
        self.accept('a-up', self.updateKeyMap, ['left', False])
        self.accept('s', self.updateKeyMap, ['backward', True])
        self.accept('s-up', self.updateKeyMap, ['backward', False])
        self.accept('d', self.updateKeyMap, ['right', True])
        self.accept('d-up', self.updateKeyMap, ['right', False])
        self.accept('space', self.updateKeyMap, ['up', True])
        self.accept('space-up', self.updateKeyMap, ['up', False])
        self.accept('lshift', self.updateKeyMap, ['down', True])
        self.accept('lshift-up', self.updateKeyMap, ['down', False])
        self.accept('i', self.updateKeyMap, ['inventory', True])
        self.accept('i-up', self.updateKeyMap, ['inventory', False])

        self.accept('1', self.setSelectedBlockType, ['grass'])
        self.accept('2', self.setSelectedBlockType, ['dirt'])
        self.accept('3', self.setSelectedBlockType, ['sand'])
        self.accept('4', self.setSelectedBlockType, ['stone'])

        self.accept('e', self.updateKeyMap, ['sprint', True])
        self.accept('e-up', self.updateKeyMap, ['sprint', False])

        self.accept('control-1', self.setFillBlockStarter)

    def setFillBlockStarter(self):
        self.fillBlockFirst = True

    def sprint(self):
        self.playerMoveSpeed = 25

    def setSelectedBlockType(self, type):
        self.selectedBlockType = type
        self.configBlockName(self.selectedBlockType)

    def handleLeftClick(self):
        self.captureMouse()
        self.removeBlock()

    def removeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)

            hitNodePath = rayHit.getIntoNodePath()
            hitObject = hitNodePath.getPythonTag('owner')
            distanceFromPlayer = hitObject.getDistance(self.camera)

            if distanceFromPlayer < 12:
                hitNodePath.clearPythonTag('owner')
                hitObject.removeNode() # Removes block
                self.blocksBroken += 1
                self.updateBlockCount()

    def placeBlock(self):
        if self.rayQueue.getNumEntries() > 0:
            self.rayQueue.sortEntries()
            rayHit = self.rayQueue.getEntry(0)
            hitNodePath = rayHit.getIntoNodePath()
            normal = rayHit.getSurfaceNormal(hitNodePath) # Gets top of the block (Surface)

            hitObject = hitNodePath.getPythonTag('owner')
            distanceFromPlayer = hitObject.getDistance(self.camera)

            if distanceFromPlayer < 12:
                hitBlockPos = hitObject.getPos() # Block player clicked on
                newBlockPos = hitBlockPos + normal * 2 # Default length of block is 2 & Gives us new position

                if self.fillBlockFirst:
                    self.createNewBlock(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)
                    self.blocksPlaced += 1
                    self.fillCounter += 1

                    self.firstBlockPos.append(newBlockPos.x)
                    self.firstBlockPos.append(newBlockPos.y)
                    self.firstBlockPos.append(newBlockPos.z)

                    self.fillBlockLast = True

                    self.updateBlockCount()
                    self.getBlockPos(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)

                if self.fillBlockFirst and self.fillBlockLast:
                    self.createNewBlock(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)
                    self.blocksPlaced += 1
                    self.fillCounter += 1

                    self.lastBlockPos.append(newBlockPos.x)
                    self.lastBlockPos.append(newBlockPos.y) 
                    self.lastBlockPos.append(newBlockPos.z)

                    self.proceedFill()

                    self.fillBlockLast = False
                    self.fillBlockFirst = False

                    self.updateBlockCount()
                    self.getBlockPos(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)

                else:
                    self.createNewBlock(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)
                    self.blocksPlaced += 1
                    self.fillCounter += 1
                    self.updateBlockCount()
                    self.getBlockPos(newBlockPos.x, newBlockPos.y, newBlockPos.z, self.selectedBlockType)

    def proceedFill(self):
        x1 = self.firstBlockPos[0]
        y1 = self.firstBlockPos[1]
        z1 = self.firstBlockPos[2]

        x2 = self.lastBlockPos[0]
        y2 = self.lastBlockPos[1]
        z2 = self.lastBlockPos[2]

        block_type = self.selectedBlockType

        diff = int(abs(self.firstBlockPos[0] - self.lastBlockPos[0]))
        start = int(self.firstBlockPos[0] if self.firstBlockPos[0] < self.lastBlockPos[0] else self.lastBlockPos[0])

        if x1 == x2 and y1 == y2:
            for i in range(start, start + diff + 1, 2):
                self.createNewBlock(x1, y1, i, block_type)
                
            print("Filled in Y")
        elif x1 == x2 and z1 == z2:
            for j in range(start, start + diff + 1, 2):
                self.createNewBlock(x1, j, z1, block_type)

            print("Filled in Z")
        elif y1 == y2 and z1 == z2:
            for k in range(start, start + diff + 1, 2):
                self.createNewBlock(k, y1, z1, block_type)

            print("Filled in X")
        else:
            print("Cannot establish connection between two blocks. Try different coordinates.")

    def updateBlockCount(self):
        self.text.setText("motexili bloki: "+str(self.blocksBroken))
        self.text2.setText("dadebuli bloki: "+str(self.blocksPlaced))

    def label(self):
        text = TextNode('node name')
        font = loader.loadFont('balavmtavr.ttf')
        text.setText("motexili bloki: 0")
        text.setFont(font)
        textNodePath = aspect2d.attachNewNode(text)
        textNodePath.setScale(0.07)
        textNodePath.setPos(-1.6, 0, -0.9)

        return text
    
    def blocksPlacedLabel(self):
        text2 = TextNode('blocks placed')
        font = loader.loadFont('balavmtavr.ttf')
        text2.setText("dadebuli bloki: 0")
        text2.setFont(font)
        textNodePath2 = aspect2d.attachNewNode(text2)
        textNodePath2.setScale(0.07)
        textNodePath2.setPos(-1.6, 0, -0.8)

        return text2
    
    def configBlockName(self, selectedBlockType):
        if self.selectedBlockType == 'grass':
            self.currentBlockName = 'balaxis bloki'
        elif self.selectedBlockType == 'dirt':
            self.currentBlockName = 'miwis bloki'
        elif self.selectedBlockType == 'sand':
            self.currentBlockName = 'qviSis bloki'
        elif self.selectedBlockType == 'stone':
            self.currentBlockName = 'qvis bloki'

        self.setBlockName(self.currentBlockName)


    currentBlock = TextNode('current block')

    def setBlockName(self, currentBlockName):
        self.currentBlock.setText(currentBlockName)

    def setCurrentBlock(self, currentBlockName):
        font = loader.loadFont('balavmtavr.ttf')
        self.currentBlock.setText(currentBlockName)
        self.currentBlock.setFont(font)
        currentBlockNodePath = aspect2d.attachNewNode(self.currentBlock)
        currentBlockNodePath.setScale(0.09)
        currentBlockNodePath.setPos(0.85, 0, -0.8)

    def getBlockPos(self, x, y, z, type):
        print(f"X({x})")
        print(f"Y({y})")
        print(f"Z({z})")
        print(f"Block Type({type})")
        print("______________________")

            
    def fillBlock(self, x1, y1, z1, x2, y2, z2, block_type):
        if x1 == x2 and y1 == y2:
            for i in range(min(z1, z2), max(z1, z2) + 1, 2):
                self.createNewBlock(x1, y1, i, block_type)
        elif x1 == x2 and z1 == z2:
            for j in range(min(y1, y2), max(y1, y2) + 1, 2):
                self.createNewBlock(x1, j, z1, block_type)
        elif y1 == y2 and z1 == z2:
            for k in range(min(x1, x2), max(x1, x2) + 1, 2):
                self.createNewBlock(k, y1, z1, block_type)
        else:
            print("Cannot establish connection between two blocks. Try different coordinates.")


    def autoBlock(self):
        self.createNewBlock(2, 0, 2, 'grass')
        print("Block placed automatically")

    def updateKeyMap(self, key, value):
        self.keyMap[key] = value

    def captureMouse(self):
        self.cameraSwingActivated = True

        md = self.win.getPointer(0)
        self.lastMouseX = md.getX()
        self.lastMouseY = md.getY()

        properties = WindowProperties()
        properties.setCursorHidden(True)
        properties.setMouseMode(WindowProperties.M_relative)
        # properties.setMouseMode(WindowProperties.M_confined)
        self.win.requestProperties(properties)
    
    def releaseMouse(self):
        self.cameraSwingActivated = False

        properties = WindowProperties()
        properties.setCursorHidden(False)
        properties.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(properties)

    def toggleInventory(self):
        if self.inventoryVisible:
            self.hideInventory()
        else:
            self.showInventory()

    def hideInventory(self):
        if hasattr(self, 'inventory'):
            self.inventory.removeNode()
            del self.inventory
            self.inventoryVisible = False
            print("Inventory turned off.")

    def showInventory(self):
        inventory = OnscreenImage(
            image = 'models/custom/textures/inventory.png',
            pos = (0, 0, 0),
            scale = 0.75,
        )
        inventory.setTransparency(TransparencyAttrib.MAlpha)
        self.inventoryVisible = True
        print("Inventory Is visible now.")

    def setupCamera(self):
        self.disable_mouse()

        #lens = OrthographicLens()
        #lens.setFilmSize(10, 15)
        #base.cam.node().setLens(lens)

        self.camera.setPos(0, 0, 5) # z 3 up
        self.camLens.setFov(90)

        crosshairs = OnscreenImage(
            image = 'assets/crosshairs.png',
            pos = (0, 0, 0),
            scale = 0.05,
        )
        crosshairs.setTransparency(TransparencyAttrib.MAlpha)

        self.cTrav = CollisionTraverser()
        ray = CollisionRay()
        ray.setFromLens(self.camNode, (0, 0))
        rayNode = CollisionNode('line-of-sight')
        rayNode.addSolid(ray)
        rayNodePath = self.camera.attachNewNode(rayNode)
        self.rayQueue = CollisionHandlerQueue()
        self.cTrav.addCollider(rayNodePath, self.rayQueue)

    def setupSkybox(self):
        skybox = loader.loadModel('assets/skybox/skybox.egg')
        skybox.setScale(500)
        skybox.setBin('background', 1)
        skybox.setDepthWrite(0)
        skybox.setLightOff()
        skybox.reparentTo(render)

    def generateTerrain(self):
        for z in range(10):
            for y in range(20):
                for x in range(20):
                        if z == 0:
                        # Place grass blocks on the top layer
                            self.createNewBlock(x * 2 - 20, y * 2 - 20, -z * 2, 'grass')
                        elif z < 3:
                        # Place dirt blocks below the top layer
                            self.createNewBlock(x * 2 - 20, y * 2 - 20, -z * 2, 'dirt')
                        else:
                        # Place stone blocks deeper below the surface
                            self.createNewBlock(x * 2 - 20, y * 2 - 20, -z * 2, 'stone')


    def createNewBlock(self, x, y, z, type):
        newBlockNode = render.attachNewNode('new block-placeholder')
        newBlockNode.setPos(x, y, z)

        if type == 'grass':
            self.grassBlock.instanceTo(newBlockNode)
        elif type == 'dirt':
            self.dirtBlock.instanceTo(newBlockNode)
        elif type == 'stone':
            self.stoneBlock.instanceTo(newBlockNode)
        elif type == 'sand':
            self.sandBlock.instanceTo(newBlockNode)

        blockSolid = CollisionBox((-1, -1, -1), (1, 1, 1))
        blockNode = CollisionNode('block-collision-node')
        blockNode.addSolid(blockSolid)
        collider = newBlockNode.attachNewNode(blockNode)
        collider.setPythonTag('owner', newBlockNode)


    def loadModels(self):
        self.grassBlock = loader.loadModel('assets/grass-block.glb')
        self.dirtBlock = loader.loadModel('assets/dirt-block.glb')
        self.stoneBlock = loader.loadModel('assets/stone-block.glb')
        self.sandBlock = loader.loadModel('assets/sand-block.glb')


    def setupLights(self):
        mainLight = DirectionalLight('main light')
        mainLightNodePath = render.attachNewNode(mainLight)
        mainLightNodePath.setHpr(30, -60, 0)
        render.setLight(mainLightNodePath)

        ambientLight = AmbientLight('ambient light')
        ambientLight.setColor((1, 1, 1, 1))
        ambientLightNodePath = render.attachNewNode(ambientLight)
        render.setLight(ambientLightNodePath)

    def fullscreen(self):
        width = 1280
        height = 720

        # Create a WindowProperties object and set the resolution
        win_props = WindowProperties()
        win_props.setSize(width, height)

        # Request the window to update its properties with the new resolution
        base.win.requestProperties(win_props)

        properties = WindowProperties()
        properties.setFullscreen(True)
        self.win.requestProperties(properties)


game = MyGame()
game.run()