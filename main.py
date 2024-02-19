"""Main file - multi threading implemented to run multiple camera feeds at once"""
import threading
import cv2
import mediapipe as mp
# import hand_pose_estimation
# import face_pose_estimation
# import display
from threading import Thread
import time
import cv2
import dlib


import numpy as np

a = 0
eyelid_state = 0


def face_pose_analysis() -> None:
    """analysis for face pose estimation

    Args:
        mp_face_mesh (_type_): _description_
        cap (_type_): _description_
        mp_drawing (_type_): _description_
        mp_drawing_styles (_type_): _description_
    """
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    mp_face_mesh = mp.solutions.face_mesh

    drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
    cap = cv2.VideoCapture(0)
    global face_pose_x

    global a
    # DETECT THE FACE LANDMARKS
    with mp_face_mesh.FaceMesh\
        (min_detection_confidence=0.7, min_tracking_confidence=0.7) as face_mesh:
        while True:
            success, image = cap.read()
            # Flip the image horizontally and convert the color space from BGR to RGB
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            # To improve performance
            image.flags.writeable = False
            # Detect the face landmarks
            results = face_mesh.process(image)
            # To improve performance
            image.flags.writeable = True
            # Convert back to the BGR color space
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            img_h, img_w, img_c = image.shape
            face_3d = []
            face_2d = []
            # Draw the face mesh annotations on the image.
            if results.multi_face_landmarks:
                for face_landmarks in results.multi_face_landmarks:
                    for idx, lm in enumerate(face_landmarks.landmark):
                        if idx == 33 or idx == 263 or idx == 1 \
                            or idx == 61 or idx == 291 or idx == 199:
                            if idx ==1:
                                nose_2d = (lm.x * img_w, lm.y * img_h)
                                nose_3d = (lm.x * img_w, lm.y * img_h, lm.z * 3000)
                            x_point, y_point = int(lm.x * img_w), int(lm.y * img_h)

                            #Get the 2d coordinates
                            face_2d.append([x_point,y_point])

                            #3d coordinates
                            face_3d.append([x_point,y_point, lm.z])
                    face_2d = np.array(face_2d, dtype=np.float64)
                    face_3d = np.array(face_3d, dtype=np.float64)

                    #The camera matrix
                    focal_length = 1 * img_w

                    cam_matrix = np.array([ [focal_length, 0, img_h / 2],
                                            [0, focal_length, img_w / 2],
                                            [0, 0, 1]])
                    dist_matrix = np.zeros((4,1), dtype=np.float64)
                    success, rot_vec, trans_vec = cv2.solvePnP\
                        (face_3d, face_2d, cam_matrix, dist_matrix)
                    rmat, jac = cv2.Rodrigues(rot_vec)
                    angles, mtxR, mtxQ, Qx, Qy, Qz = cv2.RQDecomp3x3(rmat)

                    x = angles[0] * 360
                    y = angles[1] * 360
                    z = angles[2] * 360

                    face_pose_x = angles[0] * 360

                    # a = [x,y,z]

                    # print(nose_2d)

                    if y < -10:
                        # print('looking left')
                        a = 'looking left'
                    elif y > 10:
                        # print('looking right')
                        a = 'looking right'
                    elif x < -10:
                        # print('looking down')
                        a ='looking down'
                    elif x > 10:
                        # print('looking up')
                        a = 'looking up'
                    else:
                        # print('looking forward')
                        a = 'looking forward'
                    nose_3d_projection, jacobian = cv2.projectPoints\
                        (nose_3d, rot_vec, trans_vec, cam_matrix, dist_matrix)

                    point_1 = (int(nose_2d[0]), int(nose_2d[1]))
                    point_2 = (int(nose_2d[0] + y * 10), int(nose_2d[1] - x * 10))
                    cv2.line(image, point_1, point_2, (255,0,0), 3)
                    mp_drawing.draw_landmarks(
                        image=image,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles
                        .get_default_face_mesh_tesselation_style())

            # Display the image
            cv2.imshow('face pose estimation', image)
            # Terminate the process
            if cv2.waitKey(5) & 0xFF == 27:
                break

def eyelid_detection():
    # Initialize the face detector and shape predictor
    detector = dlib.get_frontal_face_detector()
    predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

    # Function to calculate the eye aspect ratio (EAR)
    def eye_aspect_ratio(eye):
        # Compute the euclidean distances between the two sets of vertical eye landmarks
        A = ((eye[1][0] - eye[5][0])**2 + (eye[1][1] - eye[5][1])**2)**0.5
        B = ((eye[2][0] - eye[4][0])**2 + (eye[2][1] - eye[4][1])**2)**0.5
        # Compute the euclidean distance between the horizontal eye landmark
        C = ((eye[0][0] - eye[3][0])**2 + (eye[0][1] - eye[3][1])**2)**0.5
        # Compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)
        return ear

    # Load the webcam
    cap = cv2.VideoCapture(0)

    # global variable eyelidstate
    global eyelid_state

    while True:
        # Read a frame from the webcam
        ret, frame = cap.read()
        if not ret:
            break

        # Convert the frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect faces in the grayscale frame
        faces = detector(gray)

        for face in faces:
            # Predict facial landmarks
            shape = predictor(gray, face)
            shape = [(shape.part(i).x, shape.part(i).y) for i in range(68)]

            # Extract left and right eye landmarks
            left_eye = shape[36:42]
            right_eye = shape[42:48]

            # Calculate eye aspect ratio (EAR)
            left_ear = eye_aspect_ratio(left_eye)
            right_ear = eye_aspect_ratio(right_eye)

            # Average the EAR of both eyes
            ear = (left_ear + right_ear) / 2.0

            # Draw the detected eyes on the frame
            for (x, y) in left_eye:
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
            for (x, y) in right_eye:
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            # Check if the eye aspect ratio is below the threshold (eyes closed)
            if ear < 0.2:
                eyelid_state = 'Eyes Closed'
                cv2.putText(frame, "Eyes Closed", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                eyelid_state = 'Eyes Open'

        # Display the frame
        cv2.imshow("Frame", frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the webcam and close all windows
    cap.release()
    cv2.destroyAllWindows()


def display():
    # import pygame module in this program
    import pygame
    pygame.init()
    white = (255, 255, 255)
    green = (0, 255, 0)
    blue = (0, 0, 128)
    X = 600
    Y = 400
    display_surface = pygame.display.set_mode((X, Y))
    pygame.display.set_caption('Show Text')
    font = pygame.font.Font('freesansbold.ttf', 32)
    i = 0

    global a
    global eyelid_state

    while True:
        text = font.render(str(a) + ' | ' + str(eyelid_state), True, green, blue)
        textRect = text.get_rect()
        textRect.center = (X // 2, Y // 2)
        
        display_surface.fill(white)
        display_surface.blit(text, textRect)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            # Draws the surface object to the screen.
        pygame.display.update()


# thread1 = cam_thread("face_pose", 0)
# # thread2 = cam_thread("hand_pose", 1)
# thread3 = cam_thread("",0,'1') #display.show()




# thread1 = Thread( target=face_pose_analysis, args=() )
thread2 = Thread( target=eyelid_detection, args=() )
thread3 = Thread( target=display, args=() )

# thread1.start()
thread2.start()
thread3.start()

cap.release()
cv2.destroyAllWindows()