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

FLOOR_Z_LIMIT = 0.00  
MAX_REACH = 2.7

cube_velocity = np.array([0.0, 0.0, 0.0])  # prędkość obiektu 
gravity = np.array([0.0, 0.0, -15.81])  # m/s² - grawitacja
delta_time = 1/10.0  # zakładamy 60 FPS


cube_size = 0.2 # wielkość kuli
cube_position = [1.5, 1.5, cube_size / 2]  # pozycja początkowa kuli
cube_visible = True
cube_grabbed = False

ground_z = cube_size/2

# Kamera – sferyczny układ współrzędnych
cam_yaw = 45     # obrót wokół Z 
cam_pitch = 30   # nachylenie w górę 
cam_dist = 6.0   # odległość od środka

# Parametry animacji
theta_anim_start = None
theta_anim_target = None
anim_step = 0
anim_total_steps = 1000

cube_offset_local = np.array([0.0, 0, 0])  # lokalna pozycja kostki względem chwytaka

# Stan robota - kąt theta 
theta = [0, 0, 0, 0, 0, 0, 0]

#Ograniczenia kątów
JOINT_LIMITS_MIN = np.array([-180, -180, -180, -180, -180, -180, - 180]) 
JOINT_LIMITS_MAX = np.array([ 180,  180,  180,  180,  180,  180, 180])

hook_angle = 30 # kąt chwytaka
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
    URDFLink("joint_3", [0, 0, 1.0], [0, 0, 0], [0, 1, 0]),
    
    # Joint 4 - roll (X)
    URDFLink("joint_4", [0, 0.5, 0.8], [0, 0, 0], [0, 1, 0]),

    # Joint 5 
    
    URDFLink("joint_5", [0, -0.1, 0.2], [0, 0, 0], [1, 0, 0]),

    # Joint 6

    URDFLink("joint_6", [0, 0, 0.2], [0, 0, 0], [0, 0, 1]),

    URDFLink("tcp_offset", [0.4, 0.0, 0.0], [0, 0, 0], [0, 0, 0]),

])

# Wyświetlanie pozycji TCP:
def print_tcp_position():
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    pos = tcp_frame[:3, 3]
    print(f"Pozycja TCP: x={pos[0]:.3f}, y={pos[1]:.3f}, z={pos[2]:.3f}")

# Rysowanie kuli
def draw_cube(pos, size=0.1):
    if not cube_visible:
        return

    glPushMatrix()
    glTranslatef(*pos)
    glColor3f(0.2, 0.4, 0.9)  # kolor kuli
    glutSolidSphere(size / 2, 20, 20)
    glPopMatrix()

# Funkcja umożliwiająca obrót
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

def clamp_theta():

    '''

    Funkcja ta zapobiega sytuacjom, kiedy to któryś z przegubów robota przekroczyłby swoje fizyczne limity obrotu.
    Dzięki temu robot porusza się realistycznie, z zastosowaniem ograniczeń

    '''

    global theta
    theta = np.clip(theta, JOINT_LIMITS_MIN, JOINT_LIMITS_MAX)

    # Sprawdzenie, czy TCP nie spada za nisko
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    z_tcp = tcp_frame[2, 3]
    if z_tcp <= FLOOR_Z_LIMIT:
        print(f"⛔ Kolizja z podłogą! TCP za nisko: z = {z_tcp:.3f}")
        # Cofnij ostatni krok animacji / ruchu
        theta[:] = theta_anim_start if theta_anim_start is not None else theta

def draw_base():

    '''
    
    Funkcja tworząca podstawkę do robota.

    '''
        
    glPushMatrix()
    glColor3f(0.6, 0.6, 0.6) # kolor
    quadric = gluNewQuadric()
    gluCylinder(quadric, 0.5, 0.2, BASE_HEIGHT, 32, 8)
    gluDisk(quadric, 0, 0.5, 32, 1)
    glTranslatef(0, 0, BASE_HEIGHT)
    gluDisk(quadric, 0, 0.2, 32, 1)
    glPopMatrix()

