import sys
import time
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from ikpy.chain import Chain
from ikpy.link import URDFLink, OriginLink
from functools import partial
import math
from OpenGL.GL import shaders

cube_position = [1.0, 0.0, 0.0]  # x, y, z
cube_size = 0.2
cube_visible = True
cube_grabbed = False

# Kamera – sferyczny układ współrzędnych
cam_yaw = 45     # obrót wokół Z (azymut)
cam_pitch = 30   # nachylenie w górę (elewacja)
cam_dist = 6.0   # odległość od środka

# Animacja
theta_anim_start = None
theta_anim_target = None
anim_step = 0
anim_total_steps = 1000

cube_offset_local = np.array([0.0, 0, 0])  # lokalna pozycja kostki względem chwytaka
# Stan robota
theta = [0, 0, 0, 0, 0, 0]

JOINT_LIMITS_MIN = np.array([-180, -180, -180, -180, -180, -180])
JOINT_LIMITS_MAX = np.array([ 180,  180,  180,  180,  180,  180])

hook_angle = 30
hook_open = True
manual_tcp_offset = np.array([0.0, 0.0, 0.0])  # przesunięcie TCP przez użytkownika
TCP_GRIP_OFFSET = np.array([0.0, 0.0, 0.0])
BASE_HEIGHT = 0.3

puma_chain = Chain(name='puma_560', links=[
    OriginLink(),
    
    # Joint 1 - obrót podstawy (Z)
    URDFLink("joint_1", [0, 0, BASE_HEIGHT], [0, 0, 0], [0, 0, 1]),
    
    # Joint 2 - shoulder (Y)
    URDFLink("joint_2", [0, 0, 0.5], [0, 0, 0], [0, 1, 0]),
    
    # Joint 3 - elbow (Y)
    URDFLink("joint_3", [0, 0, 1.1], [0, 0, 0], [0, 1, 0]),
    
    # Joint 4 - roll (X)
    URDFLink("joint_4", [0, 0, 0.9], [0, 0, 0], [1, 0, 0]),
    
    # Joint 5 - pitch (Y)
    URDFLink("joint_5", [0, 0, 0.5], [0, 0, 0], [0, 1, 0]),
    
    # Joint 6 - roll (X)
    URDFLink("joint_6", [0, 0, 0.2], [0, 0, 0], [1, 0, 0]),
])

def print_tcp_position():
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    pos = tcp_frame[:3, 3]
    print(f"📍 Pozycja TCP: x={pos[0]:.3f}, y={pos[1]:.3f}, z={pos[2]:.3f}")

def draw_cube(pos, size=0.1):
    if not cube_visible:
        return

    glPushMatrix()
    glTranslatef(*pos)
    glColor3f(0.8, 0.2, 0.2)
    glutSolidCube(size)
    glPopMatrix()

def rotation_matrix(axis, angle_deg):
    angle_rad = np.radians(angle_deg)
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    elif axis == 'z':
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return np.eye(3)

min_deg = [-160, -110, -135, -180, -90, -180]
max_deg = [ 160,  110,  135,  180,  90,  180]

def clamp_theta():
    global theta
    theta = np.clip(theta, JOINT_LIMITS_MIN, JOINT_LIMITS_MAX)

    # Sprawdzenie, czy TCP nie spada za nisko
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    z_tcp = tcp_frame[2, 3]
    if z_tcp < 0.05:
        print(f"⚠️ Zbyt niskie położenie TCP: z = {z_tcp:.2f}, cofam ruch.")
        theta[1] = max(theta[1], -60)
        theta[2] = min(theta[2], 60)

def draw_base():
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6)
    quadric = gluNewQuadric()
    gluCylinder(quadric, 0.5, 0.2, BASE_HEIGHT, 32, 8)
    gluDisk(quadric, 0, 0.5, 32, 1)
    glTranslatef(0, 0, BASE_HEIGHT)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glPopMatrix()

