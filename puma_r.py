import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Przykładowe kąty przegubów PUMA (na początek 3 dla uproszczenia)
theta = [0, 0, 0]  # stopnie
base_angle = 0
hook_angle = 30
hook_open = True

BASE_HEIGHT = 0.3  # wysokość pionowej kolumny (możesz zmieniać)

def draw_base():
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6)
    quadric = gluNewQuadric()
    glTranslatef(0, 0, 0)  # baza stoi na (0,0,0)
    gluCylinder(quadric, 0.5, 0.3, BASE_HEIGHT, 32, 8)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glTranslatef(0, 0, BASE_HEIGHT)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glPopMatrix()

def draw_arm():
    glPushMatrix()
    glTranslatef(0, 0, BASE_HEIGHT)
    glRotate(base_angle, 0, 0, 1)
    draw_link_base(length=1.3, radius=0.2, color=(0.5,0.5,0.5))
    glTranslatef(0, 0, BASE_HEIGHT+1)
    glRotatef(theta[0], 0, 1, 0)
    draw_link(length=1.0, radius=0.15, color=(1,0,0))
    glTranslatef(1.0, 0, 0)
    glRotatef(theta[1], 0, 1, 0)
    draw_link(length=1.0, radius=0.1, color=(0,1,0))
    if hook_open==True: hook_angle=30
    else: hook_angle=5
    glTranslatef(1.0, 0, 0)
    glRotatef(theta[2], 0, 0, 1)
    draw_hook(hook_angle)
    glPopMatrix()

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(4,4,5, 0,0,0, 0,0,1)  # Ustaw kamerę
    draw_base()   # Dodaj to!
    draw_arm()
    glutSwapBuffers()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(50, w/h, 0.1, 100)
    glMatrixMode(GL_MODELVIEW)

def draw_link(length=1.0, radius=0.07, color=(1,0,0)):
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    # Ustaw walec wzdłuż osi X (domyślnie idzie wzdłuż Z)
    glRotatef(90, 0, 1, 0)
    gluCylinder(quadric, radius, radius, length, 16, 4)
    # Końcówki (opcjonalnie, by były zakryte)
    gluDisk(quadric, 0, radius, 16, 1)  # początek
    glTranslatef(0, 0, length)
    gluDisk(quadric, 0, radius, 16, 1)  # koniec
    glPopMatrix()

def draw_link_base(length=1.0, radius=0.07, color=(1,0,0)):
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    # Ustaw walec wzdłuż osi X (domyślnie idzie wzdłuż Z)
    glRotatef(0, 0, 1, 0)
    gluCylinder(quadric, radius, radius, length, 16, 4)
    # Końcówki (opcjonalnie, by były zakryte)
    gluDisk(quadric, 0, radius, 16, 1)  # początek
    glTranslatef(0, 0, length)
    gluDisk(quadric, 0, radius, 16, 1)  # koniec
    glPopMatrix()

def draw_hook(opening_ang=30.0, length=0.5, radius=0.03):
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.0)
    glRotatef(opening_ang, 0, 0, 1)  # obrót w lewo
    glTranslatef(0.0, length / 2, 0.0)  # przesuń wzdłuż szczęki
    draw_link(length=length, radius=radius, color=(1, 0, 0))
    glPopMatrix()

    # Szczęka prawa
    glPushMatrix()
    glTranslatef(0.0, 0.0, 0.0)
    glRotatef(-opening_ang, 0, 0, 1)  # obrót w prawo
    glTranslatef(0.0, length / 2, 0.0)  # przesuń wzdłuż szczęki
    draw_link(length=length, radius=radius, color=(1, 0, 0))
    glPopMatrix()

def draw_joint(radius=0.09):
    glColor3f(0.2,0.2,0.2)
    glPushMatrix()
    glutSolidSphere(radius, 16, 8)
    glPopMatrix()

def keyboard(key, x, y):
    if key == b'q':
        sys.exit()
    if key == b'a':
        theta[0] += 5
    if key == b'z':
        theta[0] -= 5
    if key == b's':
        theta[1] += 5
    if key == b'x':
        theta[1] -= 5
    if key == b'd':
        theta[2] += 5
    if key == b'c':
        theta[2] -= 5
    if key == b'f':
        theta[3] += 5
    if key == b'v':
        theta[3] -= 5 
    if (key == b'q' & hook_open==False):
        hook_open=True
    if (key == b'q' & hook_open==True):
        hook_open=False
        

    glutPostRedisplay()

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"PUMA Robot - PyOpenGL skeleton")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutMainLoop()

if __name__ == "__main__":
    main()