def draw_arm():

    '''
    
    Funkcja umożliwiająca rysowanie ramienia robota (na podstawce)

    '''
        
    clamp_theta() # Załączenie funkcji clamp_theta
    glPushMatrix()

    # PODSTAWA 
    glTranslatef(0, 0, BASE_HEIGHT)
    glRotatef(theta[0], 0, 0, 1)

    # SEGMENT 1 
    length1 = 0.5 
    glPushMatrix()
    draw_link_base(length=length1, radius=0.2, color=(0.3, 0.3, 0.6))
    glPopMatrix()
    glTranslatef(0, 0, length1)
    
    # SEGMENT 2
    glTranslatef(0, 0.15, 0)
    draw_joint(0.2) # Rysowanie kuli
    glTranslatef(0, 0.15, 0)
    glRotatef(theta[1], 0, 1, 0)
    length2 = 1.0 # długość danej części ramienia
    glPushMatrix()
    draw_link(length=length2, radius=0.15, color=(0.4, 0.6, 0.8))
    glPopMatrix()
    glTranslatef(0, 0, length2)
    
    # SEGMENT 3
    glTranslatef(0, 0.1, 0)
    draw_joint(0.15)
    glTranslatef(0, 0.1, 0)
    glRotatef(theta[2], 0, 1, 0)
    length3 = 0.8 # długość danej części ramienia
    glPushMatrix()
    draw_link(length=length3, radius=0.1, color=(0.4, 0.7, 0.6))
    glPopMatrix()
    glTranslatef(0, 0, length3)
    
    # SEGMENT 4 
    glTranslatef(0, -0.05, 0)
    draw_joint(0.1)
    glTranslatef(0, -0.05, 0)
    glRotatef(theta[3], 0, 1, 0)
    length4 = 0.2 # długość danej części ramienia
    glPushMatrix()
    draw_link(length=length4, radius=0.08, color=(0.5, 0.5, 0.7))
    glPopMatrix()
    glTranslatef(0, 0 , length4)

    # SEGMENT 5
    draw_joint(0.08)
    length5=0.2 # długość danej części ramienia
    glRotatef(theta[4], 1, 0, 0)    
    glPushMatrix()
    draw_link(length=length5, radius=0.06, color=(0.6, 0.4, 0.6))
    glPopMatrix()
    glTranslatef(0, 0, length5)

    # SEGMENT 6
    draw_joint(0.06)
    glRotatef(theta[5], 0, 0, 1)
    draw_hook(opening_ang=hook_angle)
    glPopMatrix()

def draw_link(length=1.0, radius=0.07, color=(1, 0, 0)):
 
    '''
    
    Funkcja rysująca segment ramienia 

    '''
    
    glColor3f(*color)
    quadric = gluNewQuadric()
    gluCylinder(quadric, radius, radius, length, 16, 4)
    glPushMatrix()
    glRotatef(180, 1, 0, 0)  #Odpowiednia rotacja
    gluDisk(quadric, 0, radius, 16, 1)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(0, 0, length)
    gluDisk(quadric, 0, radius, 16, 1)
    glPopMatrix()

def draw_link_base(length=1.0, radius=0.07, color=(1,0,0)):

    '''
    
    Funkcja rysująca bazę.

    '''
     
    glColor3f(*color)
    quadric = gluNewQuadric()
    glPushMatrix()
    gluCylinder(quadric, radius, radius, length, 16, 4)
    gluDisk(quadric, 0, radius, 16, 1)
    glTranslatef(0, 0, length)
    gluDisk(quadric, 0, radius, 16, 1)
    glPopMatrix()

def draw_joint(radius=0.09):

    '''
    
    Funkcja rysująca kulę (przegub)

    '''

    glColor3f(1.0, 0.9, 0.3)
    glPushMatrix()
    glutSolidSphere(radius, 16, 8)
    glPopMatrix()

def draw_hook(opening_ang=30.0, length=0.3, radius=0.03, spacing=0.0, end_length=0.2):
    glPushMatrix()
    glRotatef(90, 0, 1, 0)  # Ustawienie haka wzdłuż osi

    for direction in [+1, -1]:
        glPushMatrix()
        glTranslatef(0, direction * spacing, 0)

        # ROTACJA tylko czerwonej części
        glRotatef(direction * opening_ang, 1, 0, 0)
        draw_link(length=length, radius=radius, color=(0.9, 0.2, 0.2))  
        glTranslatef(0, 0, end_length + length / 2)

        # ZRESETUJ rotację przed rysowaniem zielonej części
        glPushMatrix()
        glRotatef(-direction * opening_ang, 1, 0, 0)  # Odwrócenie poprzedniej rotacji
        draw_joint(0.05)
        draw_link(length=end_length, radius=radius, color=(0.3, 0.8, 0.4)) 
        glPopMatrix()
        glPopMatrix()

    glPopMatrix()