def draw_arm():
    clamp_theta()
    glPushMatrix()

    # PODSTAWA
    glTranslatef(0, 0, BASE_HEIGHT)
    glRotatef(theta[0], 0, 0, 1)
    length1 = 0.5
    glPushMatrix()
    draw_link_base(length=length1, radius=0.2, color=(0,0,1))
    glPopMatrix()
    glTranslatef(0, 0, length1)
    
    # SEGMENT 1
    glTranslatef(0, 0.15, 0)
    draw_joint2(0.2)
    glTranslatef(0, 0.15, 0)
    glRotatef(theta[1], 0, 1, 0)
    length2 = 1.1
    glPushMatrix()
    draw_link(length=length2, radius=0.15, color=(1,0,0))
    glPopMatrix()
    glTranslatef(0, 0, length2)
    
    # SEGMENT 3
    glTranslatef(0, 0.1, 0)
    draw_joint2(0.15)
    glTranslatef(0, 0.1, 0)
    glRotatef(theta[2], 0, 1, 0)
    length3 = 0.9
    glPushMatrix()
    draw_link(length=length3, radius=0.1, color=(0,1,0))
    glPopMatrix()
    glTranslatef(0, 0, length3)
    
    # SEGMENT 4 
    glTranslatef(0, -0.05, 0)
    draw_joint(0.1)
    glTranslatef(0, -0.05, 0)
    glRotatef(theta[3], 1, 0, 0)
    length4 = 0.5
    glPushMatrix()
    draw_link(length=length4, radius=0.08, color=(0,1,1))
    glPopMatrix()
    glTranslatef(0, 0 , length4)

    # SEGMENT 5
    draw_joint(0.08)
    length5=0.2
    glRotatef(theta[4], 0, 1, 0)
    glPushMatrix()
    draw_link(length=length5, radius=0.06, color=(1,0,1))
    glPopMatrix()
    glTranslatef(0, 0, length5)

    # SEGMENT 6
    draw_joint(0.06)
    glRotatef(theta[5], 0, 0, 1)
    draw_hook(opening_ang=hook_angle)
    glPopMatrix()

def draw_link(length=1.0, radius=0.07, color=(1,0,0)):
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    gluCylinder(quadric, radius, radius, length, 16, 4)
    gluDisk(quadric, 0, radius, 16, 1)
    glTranslatef(0, 0, length)
    gluDisk(quadric, 0, radius, 16, 1)
    glPopMatrix()

def draw_link_base(length=1.0, radius=0.07, color=(1,0,0)):
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    gluCylinder(quadric, radius, radius, length, 16, 4)
    gluDisk(quadric, 0, radius, 16, 1)
    glPopMatrix()

def draw_joint(radius=0.09):
    glColor3f(1,1,0)
    glPushMatrix()
    glutSolidSphere(radius, 16, 8)
    glPopMatrix()

def draw_joint2(radius=0.07, height=0.04):
    glColor3f(1, 1, 0)  # żółty

    quadric = gluNewQuadric()
    glPushMatrix()

    # Orientacja w osi Z
    glRotatef(90, 1, 0, 0)

    # Denko dolne
    gluDisk(quadric, 0, radius, 16, 1)

    # Główna część cylindra
    gluCylinder(quadric, radius, radius, height, 16, 4)

    # Denko górne
    glTranslatef(0, 0, height)
    gluDisk(quadric, 0, radius, 16, 1)

    glPopMatrix()

def draw_fingers(opening_ang=30.0, length=0.4, radius=0.03, spacing=0.08, end_length=0.2):
    for direction in [+1, -1]:
        glPushMatrix()
        draw_link(length=length, radius=radius, color=(1, 0, 0))
        glTranslatef(0, direction * spacing, 0)
        glRotatef(direction * opening_ang, 0, 0, 1)
        glTranslatef(0, direction * length / 2, 0)
        #draw_link(length=length, radius=radius, color=(1, 0, 0))
        glTranslatef(end_length + length / 2, 0, 0)
        glRotatef(-opening_ang * direction, 0, 0, 1)
        draw_joint(0.05)
        draw_link(length=end_length, radius=radius, color=(0, 1, 0))
        glPopMatrix()


def draw_hook(opening_ang=30.0, length=0.4, radius=0.03, spacing=-0.2, end_length=0.2):
    glPushMatrix()
    glRotatef(90, 0, 1, 0)  # Obracamy, żeby chwytak był wzdłuż osi Z

    for direction in [+1, -1]:
        glPushMatrix()
        glTranslatef(0, direction * spacing, 0)
        glRotatef(direction * opening_ang, 1, 0, 0)
        glTranslatef(0, direction * length / 2, 0)
        draw_link(length=length, radius=radius, color=(1, 0, 0))
        glTranslatef(end_length + length / 2, 0, 0)
        glRotatef(-opening_ang * direction, 0, 0, 1)
        #draw_joint(0.05)
        #draw_link(length=end_length, radius=radius, color=(0, 1, 0))
        glPopMatrix()

    glPopMatrix()


def draw_floor():
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glVertex3f(5, 0, 0)
    glVertex3f(0, 5, 0)
    glVertex3f(-5, 0, 0)
    glVertex3f(0, -5, 0)
    glEnd()

