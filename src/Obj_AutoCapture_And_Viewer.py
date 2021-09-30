import glfw
import OpenGL.GL as gl
import OpenGL.GLU as glu
import numpy as np
import ctypes
import time
import datetime
from PIL import Image

mode = 0 # [0] User Mode [1] Turn Table Mode
timeModeSet = time.time()
curTime = time.time()
prevTime = time.time()
namedCnt = 0
saveImgCnt = 0

gCamAng = 0.
gCamHeight = 3.
gCenterHeight = 1.
distanceFromOrigin = 50
dropped = False
gVertexArraySeparate = np.zeros((3, 3))

def key_callback(window, key, scancode, action, mods):
    global mode, timeModeSet, namedCnt, gCamAng, gCamHeight, gCenterHeight, distanceFromOrigin
    if action==glfw.PRESS or action==glfw.REPEAT:

        if key==glfw.KEY_LEFT: # CCW
            gCamAng += np.radians(-10%360)
        elif key==glfw.KEY_RIGHT: # CW
            gCamAng += np.radians(10%360)
        elif key==glfw.KEY_UP: # Up
            if gCamHeight < 9:
                gCamHeight += .1
        elif key==glfw.KEY_DOWN: # Down
            if gCamHeight > -9:
                gCamHeight -= .1
        
        elif key==glfw.KEY_1: # normal
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        elif key==glfw.KEY_2: # wire frame
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)

        elif key==glfw.KEY_D: # Zoom In
            if distanceFromOrigin > 0:
                distanceFromOrigin -= 1
        elif key==glfw.KEY_A: # Zoom Out
            if distanceFromOrigin < 180:
                distanceFromOrigin +=1

        elif key==glfw.KEY_W: # Center Up
            if gCenterHeight < 9:
                gCenterHeight += .1
        elif key==glfw.KEY_S: # Center Down
            if gCenterHeight > -9:
                gCenterHeight -= .1

        elif key==glfw.KEY_R:
            gCamAng = 0.
            gCamHeight = 3.
            gCenterHeight = 1.
            distanceFromOrigin = 90

        elif key==glfw.KEY_Z: # TODO: User Mode
            mode = 0
            print('Set User Mode')
        elif key==glfw.KEY_X: # TODO: Turn Table Mode
            mode = 1
            timeModeSet = time.time()
            namedCnt = 0
            print('Set Turn Table Mode')

def framebuffer_size_callback(window, width, height):
    gl.glViewport(0, 0, width, height)

def drop_callback(window, paths):
    global dropped, gVertexArraySeparate
    vertices = None
    normals = None
    faces = None
    numberOfFacesWith3Vertices = 0
    numberOfFacesWith4Vertices = 0
    numberOfFacesWithMoreThan4Vertices = 0
    dropped = True
    fileName = paths[0].split('\\')[-1]

    if(paths[0].split('.')[1].lower() != "obj"):
        print("Invalid File\nPlease provide an .obj file")
        return

    # parsing
    with open(paths[0]) as f:
        lines = f.readlines()
        vStrings = [x.strip('v') for x in lines if x.startswith('v ')]
        vertices = convertVertices(vStrings)

        if np.amax(vertices) <= 1.2:
            vertices /= np.amax(vertices)
        else:
            vertices /= np.amax(vertices)/2
        vnStrings = [x.strip('vn') for x in lines if x.startswith('vn')]

        if not vnStrings: #if There is no normal vectors in the obj file then compute them
            normals = fillNormalsArray(vertices, len(vStrings))
        else:
            normals = convertVertices(vnStrings)
        faces = [x.strip('f') for x in lines if x.startswith('f')]
    
    for face in faces: 
        if len(face.split()) == 3:
            numberOfFacesWith3Vertices +=1
        elif len(face.split()) == 4:
            numberOfFacesWith4Vertices +=1
        else:
            numberOfFacesWithMoreThan4Vertices +=1
    
    print("File name:",fileName,"\nTotal number of faces:", len(faces),
        "\nNumber of faces with 3 vertices:",numberOfFacesWith3Vertices, 
        "\nNumber of faces with 4 vertices:",numberOfFacesWith4Vertices,
        "\nNumber of faces with more than 4 vertices:",numberOfFacesWithMoreThan4Vertices)
    
    if(numberOfFacesWith4Vertices > 0 or numberOfFacesWithMoreThan4Vertices > 0):
        faces = triangulate(faces)
    gVertexArraySeparate = createVertexArraySeparate(faces, normals, vertices)

def fillNormalsArray(vertices, numberOfVertices):
    normals = np.zeros((numberOfVertices, 3))
    i = 0

    for vertice in vertices:
        normals[i] = normalized(vertice)
        i +=1
    return normals