def draw_floor():

    '''
    
    Funkcja rysująca podgłogę - na której stoi robot, czy umiejscowiony jest obiekt.

    '''

    glColor3f(0.5, 0.5, 0.5)
    glBegin(GL_LINES)
    step = 0.5 #warość kroku
    range_ = 5
    for i in np.arange(-range_, range_ + step, step):

        # linie wzdłuż X
        glVertex3f(i, -range_, 0)
        glVertex3f(i, range_, 0)

        # linie wzdłuż Y
        glVertex3f(-range_, i, 0)
        glVertex3f(range_, i, 0)
    glEnd()

def get_gripper_hitbox():

    '''
    
    Hitboxy

    '''
    
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    gripper_pos = tcp_frame[:3, 3] + tcp_frame[:3, :3] @ TCP_GRIP_OFFSET
    gripper_orient = tcp_frame[:3, :3]

    # Rozmiar hitboxa 
    hitbox_size = np.array([0.1, 0.1, 0.2])  # szerokość, głębokość, wysokość

    return gripper_pos, gripper_orient, hitbox_size


def is_gripper_below_floor(theta_candidate):
    theta_rad = [0] + list(np.radians(theta_candidate))
    tcp_frame = puma_chain.forward_kinematics(theta_rad)

    # Pozycja środka hitboxa
    gripper_pos = tcp_frame[:3, 3] + tcp_frame[:3, :3] @ TCP_GRIP_OFFSET

    # Zakładamy, że oś Z hitboxa to orientacja Z chwytaka
    hitbox_height = 0.2  # wysokość hitboxa (zmień jeśli trzeba)
    z_bottom = gripper_pos[2] - (hitbox_height / 2)

    return z_bottom <= FLOOR_Z_LIMIT

def display():

    '''
    
    Funkcja pokazująca obraz - ramię robota + obiekt + przestrzeń

    '''
     
    global cube_velocity
    global cube_grabbed
    global cube_position

    glClearColor(0.78, 0.83, 0.89, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Obliczanie pozycji kamery na podstawie kąta 
    x = cam_dist * np.cos(np.radians(cam_pitch)) * np.cos(np.radians(cam_yaw))
    y = cam_dist * np.cos(np.radians(cam_pitch)) * np.sin(np.radians(cam_yaw))
    z = cam_dist * np.sin(np.radians(cam_pitch))

    gluLookAt(x, y, z, 0, 0, 0.5, 0, 0, 1)

    draw_floor() #Rysowanie podgłogi
    draw_base()  #Rysowanie podstawki
    draw_arm()   #Rysowanie ramienia

    if cube_grabbed:
        if not hook_open:
            update_cube_position_from_tcp()
        else:
            # upuszczenie kostki w aktualnej pozycji chwytaka
            tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
            tcp_pos = tcp_frame[:3, 3] + TCP_GRIP_OFFSET
            tcp_orient = tcp_frame[:3, :3]
            cube_position = tcp_pos + tcp_orient @ cube_offset_local
            cube_velocity[:] = np.array([0.0, 0.0, 0.0])
            cube_grabbed = False
    else:
        # Symulacja spadania
        cube_velocity += gravity * delta_time
        cube_position += cube_velocity * delta_time

    # Detekcja kolizji z ziemią
    if cube_position[2] < ground_z:
        cube_position[2] = ground_z
        cube_velocity[:] = 0.0

    draw_cube(cube_position, cube_size)

    glutSwapBuffers()

def reshape(w, h):

    '''
    
    Ustawienie perspektywy OpenGL po zmianie rozmiaru okna

    '''
        
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(70, w/h, 0.1, 100)
    glMatrixMode(GL_MODELVIEW)

def start_animation_to_target(frame, steps=200):

    '''
    
    Animacja pozwalająca zasymulować ruch ramienia w sposób realistyczny

    '''
        
    global theta_anim_start, theta_anim_target, anim_step, anim_total_steps

    anim_total_steps = steps #kroki symulacji
    anim_step = 0
    theta_anim_start = np.array(theta)

    try:
        ik_result = puma_chain.inverse_kinematics(
            target_position=frame[:3, 3],
            target_orientation=frame[:3, :3],
            orientation_mode="all",
            initial_position=[0] + list(np.radians(theta))
        )

        target_angles = np.degrees(ik_result[1:])  # pomijamy pierwszy (dla fixed base)
        theta_anim_target = np.clip(target_angles, JOINT_LIMITS_MIN, JOINT_LIMITS_MAX)

        glutTimerFunc(10, animation_step, 0)
    except Exception as ex:
        print("Błąd IK / animacji:", ex)

def animation_step(value):

    '''

    Symulowanie ruchu robota "krok po kroku" w czasie.

    '''
    global theta, anim_step, anim_total_steps

    if anim_step >= anim_total_steps:
        return

    alpha = anim_step / anim_total_steps
    candidate_theta = (1 - alpha) * theta_anim_start + alpha * theta_anim_target
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(candidate_theta)))
    z_tcp = tcp_frame[2, 3]

    if is_arm_below_floor(candidate_theta) or is_gripper_below_floor(candidate_theta):
        print(f"⛔ Animacja zatrzymana – kolizja ramienia z podłogą")
        return
    
    theta = candidate_theta
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
        b'z': (0, +step), b'x': (0, -step),
        b'm': (1, +step), b'n': (1, -step),
        b'u': (2, +step), b'i': (2, -step),
        b'j': (3, +step), b'h': (3, -step),
        b'l': (4, +step), b';': (4, -step),
        b't': (5, +step), b'y': (5, -step),
    }

    if key in keymap:
        joint, delta = keymap[key]
        test_theta = theta.copy()
        test_theta[joint] += delta

        # Sprawdź czy nowa pozycja nie spowoduje kolizji
        tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(test_theta)))
        z_tcp = tcp_frame[2, 3]

        if is_arm_below_floor(test_theta) or is_gripper_below_floor(test_theta):
            print(f"Ruch zablokowany – jakiś segment zahacza podłogę")
            return

        # Jeśli OK – wykonaj ruch
        theta[joint] += delta
        clamp_theta()
        glutPostRedisplay()
        print(f"[Manual] theta = {theta}")


