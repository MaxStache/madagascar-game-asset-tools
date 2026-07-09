from direct.showbase.ShowBase import ShowBase
import formats.rwtxd as rwtxd

texture_dict = rwtxd.load("Levels/KingOfNY/2_TD_LEVEL FOLDER.txd")
text = texture_dict.findTextureByName("alex_body")
rwtxd.export_png(text, "test.png")

class Viewer(ShowBase):
    def __init__(self):
        super().__init__()

        self.disableMouse()

        self.camera.setPos(0, -10, 2)
        self.camera.lookAt(0, 0, 0)

        cube = self.loader.loadModel("models/box")
        cube.reparentTo(self.render)

app = Viewer()
app.run()