def normalized(v):
    l2norm = np.sqrt(np.dot(v, v))
    return 1/l2norm * np.array(v)

def convertVertices(verticesStrings):
    v = np.zeros((len(verticesStrings), 3))
    i = 0

    for vertice in verticesStrings:
        j = 0
        for t in vertice.split():
            try:
                v[i][j] = (float(t))
            except ValueError:
                pass
            j+=1
        i+=1
    return v

def triangulate(faces):
    facesList = []
    nPolygons = []

    for face in faces:
        if(len(face.split())>=4):
            nPolygons.append(face)
        else:
            facesList.append(face)

    for face in nPolygons:
        for i in range(1, len(face.split())-1):
            seq = [str(face.split()[0]), str(face.split()[i]), str(face.split()[i+1])]
            string = ' '.join(seq)
            facesList.append(string)
    return facesList

def createVertexArraySeparate(faces, normals, vertices):
    varr = np.zeros((len(faces)*6,3), 'float32')
    i=0
    normalsIndex = 0
    verticeIndex = 0

    for face in faces:
        for f in face.split():
            if '//' in f: # f v//vn
                verticeIndex = int(f.split('//')[0])-1 
                normalsIndex = int(f.split('//')[1])-1
            elif '/' in f: 
                if len(f.split('/')) == 2: # f v/vt
                    verticeIndex = int(f.split('/')[0])-1 
                    normalsIndex = int(f.split('/')[0])-1
                else: # f v/vt/vn
                    verticeIndex = int(f.split('/')[0])-1 
                    normalsIndex = int(f.split('/')[2])-1
            else: # f v v v
                verticeIndex = int(f.split()[0])-1 
                normalsIndex = int(f.split()[0])-1

            varr[i] = normals[normalsIndex]
            varr[i+1] = vertices[verticeIndex]
            i+=2
    return varr

def render(width, height):
    global mode, timeModeSet, curTime, prevTime, namedCnt, saveImgCnt, gCamAng, gCamHeight, gCenterHeight, distanceFromOrigin, dropped, gVertexArraySeparate
    gl.glClear(gl.GL_COLOR_BUFFER_BIT|gl.GL_DEPTH_BUFFER_BIT)
    gl.glClearColor(1,1,1,0) # (r,g,b,a)

    gl.glEnable(gl.GL_DEPTH_TEST)
    gl.glEnable(gl.GL_NORMALIZE)
    gl.glMatrixMode(gl.GL_PROJECTION) # use projection matrix stack for projection transformation for correct lighting
    gl.glLoadIdentity()
    glu.gluPerspective(distanceFromOrigin, 1, 1,10)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    if mode == 0: # User Mode
        glu.gluLookAt(5*np.sin(gCamAng),gCamHeight,5*np.cos(gCamAng), 0,gCenterHeight,0, 0,1,0)
        saveImgCnt = 0
    elif mode == 1: # Turn Table Mode
        hz = 0.2 # TODO: Set rotation Hz
        timeDelta = timeModeSet - time.time()
        gCamAngDelta = timeDelta * hz * np.radians(360)
        gCamAngOutput = gCamAng + gCamAngDelta
        glu.gluLookAt(5*np.sin(gCamAngOutput),gCamHeight,5*np.cos(gCamAngOutput), 0,gCenterHeight,0, 0,1,0)

    drawFrame()
    drawLight()

    # material reflectance for each color channel
    # (r,g,b,a)
    diffuseObjectColor = (0.1,0.1,0.1,1.)
    specularObjectColor = (0.6,0.3,0.3,.5)
    gl.glMaterialfv(gl.GL_FRONT, gl.GL_AMBIENT_AND_DIFFUSE, diffuseObjectColor)
    # glMaterialfv(GL_FRONT, GL_SPECULAR, specularObjectColor)

    gl.glPushMatrix()
    if dropped is True: # When drop the obj file
        drawObject(gVertexArraySeparate)
    gl.glPopMatrix()

    if mode == 1: # Turn Table Mode
        curTime = time.time()
        if curTime - prevTime > 0.1: # TODO: Set time interval for capture screen
            now = datetime.datetime.now()
            strNow = str(datetime.date.fromtimestamp(timeModeSet)) + '_' + str(now.hour) + '-' + str(now.minute) + '-' + str(now.second)
            saveImage(strNow + '_' + str(namedCnt), width, height)
            prevTime = curTime
            namedCnt += 1
    
