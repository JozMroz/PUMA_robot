import sys
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Przykładowe kąty przegubów PUMA (na początek 3 dla uproszczenia)
theta = [0, 0, 0]  # stopnie

BASE_HEIGHT = 1.0  # wysokość pionowej kolumny (możesz zmieniać)

def draw_base():
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6)
    quadric = gluNewQuadric()
    glTranslatef(0, 0, 0)  # baza stoi na (0,0,0)
    gluCylinder(quadric, 0.2, 0.2, BASE_HEIGHT, 32, 8)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glTranslatef(0, 0, BASE_HEIGHT)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glPopMatrix()

def draw_arm():
    glPushMatrix()
    glTranslatef(0, 0, BASE_HEIGHT)
    glRotatef(theta[0], 0, 0, 1)
    draw_link(length=1.0, radius=0.07, color=(1,0,0))
    glTranslatef(1.0, 0, 0)
    glRotatef(theta[1], 0, 1, 0)
    draw_link(length=1.0, radius=0.07, color=(0,1,0))
    glTranslatef(1.0, 0, 0)
    glRotatef(theta[2], 0, 0, 1)
    draw_link(length=0.7, radius=0.06, color=(0,0,1))
    glPopMatrix()

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    gluLookAt(3,3,5, 0,0,0, 0,0,1)  # Ustaw kamerę
    draw_base()   # Dodaj to!
    draw_arm()
    glutSwapBuffers()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, w/h, 0.1, 100)
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