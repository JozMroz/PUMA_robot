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
anim_total_steps = 100

cube_offset_local = np.array([0.2, 0, 1])  # lokalna pozycja kostki względem chwytaka
# Stan robota
theta = [0, 0, 0, 0, 0, 0]
hook_angle = 30
hook_open = True
manual_tcp_offset = np.array([0.0, 0.0, 0.0])  # przesunięcie TCP przez użytkownika
TCP_GRIP_OFFSET = np.array([0.0, 0.0, 1.0])
BASE_HEIGHT = 0.3

# Łańcuch kinematyczny
puma_chain = Chain(name='puma_6dof', links=[
    OriginLink(),
    URDFLink("joint_1", [0, 0, 0.3], [0, 0, 0], [0, 0, 1]),
    URDFLink("joint_2", [0, 0, 0], [0, 0, 0], [0, 1, 0]),
    URDFLink("joint_3", [1.1, 0, 0], [0, 0, 0], [0, 1, 0]),
    URDFLink("joint_4", [1.1, 0, 0], [0, 0, 0], [0, 0, 1]),  # był [1,0,0]
    URDFLink("joint_5", [0.5, 0, 0], [0, 0, 0], [0, 1, 0]),
    URDFLink("joint_6", [0.2, 0, 0], [0, 0, 0], [0, 0, 1]),
])

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
    for i in range(6):
        theta[i] = max(min(theta[i], max_deg[i]), min_deg[i])

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
    glTranslatef(0, 0, BASE_HEIGHT)
    glRotatef(theta[0], 0, 0, 1)
    draw_link_base(length=1.1, radius=0.2, color=(0,0,1))
    glTranslatef(0, 0, 1.1)
    draw_joint(0.2)
    glRotatef(theta[1], 0, 1, 0)
    draw_link(length=1.1, radius=0.15, color=(1,0,0))
    glTranslatef(1.1, 0, 0)
    draw_joint(0.15)
    glRotatef(theta[2], 0, 1, 0)
    draw_link(length=1.1, radius=0.1, color=(0,1,0))
    glTranslatef(1.1, 0, 0)
    draw_joint(0.1)
    glRotatef(theta[3], 1, 0, 0)
    draw_link(length=0.5, radius=0.08, color=(0,1,1))
    glTranslatef(0.5, 0, 0)
    draw_joint(0.08)
    glRotatef(theta[4], 0, 1, 0)
    draw_link(length=0.2, radius=0.06, color=(1,0,1))
    glTranslatef(0.2, 0, 0)
    draw_joint(0.06)
    glRotatef(theta[5], 0, 0, 1)
    draw_hook(opening_ang=hook_angle)
    glPopMatrix()

def draw_link(length=1.0, radius=0.07, color=(1,0,0)):
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    glRotatef(90, 0, 1, 0)
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

def draw_hook(opening_ang=30.0, length=0.4, radius=0.03, spacing=-0.15, end_length=0.2):
    if spacing is None:
        spacing = 0.0
    for direction in [+1, -1]:
        glPushMatrix()
        glTranslatef(0, direction * spacing, 0)
        glRotatef(direction * opening_ang, 0, 0, 1)
        glTranslatef(0, direction * length / 2, 0)
        draw_link(length=length, radius=radius, color=(1, 0, 0))
        glTranslatef(end_length + length / 2, 0, 0)
        glRotatef(-opening_ang * direction, 0, 0, 1)
        draw_joint(0.05)
        draw_link(length=end_length, radius=radius, color=(0, 1, 0))
        glPopMatrix()
    glTranslatef(0.1, 0, 0)

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

    if cube_grabbed and not hook_open:
       update_cube_position_from_tcp()
       draw_cube(cube_position, cube_size)
    else:
       draw_cube(cube_position, cube_size)
       if cube_grabbed and hook_open:
          cube_grabbed = False
        # Ustawienie pozycji po upuszczeniu:
          tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
          tcp_pos = tcp_frame[:3, 3]
          tcp_orient = tcp_frame[:3, :3]
          cube_position = tcp_pos + tcp_orient @ cube_offset_local

    glutSwapBuffers()

def reshape(w, h):
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(70, w/h, 0.1, 100)
    glMatrixMode(GL_MODELVIEW)

def start_animation_to_target(frame, steps=100):
    global theta_anim_start, theta_anim_target, anim_step, anim_total_steps

    anim_total_steps = steps
    anim_step = 0
    theta_anim_start = np.array(theta)

    target_angles = np.degrees(
        puma_chain.inverse_kinematics(
            target_position=frame[:3, 3],
            target_orientation=frame[:3, :3],
            orientation_mode="all",
            initial_position=[0] + list(np.radians(theta))
        )[1:]
    )
    min_deg = [-160, -110, -135, -180, -90, -180]
    max_deg = [ 160,  110,  135,  180,  90,  180]
    min_rad = np.radians(min_deg)
    max_rad = np.radians(max_deg)

    theta_anim_target = np.clip(target_angles, np.degrees(min_rad), np.degrees(max_rad))

    glutTimerFunc(10, animation_step, 0)

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
       tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
       tcp_pos = tcp_frame[:3, 3] + TCP_GRIP_OFFSET
       tcp_orient = tcp_frame[:3, :3]

       if cube_grabbed:
           cube_grabbed = False
           cube_position = tcp_pos + tcp_orient @ cube_offset_local
       else:
           dist = np.linalg.norm(tcp_pos - cube_position)
           if dist < 0.2 and not hook_open:
              cube_grabbed = True
              hook_open = False
              hook_angle = 10.0

              # 🔧 WYZNACZ DYNAMICZNIE OFFSET KOSTKI WZGLĘDEM TCP

              cube_offset_local = np.linalg.inv(tcp_orient) @ (cube_position - tcp_pos)
              print(f"📌 Nowy cube_offset_local = {cube_offset_local}")

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
            frame[:3, 3] = [x, y, z - 1.0]
            frame[:3, :3] = np.eye(3)
            start_animation_to_target(frame)
        except Exception as ex:
            print("❌ Błąd wprowadzania współrzędnych:", ex)
    elif key == b'p':
       tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
       z_axis = tcp_frame[:3, 2]  # kolumna 2 = oś Z TCP
       print(f"🧭 Oś Z chwytaka (TCP): {z_axis}")
    elif key == b'k':
        try:
            # Ustawienie końcówki chwytaka nad kostką
            gripper_orientation = np.array([
            [1, 0, 0],   # X
            [0, 1, 0],   # Y
            [0, 0, -1]   # Z w dół
            ])

        # Pozycja chwytaka dokładnie na pozycji kostki
        # (uwzględniamy, że TCP jest cofnięty względem palców chwytaka)
            tcp_target = get_tcp_from_gripper_target(
                gripper_pos=np.array(cube_position),
                orientation=gripper_orientation,
                offset_vector=TCP_GRIP_OFFSET  # domyślnie: [0.0, 0.0, 1.0]
            )

            start_animation_to_target(tcp_target)
            print(f"🎯 Ramię ustawia się do chwytu kostki: {tcp_target[:3, 3]}")
        except Exception as ex:
            print("❌ Błąd ustawiania TCP do chwytu:", ex)

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

def get_tcp_from_gripper_target(gripper_pos, orientation=np.eye(3), offset_vector=[0.0, 0.0, -0.2]):
    tcp_frame = np.eye(4)
    tcp_frame[:3, :3] = orientation
    tcp_frame[:3, 3] = gripper_pos - orientation @ np.array(offset_vector)
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

    hook_angle = 30.0

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