def keyboard(key, x, y, frame):

    '''

    Przypisanie klawiszy do wykonywania odpowiednich ruchów.

    '''
        
    global hook_open, hook_angle, target_index, targets
    global cam_yaw, cam_pitch, cam_dist
    global cube_position, cube_grabbed, cube_visible
    global cube_offset_local

    if key == b'7':
        sys.exit() #Wyjście

    elif key == b'o': #Otwieranie/zamykanie chwytaka
        hook_open = not hook_open
        hook_angle = 30.0 if hook_open else 20.0

    elif key == b'g': #Łapanie kulki wraz z warunkami (czy jest odpowiednia odległość itd.)
        print("Sprawdzam warunki chwytu...")
        tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    
        # Oblicz pozycję chwytaka
        gripper_pos = tcp_frame[:3, 3] + tcp_frame[:3, :3] @ TCP_GRIP_OFFSET
        gripper_orient = tcp_frame[:3, :3]
    
        # Oblicz odległość do kostki
        dist = np.linalg.norm(gripper_pos - np.array(cube_position))
    
        if cube_grabbed:
            print("Kostka upuszczona.")
            cube_grabbed = False
            # Zachowaj aktualną pozycję kostki
        elif dist < 0.3:  # Zmniejszony próg odległości
            print("Chwytam kostkę")
            hook_open = False
            hook_angle = 20.0
            cube_grabbed = True
            # Oblicz lokalne przesunięcie kostki względem chwytaka

            cube_offset_local = np.zeros(3)
            print(f"Nowy cube_offset_local = {cube_offset_local}")
        else:
            print(f"Za daleko od kostki: {dist:.2f}")

    elif key == b'c': #Zmiana położenia kostki
        try:
            coords = input("Podaj współrzędne kostki x y z (oddzielone spacjami): ").strip()
            x, y, z = map(float, coords.split())
            proposed_position = np.array([x, y, z])
            distance_from_base = np.linalg.norm(proposed_position[:2])  

            if distance_from_base > MAX_REACH:
                print(f"Pozycja ({x:.2f}, {y:.2f}) jest za daleko! Maksymalny zasięg to {MAX_REACH} m.")
            else:
                cube_position = [x, y, z]
                print(f"Kostka ustawiona na: {cube_position}")
        except Exception as ex:
            print("Błąd wprowadzania współrzędnych kostki:", ex)

    elif key == b'e': #Zmiana położenia ramienia (współrzędne tcp)
        try:
            coords = input("Podaj współrzędne x y z (oddzielone spacjami): ").strip()
            x, y, z = map(float, coords.split())

            # Poprawna macierz transformacji TCP uwzględniająca przesunięcie końcówki chwytaka
            frame = get_tcp_from_gripper_target(
                gripper_pos=np.array([x, y, z]),
                orientation=np.eye(3),

            )

            try_reach_safely(frame)
        except Exception as ex:
            print("Błąd wprowadzania współrzędnych:", ex)

    elif key == b'k': #Dojście chwytaka do obiektu (z animacją)
        execute_approach_and_grab(cube_position)
    
    elif key == b'f': #Wyświetlenie pozycji TCP (x, y, z)
        print_tcp_position()



    # Kamera – obrót i zoom
    elif key == b'a': cam_yaw -= 5
    elif key == b'd': cam_yaw += 5
    elif key == b'w': cam_pitch = min(cam_pitch + 5, 89)
    elif key == b's': cam_pitch = max(cam_pitch - 5, -89)
    elif key == b'+': cam_dist = max(2.0, cam_dist - 0.5)
    elif key == b'-': cam_dist = min(15.0, cam_dist + 0.5)
    else:
        keyboard_movement(key) #Reszta funkcji zapisana w innym miejscu


    glutPostRedisplay()

