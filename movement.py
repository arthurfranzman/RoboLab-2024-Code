# EV3 Imports
import math

import ev3dev.ev3 as ev3
from ev3dev.ev3 import Button

from planet import Planet
from odometry import Odometry

import time
import json


class Movement:
    """
        Class which does all the movement tasks.
        """

    def __init__(self):
        """
            Initializes the data structure of the movement class with color sensor, motor and linefollow values.
            :return: void
            """
        # linefollow-Initialisierung
        # Bauteile
        self.cs = ev3.ColorSensor()
        self.cs.mode = 'RGB-RAW'
        self.us = ev3.UltrasonicSensor()
        self.us.mode = 'US-DIST-CM'
        self.lm = ev3.LargeMotor("outC")
        self.rm = ev3.LargeMotor("outB")
        self.btn = Button()
        self.obstacle = False
        self.current_path_status = "free"
        self.odometry = Odometry()
        # Farbkalibrierung
        self.off1 = 60  # Richtwert Rot
        self.off2 = 85  # Richtwert Grün
        self.off3 = 60  # Richtwert Blau
        # PID Values
        self.kp = 100
        self.ki = 10
        self.kd = 130
        self.tp = 160  # normale Basisgeschwindigkeit
        self.abweichung = 15
        self.to_start_node = True
        self.cal_instance = self.calibrate()

    def linefollow(self):
        """
            Main linefollow of the robot. Follows the line based on PID Controller.
            :return current_path_status: bool, returns whether an obstacle has been detected.
            """
        self.obstacle = False
        ev3.Sound.set_volume(100)
        integral = 0
        lasterror = 0
        self.current_path_status = "free"
        while not self.btn.any():
            # Hinderniserkennung
            if self.us.value() <= 90:  # falls ein Hindernis 9 cm entfernt ist
                self.obstacle = True
                self.turnaround()
                self.current_path_status = "blocked"
            # Auslesen der RBG Werte
            value1 = self.cs.red
            value2 = self.cs.green
            value3 = self.cs.blue
            # wenn auf einem roten Knoten
            if (value1 >= (self.cal_instance["red_calibrate_values"]["min_red"] - self.abweichung)) and (
                    (self.cal_instance["red_calibrate_values"]["max_green"] + self.abweichung) >= value2) and (
                    (self.cal_instance["red_calibrate_values"]["max_blue"] + self.abweichung) >= value3):
                self.lm.stop()
                self.rm.stop()
                if self.obstacle:
                    ev3.Sound.beep()
                    time.sleep(0.5)
                    ev3.Sound.beep()
                self.lm.run_to_rel_pos(position_sp=135, speed_sp=100)
                self.rm.run_to_rel_pos(position_sp=135, speed_sp=100)
                self.lm.wait_while('running')
                self.rm.wait_while('running')
                break
            # wenn auf einem blauen Knoten
            if (self.cal_instance["blue_calibrate_values"]["max_red"] + self.abweichung >= value1) and (
                    value2 >= self.cal_instance["blue_calibrate_values"]["min_green"] - self.abweichung) and (
                    value3 >= self.cal_instance["blue_calibrate_values"]["min_blue"] - self.abweichung):
                self.lm.stop()
                self.rm.stop()
                if self.obstacle:
                    ev3.Sound.beep()
                    time.sleep(0.5)
                    ev3.Sound.beep()
                self.lm.run_to_rel_pos(position_sp=135, speed_sp=100)
                self.rm.run_to_rel_pos(position_sp=135, speed_sp=100)
                self.lm.wait_while('running')
                self.rm.wait_while('running')
                break
            # eigentliche Linienverfolgung:
            # Berechnung der Abweichungen
            error1 = value1 - self.off1
            error2 = value2 - self.off2
            error3 = value3 - self.off3
            # Berechnung der mittleren Abweichung
            merror = round((error1 + error2 + error3) / 3)
            # Änderung der Variablen I und D
            integral = integral + merror
            if integral > 1500:
                integral = 1500
            elif integral < -1500:
                integral = -1500
            derivative = merror - lasterror
            # Berechnung der Geschwindigkeitsänderung
            motor_turn = self.kp * merror + self.ki * integral + self.kd * derivative
            motor_turn = motor_turn / 100
            # Übertragung und Ausführung auf die Motoren
            powerl = self.tp + motor_turn
            powerr = self.tp - motor_turn
            self.lm.run_forever(speed_sp=powerl, stop_action="brake")
            self.rm.run_forever(speed_sp=powerr, stop_action="brake")
            lasterror = merror
            # self.odometry.pos_update()
            # print(f'x:     {self.odometry.final_x * 0.05}, y:     {self.odometry.final_y * 0.05}')
        return self.current_path_status

    def node_scan(self, current_orientation):
        """
            Scans paths of the current node and returns them in a list.
            :param current_orientation: Direction Class Enum value, which stores the current position,
            which helps us determine the angle to the next path to take
            :return: list with the yet to be discovered paths from this node.
            """
        self.cs.mode = 'RGB-RAW'
        self.lm.stop()
        self.rm.stop()
        self.lm.position = 0
        self.rm.position = 0
        original_orientation = Planet().convert_direction(current_orientation)
        orientation_one = None
        orientation_three = None
        orientation_four = None
        unvisited_directions_list = []
        while True:
            self.lm.run_to_rel_pos(position_sp=1500, speed_sp=150, stop_action='brake')
            self.rm.run_to_rel_pos(position_sp=-1500, speed_sp=150, stop_action='brake')
            if self.cs.red <= 80 and self.cs.blue <= 80:
                if 250 > self.lm.position >= 83 and orientation_one is None:
                    orientation_one = Planet().convert_direction((int(original_orientation) + 90) % 360)
                    unvisited_directions_list.append(orientation_one)
                if 581 > self.lm.position >= 415 and orientation_three is None:
                    orientation_three = Planet().convert_direction((int(original_orientation) + 270) % 360)
                    unvisited_directions_list.append(orientation_three)
                if 747 > self.lm.position >= 581 and orientation_four is None:
                    orientation_four = Planet().convert_direction(int(original_orientation) % 360)
                    unvisited_directions_list.append(orientation_four)
            if self.lm.position >= 1245 and self.cs.red <= 80 and self.cs.blue <= 80:  # 913
                self.lm.stop()
                self.rm.stop()
                print(f'node scan mit linienerkennung - motorposition: {self.lm.position}, und farben - rot: {self.cs.red} und blau: {self.cs.blue}')
                break
            elif self.lm.position >= 1330:
                self.lm.stop()
                self.rm.stop()
                print(f'node scan mit motorposition - motorposition: {self.lm.position}')
                break
        return unvisited_directions_list

    # Drehung an einem Hindernis
    def turnaround(self):
        """
            Method which turns the robot around after detecting an obstacle in the linefollow method.
            reads the color values, making it more accurate on the line after turning.
            :return: void
            """
        self.lm.position = 0
        self.rm.position = 0
        while True:
            self.lm.run_to_rel_pos(position_sp=415, speed_sp=150, stop_action='brake')
            self.rm.run_to_rel_pos(position_sp=-415, speed_sp=150, stop_action='brake')
            if self.cs.red <= 80 and self.cs.blue <= 80:
                if 415 > self.lm.position >= 250:
                    self.lm.stop()
                    self.rm.stop()
                    break

    def turn(self, next_direction, current_orientation):
        """
            Method which turns to the corresponding required position. Very accurate because of
            checking both the motor position and the color readings.
            :param next_direction: next direction to turn the robot to
            :param current_orientation: the current position, which helps determine how to turn the robot.
            :return: void
            """
        self.lm.position = 0
        self.rm.position = 0
        turn_angle = (int(next_direction) - int(current_orientation)) % 360
        if turn_angle == 90:
            while True:
                self.lm.run_to_rel_pos(position_sp=250, speed_sp=150, stop_action='brake')
                self.rm.run_to_rel_pos(position_sp=-250, speed_sp=150, stop_action='brake')
                if self.cs.red <= 80 and self.cs.blue <= 80:
                    if 250 > self.lm.position >= 83:
                        self.lm.stop()
                        self.rm.stop()
                        break
        elif turn_angle == 180:
            while True:
                self.lm.run_to_rel_pos(position_sp=415, speed_sp=150, stop_action='brake')
                self.rm.run_to_rel_pos(position_sp=-415, speed_sp=150, stop_action='brake')
                if self.cs.red <= 80 and self.cs.blue <= 80:
                    if 415 > self.lm.position >= 250:
                        self.lm.stop()
                        self.rm.stop()
                        break
        elif turn_angle == 270:
            while True:
                self.lm.run_to_rel_pos(position_sp=-250, speed_sp=150, stop_action='brake')
                self.rm.run_to_rel_pos(position_sp=250, speed_sp=150, stop_action='brake')
                if self.cs.red <= 80 and self.cs.blue <= 80:
                    if -250 < self.lm.position <= -83:
                        self.lm.stop()
                        self.rm.stop()
                        break

    def tetris(self):
        """
            Method which plays the original tetris theme in 8-bit version with full volume as it should be.
            :return: void
            """
        ev3.Sound.set_volume(100)
        ev3.Sound.play('tetris-mono-32.wav').wait()

    def read_color_values(self):
        """
            Originally used to determine the current color values of the ev3 Color Sensor.
            :return: void
            """
        print(self.cs.red)
        print(self.cs.green)
        print(self.cs.blue)

    def calibrate(self):
        """
            Calibrates the current color values by measuring ten sample values. saving them in a dict.
            node recognition of the linefollow will automatically adjust to the color calibration.
            :return: Dictionary with the min and max values of rgb of the blue and the red values.
            """
        calibration_data = {}
        counter = 0
        red_calibrate_values = {"red": [], "green": [], "blue": []}
        red_calibrate = input('press enter to calibrate red:')
        if red_calibrate == "":
            while counter < 11:
                red_calibrate_values["red"].append(self.cs.red)
                red_calibrate_values["green"].append(self.cs.green)
                red_calibrate_values["blue"].append(self.cs.blue)
                time.sleep(0.05)
                counter += 1
            calibration_data["red_calibrate_values"] = {"min_red": int(min(red_calibrate_values["red"])),
                                                        "max_red": int(max(red_calibrate_values["red"])),
                                                        "min_green": int(min(red_calibrate_values["green"])),
                                                        "max_green": int(max(red_calibrate_values["green"])),
                                                        "min_blue": int(min(red_calibrate_values["blue"])),
                                                        "max_blue": int(max(red_calibrate_values["blue"]))}
        ev3.Sound.beep()
        counter = 0
        blue_calibrate_values = {"red": [], "blue": [], "green": []}
        blue_calibrate = input('press enter to calibrate blue:')
        if blue_calibrate == "":
            while counter < 11:
                blue_calibrate_values["red"].append(self.cs.red)
                blue_calibrate_values["green"].append(self.cs.green)
                blue_calibrate_values["blue"].append(self.cs.blue)
                time.sleep(0.05)
                counter += 1
            calibration_data["blue_calibrate_values"] = {"min_red": int(min(blue_calibrate_values["red"])),
                                                         "max_red": int(max(blue_calibrate_values["red"])),
                                                         "min_green": int(min(blue_calibrate_values["green"])),
                                                         "max_green": int(max(blue_calibrate_values["green"])),
                                                         "min_blue": int(min(blue_calibrate_values["blue"])),
                                                         "max_blue": int(max(blue_calibrate_values["blue"]))}
            ev3.Sound.beep()
            print('3...')
            time.sleep(0.9)
            ev3.Sound.beep()
            print('2...')
            time.sleep(0.9)
            ev3.Sound.beep()
            print('1...')
            time.sleep(0.9)
            ev3.Sound.play_song((
                ('E4', 'e3'),
                ('E4', 'e3'),
                ('A4', 'h')))
            print('GO!')
        return calibration_data