def drawFrame():
    gl.glBegin(gl.GL_LINES)
    # x axis (Red)
    gl.glColor3ub(255, 0, 0)
    gl.glVertex3fv(np.array([0.,0.,0.]))
    gl.glVertex3fv(np.array([1.,0.,0.]))
    # y axis (Green)
    gl.glColor3ub(0, 255, 0)
    gl.glVertex3fv(np.array([0.,0.,0.]))
    gl.glVertex3fv(np.array([0.,1.,0.]))
    # z axis (Blue)
    gl.glColor3ub(0, 0, 255)
    gl.glVertex3fv(np.array([0.,0.,0.]))
    gl.glVertex3fv(np.array([0.,0.,1.]))
    gl.glEnd()

def drawLight():
    gl.glEnable(gl.GL_LIGHTING)   #comment: no lighting

    gl.glEnable(gl.GL_LIGHT0)
    gl.glEnable(gl.GL_LIGHT1)
    gl.glEnable(gl.GL_LIGHT2)
    
    # light position
    # (x, y, z, w)
    # If the w component of the position is 0, the light is treated as a directional source.
    gl.glPushMatrix()
    lightPos0 = (1.,2.,3.,gl.GL_TRUE)
    lightPos1 = (3.,2.,1.,gl.GL_TRUE)
    lightPos2 = (2.,3.,1.,gl.GL_TRUE)

    gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, lightPos0)
    gl.glLightfv(gl.GL_LIGHT1, gl.GL_POSITION, lightPos1)
    gl.glLightfv(gl.GL_LIGHT2, gl.GL_POSITION, lightPos2)
    gl.glPopMatrix()

    # light intensity for each color channel
    # (r, g, b, a)
    ambientLightColor0 = (.1,.1,.1,1.)
    diffuseLightColor0 = (1.,1.,1.,1.)
    specularLightColor0 = (1.,1.,1.,1.)
    
    ambientLightColor1 = (.075,.075,.075,1.)
    diffuseLightColor1 = (0.75,0.75,0.75,0.75)
    specularLightColor1 = (0.75,0.75,0.75,0.75)
    
    ambientLightColor2 = (.05,.05,.05,1.)
    diffuseLightColor2 = (0.5,0.5,0.,0.5)
    specularLightColor2 = (0.5,0.5,0.,0.5)

    gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, ambientLightColor0)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, diffuseLightColor0)
    gl.glLightfv(gl.GL_LIGHT0, gl.GL_SPECULAR, specularLightColor0)
    gl.glLightfv(gl.GL_LIGHT1, gl.GL_AMBIENT, ambientLightColor1)
    gl.glLightfv(gl.GL_LIGHT1, gl.GL_DIFFUSE, diffuseLightColor1)
    gl.glLightfv(gl.GL_LIGHT1, gl.GL_SPECULAR, specularLightColor1)
    gl.glLightfv(gl.GL_LIGHT2, gl.GL_AMBIENT, ambientLightColor2)
    gl.glLightfv(gl.GL_LIGHT2, gl.GL_DIFFUSE, diffuseLightColor2)
    gl.glLightfv(gl.GL_LIGHT2, gl.GL_SPECULAR, specularLightColor2)

def drawObject(vertexArray):
    gl.glEnableClientState(gl.GL_VERTEX_ARRAY)
    gl.glEnableClientState(gl.GL_NORMAL_ARRAY)
    gl.glNormalPointer(gl.GL_FLOAT, 6*vertexArray.itemsize, vertexArray)
    gl.glVertexPointer(3, gl.GL_FLOAT, 6*vertexArray.itemsize, ctypes.c_void_p(vertexArray.ctypes.data + 3*vertexArray.itemsize))
    gl.glDrawArrays(gl.GL_TRIANGLES, 0, int(vertexArray.size/6))

def saveImage(name, width, height):
    global saveImgCnt, mode

    pixels = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
    pil_image = Image.frombytes('RGB', (width, height), pixels).transpose(Image.FLIP_TOP_BOTTOM)
    pil_image.save('image/' + name + '.png') # TODO: Set save location (recommands absolute location)
    print('image saved: ' + 'image/' + name + '.png')

    saveImgCnt += 1

    if saveImgCnt == 46:
        mode = 0

if __name__ == "__main__":
    width = 720 # TODO: Image/window size
    height = 720 # TODO: Image/window size
    if not glfw.init():
        exit()
    window = glfw.create_window(width, height,'3D Obj File Viewer', None,None)
    if not window:
        glfw.terminate()
        exit()

    glfw.make_context_current(window)
    glfw.set_key_callback(window, key_callback)
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    glfw.set_drop_callback(window, drop_callback)
    glfw.swap_interval(1)

    while not glfw.window_should_close(window):
        glfw.poll_events()
        render(width, height)
        glfw.swap_buffers(window)
    glfw.terminate()