def get_tcp_from_gripper_target(gripper_pos, orientation=np.eye(3)):

    '''
    Funkcja tworzy macierz transformacji TCP opartą na zadanej 
    pozycji i orientacji chwytaka – do użycia w inverse kinematics.
    '''
    tcp_frame = np.eye(4)
    tcp_frame[:3, :3] = orientation
    tcp_frame[:3, 3] = gripper_pos
    print(f"Cel IK: {tcp_frame[:3, 3]}")
    return tcp_frame

def update_cube_position_from_tcp():
    global cube_position
    tcp_frame = puma_chain.forward_kinematics([0] + list(np.radians(theta)))
    cube_position = tcp_frame[:3, 3]

def is_arm_below_floor(theta_deg):
    theta_rad = [0] + list(np.radians(theta_deg))
    frames = puma_chain.forward_kinematics(theta_rad, full_kinematics=True)

    for i, frame in enumerate(frames[1:], start=1):  # pomiń base (0)
        z = frame[2, 3]
        if z <= FLOOR_Z_LIMIT:
            print(f"Segment {i} za nisko: z = {z:.3f}")
            return True
    return False

def try_reach_safely(target_frame, max_attempts=10, dz_step=0.05, angles_deg=[0, 30, 60, 90, 120, 150, 180]):
    """
    Próbuje dotrzeć do celu poprzez:
    1. Zorientowanie TCP w dół (Z-osią)
    2. Rotacje wokół osi X (pochylenie chwytaka)
    3. Unoszenie celu nad podłogą

    Szuka bezkolizyjnej konfiguracji.
    """
    def generate_orientations_z_down():
        base_orientation = np.eye(3)
        base_orientation[:, 2] = np.array([0, 0, -1])  # Z w dół
        base_orientation[:, 1] = np.cross([0, 0, 1], base_orientation[:, 2])  # ortogonalne Y
        base_orientation[:, 0] = np.cross(base_orientation[:, 1], base_orientation[:, 2])

        angles_z = [0, 45, 90, 135, 180]
        angles_x = [0, 30, 60]

        for ax in angles_x:
            for az in angles_z:
                Rz = rotation_matrix('z', az)
                Rx = rotation_matrix('x', ax)
                yield Rx @ Rz @ base_orientation

    for dz in [dz_step * i for i in range(max_attempts)]:
        for orient in generate_orientations_z_down():
            test_frame = target_frame.copy()
            test_frame[2, 3] += dz
            test_frame[:3, :3] = orient

            try:
                ik_result = puma_chain.inverse_kinematics(
                    target_position=test_frame[:3, 3],
                    target_orientation=test_frame[:3, :3],
                    orientation_mode="all",
                    initial_position=[0] + list(np.radians(theta))
                )
                candidate_theta = np.degrees(ik_result[1:])

                if not is_arm_below_floor(candidate_theta) and not is_gripper_below_floor(candidate_theta):
                    print(f"✅ Ustawienie OK: dz={dz:.2f}")
                    start_animation_to_target(test_frame)
                    return
                else:
                    print(f"Kolizja przy dz={dz:.2f}")
            except Exception as ex:
                print(f"Błąd IK: {ex}")

    print("Nie znaleziono bezkolizyjnej trajektorii.")