def display():
    global cube_grabbed
    global cube_position
    glClearColor(1.0, 0.5, 0.31, 0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Oblicz pozycję kamery na podstawie kąta
    x = cam_dist * np.cos(np.radians(cam_pitch)) * np.cos(np.radians(cam_yaw))
    y = cam_dist * np.cos(np.radians(cam_pitch)) * np.sin(np.radians(cam_yaw))
    z = cam_dist * np.sin(np.radians(cam_pitch))

    gluLookAt(x, y, z, 0, 0, 0.5, 0, 0, 1)

    draw_floor()
    draw_base()
    draw_arm()

    if cube_grabbed:
        if not hook_open:
            update_cube_position_from_tcp()
        else:
            # upuszczenie kostki w aktualnej pozycji chwytaka
            tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
            tcp_pos = tcp_frame[:3, 3] + TCP_GRIP_OFFSET
            tcp_orient = tcp_frame[:3, :3]
            cube_position = tcp_pos + tcp_orient @ cube_offset_local
            cube_grabbed = False
    draw_cube(cube_position, cube_size)

    glutSwapBuffers()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(70, w/h, 0.1, 100)
    glMatrixMode(GL_MODELVIEW)

def start_animation_to_target(frame, steps=1000):
    global theta_anim_start, theta_anim_target, anim_step, anim_total_steps

    anim_total_steps = steps
    anim_step = 0
    theta_anim_start = np.array(theta)

    # Ograniczenia w stopniach

    try:
        # Rozwiąż IK
        ik_result = puma_chain.inverse_kinematics(
            target_position=frame[:3, 3],
            target_orientation=frame[:3, :3],
            orientation_mode="all",
            initial_position=[0] + list(np.radians(theta))
        )

        # Wyciągnij kąty z IK (pomijamy joint 0)
        target_angles = np.degrees(ik_result[1:])

        # Ogranicz kąty IK do zakresu
        theta_anim_target = np.clip(target_angles, JOINT_LIMITS_MIN, JOINT_LIMITS_MAX)

        # Rozpocznij animację
        glutTimerFunc(10, animation_step, 0)
    except Exception as ex:
        print("❌ Błąd IK / animacji:", ex)

def animation_step(value):
    global theta, anim_step, anim_total_steps

    if anim_step >= anim_total_steps:
        return

    alpha = anim_step / anim_total_steps
    theta = (1 - alpha) * theta_anim_start + alpha * theta_anim_target
    clamp_theta()
    glutPostRedisplay()

    anim_step += 1
    glutTimerFunc(10, animation_step, 0)
    if cube_grabbed and not hook_open:
        update_cube_position_from_tcp()
    print(f"[Step {anim_step}] theta = {theta.round(2)}")

def keyboard_movement(key):
    global theta
    step = 2.0  # krok w stopniach

    keymap = {
        b'z': (0, +step), b'x': (0, -step),  # joint 1
        b'm': (1, +step), b'n': (1, -step),  # joint 2
        b'u': (2, +step), b'i': (2, -step),  # joint 3
        b'j': (3, +step), b'h': (3, -step),  # joint 4
        b'l': (4, +step), b';': (4, -step),  # joint 5
        b't': (5, +step), b'y': (5, -step),  # joint 6
        }

    if key in keymap:
        joint, delta = keymap[key]
        theta[joint] += delta
        clamp_theta()
        glutPostRedisplay()
        print(f"[Manual] theta = {theta}")


def keyboard(key, x, y, frame):
    global hook_open, hook_angle, target_index, targets
    global cam_yaw, cam_pitch, cam_dist
    global cube_position, cube_grabbed, cube_visible
    global cube_offset_local

    if key == b'q':
        sys.exit()
    elif key == b'o':
        hook_open = not hook_open
        hook_angle = 30.0 if hook_open else 10.0

    elif key == b'g':
        print("🔎 Sprawdzam warunki chwytu...")
        tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    
        # Oblicz pozycję chwytaka
        gripper_pos = tcp_frame[:3, 3] + tcp_frame[:3, :3] @ TCP_GRIP_OFFSET
        gripper_orient = tcp_frame[:3, :3]
    
        # Oblicz odległość do kostki
        dist = np.linalg.norm(gripper_pos - np.array(cube_position))
    
        if cube_grabbed:
            print("📤 Kostka upuszczona.")
            cube_grabbed = False
            # Zachowaj aktualną pozycję kostki
        elif dist < 0.3:  # Zmniejszony próg odległości
            print("📥 Chwytam kostkę")
            hook_open = False
            hook_angle = 60.0
            cube_grabbed = True
            # Oblicz lokalne przesunięcie kostki względem chwytaka
            cube_offset_local = np.linalg.inv(gripper_orient) @ (np.array(cube_position) - gripper_pos)
            print(f"📌 Nowy cube_offset_local = {cube_offset_local}")
        else:
            print(f"❌ Za daleko od kostki: {dist:.2f}")

    elif key == b'r':
        cube_visible = True
        cube_grabbed = False
        cube_position = [1.0, 0.0, 0.0]

    elif key == b'c':
        try:
            coords = input("Podaj współrzędne kostki x y z (oddzielone spacjami): ").strip()
            x, y, z = map(float, coords.split())
            cube_position = [x, y, z]
            print(f"✅ Kostka ustawiona na: {cube_position}")
        except Exception as ex:
            print("❌ Błąd wprowadzania współrzędnych kostki:", ex)

    elif key == b'e':
        try:
            coords = input("Podaj współrzędne x y z (oddzielone spacjami): ").strip()
            x, y, z = map(float, coords.split())

            # Poprawna macierz transformacji TCP uwzględniająca przesunięcie końcówki chwytaka
            frame = get_tcp_from_gripper_target(
                gripper_pos=np.array([x, y, z]),
                orientation=np.eye(3),
                offset_vector=TCP_GRIP_OFFSET
            )

            start_animation_to_target(frame)
        except Exception as ex:
            print("❌ Błąd wprowadzania współrzędnych:", ex)
    elif key == b'p':
       tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
       z_axis = tcp_frame[:3, 2]  # kolumna 2 = oś Z TCP
       print(f"🧭 Oś Z chwytaka (TCP): {z_axis}")

    elif key == b'k':
        try:
            cube_pos = np.array(cube_position)

            # Docelowa orientacja chwytaka: Z w dół (chwyt pionowy z góry)
            gripper_orientation = np.array([
                [1,  0,  0],
                [0, 1,  0],
                [0,  0, 1]
            ])

            # Pozycja TCP, tak by końcówka chwytaka była idealnie w centrum kostki
            tcp_target = get_tcp_from_gripper_target(
                gripper_pos=cube_pos,
                orientation=gripper_orientation,
                offset_vector=TCP_GRIP_OFFSET
            )

            print("🎯 Ustawiam TCP bezpośrednio do chwytu...")
            start_animation_to_target(tcp_target)

        except Exception as ex:
            print("❌ Błąd ustawiania TCP do dokładnego chwytu:", ex)
    
    elif key == b'f':
        print_tcp_position()

    # Kamera – obrót i zoom
    elif key == b'a': cam_yaw -= 5
    elif key == b'd': cam_yaw += 5
    elif key == b'w': cam_pitch = min(cam_pitch + 5, 89)
    elif key == b's': cam_pitch = max(cam_pitch - 5, -89)
    elif key == b'+': cam_dist = max(2.0, cam_dist - 0.5)
    elif key == b'-': cam_dist = min(15.0, cam_dist + 0.5)
    else:
        keyboard_movement(key)


    glutPostRedisplay()

def get_tcp_from_gripper_target(gripper_pos, orientation=np.eye(3), offset_vector=[0.0, 0.0, 0.0]):
    tcp_frame = np.eye(4)
    tcp_frame[:3, :3] = orientation
    tcp_frame[:3, 3] = gripper_pos - orientation @ np.array(offset_vector)
    print(f"🎯 Cel IK: {tcp_frame[:3, 3]}")
    return tcp_frame

def update_cube_position_from_tcp():
    global cube_position
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    tcp_pos = tcp_frame[:3, 3] + TCP_GRIP_OFFSET
    tcp_orient = tcp_frame[:3, :3]
    cube_position = tcp_pos + tcp_orient @ cube_offset_local

def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"PUMA Robot - PyOpenGL + IK 6DOF")

    glEnable(GL_DEPTH_TEST)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glShadeModel(GL_SMOOTH)

    light_position = [2.0, 2.0, 5.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)

    light_position = [1.0, 1.0, 2.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)

    glShadeModel(GL_SMOOTH)  # lub GL_FLAT dla płaski

    global targets, target_index
    targets = [
        ([1.2, 0.0, 1.2], np.eye(3)),
        ([1.5, 0.5, 1.0], rotation_matrix('z', 45)),
        ([1.0, -0.5, 1.3], rotation_matrix('y', 90))
    ]
    target_index = 0

    frame = np.eye(4)
    pos, orient = targets[target_index]
    frame[:3, 3] = pos
    frame[:3, :3] = orient

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(partial(keyboard, frame=frame))
    start_animation_to_target(frame)
    glutMainLoop()

if __name__ == "__main__":
    main()