def execute_approach_and_grab(target_xyz):
    """
    Sekwencja:
    1. Podejście z góry (Z + 0.2)
    2. Po zakończeniu animacji zejście w dół z właściwą orientacją chwytaka
    """
    print("🚀 Etap 1: podejście nad kostkę")

    approach_frame = get_tcp_from_gripper_target(
        gripper_pos=np.array(target_xyz) + np.array([0, 0, 0.2]),
        orientation=np.eye(3)
    )

    def descend_to_target(_):
        print("🕳️ Etap 2: zejście w dół z obrotem chwytaka")
        gripper_orientation = np.array([
            [1,  0,  0],
            [0,  1,  0],
            [0,  0, -1]  # oś Z chwytaka skierowana w dół
        ])
        target_frame = get_tcp_from_gripper_target(
            gripper_pos=np.array(target_xyz),
            orientation=gripper_orientation
        )
        try_reach_safely(target_frame)

    # Wykonaj pierwszy etap i po 1.5 sekundy drugi
    try_reach_safely(approach_frame)
    glutTimerFunc(1500, descend_to_target, 0)



def main():
    '''
    Funkcja główna – inicjalizuje okno OpenGL, ustawia światło, kamerę i uruchamia pętlę główną GLUT
    '''

    # Inicjalizacja GLUT z argumentami systemowymi
    glutInit(sys.argv)

    # Ustawienie trybu wyświetlania: podwójne buforowanie, kolory RGB i bufor głębokości
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)

    # Ustawienie początkowego rozmiaru okna
    glutInitWindowSize(800, 600)

    # Utworzenie okna z tytułem
    glutCreateWindow(b"Robot PUMA")

    # Włączenie testu głębokości (widoczność obiektów zależna od odległości)
    glEnable(GL_DEPTH_TEST)

    # Włączenie oświetlenia sceny
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)

    # Włączenie obsługi kolorów dla materiałów
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

    # Ustawienie wygładzania oświetlenia (lepsze przejścia cieni)
    glShadeModel(GL_SMOOTH)

    # Ustawienie parametrów światła (ambient – rozproszone, diffuse – podstawowe, specular – połysk)
    glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])

    # Włączenie efektu mgły (dla głębi)
    glEnable(GL_FOG)
    glFogfv(GL_FOG_COLOR, [0.92, 0.95, 1.0, 1.0])  # kolor mgły
    glFogf(GL_FOG_START, 4.0)                     # odległość początku mgły
    glFogf(GL_FOG_END, 12.0)                      # odległość końca mgły
    glFogi(GL_FOG_MODE, GL_LINEAR)                # liniowe przejście mgły

    # Ustawienie pozycji światła
    light_position = [2.0, 2.0, 5.0, 1.0]
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)
    light_position = [1.0, 1.0, 2.0, 1.0]  # nadpisuje poprzednie – można usunąć wcześniejsze
    glLightfv(GL_LIGHT0, GL_POSITION, light_position)

    # Tryb cieniowania (ponownie – może być zbędny, bo był wyżej)
    glShadeModel(GL_SMOOTH)

    # Celowe pozycje i orientacje – do testowania inverse kinematics
    global targets, target_index
    targets = [
        ([1.2, 0.0, 1.2], np.eye(3)),                     # bez rotacji
        ([1.5, 0.5, 1.0], rotation_matrix('z', 45)),      # obrót wokół Z
        ([1.0, -0.5, 1.3], rotation_matrix('y', 90))      # obrót wokół Y
    ]
    target_index = 0

    # Zbudowanie pierwszej ramki celu (pozycja + orientacja)
    frame = np.eye(4)
    pos, orient = targets[target_index]
    frame[:3, 3] = pos        # pozycja celu
    frame[:3, :3] = orient    # orientacja celu

    # Rejestracja funkcji obsługi renderowania, zmiany rozmiaru okna i klawiatury
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(partial(keyboard, frame=frame))  # przekazuje frame jako parametr domknięcia

    # Uruchomienie głównej pętli programu OpenGL
    glutMainLoop()

    

if __name__ == "__main__":
    main()