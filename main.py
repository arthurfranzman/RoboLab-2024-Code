#!/usr/bin/env python3
import time
# generelle imports
from queue import Queue
from typing import Optional

# Communication-Imports
import ev3dev.ev3 as ev3
import os
import logging
import paho.mqtt.client as mqtt
import uuid
import signal

# Klassen-Imports
from communication import Communication
from movement import Movement
from planet import Direction, Planet
# from odometry import Odometry

client = None  # DO NOT EDIT
# benötigte Variablen
mission_completed = False
target_queue = Queue()
on_node = True
current_x = 0
current_y = 0
next_direction = Direction.NORTH
unveiled_start_x = 0
unveiled_start_y = 0
unveiled_start_direction = Direction.NORTH
unveiled_end_x = 0
unveiled_end_y = 0
unveiled_end_direction = Direction.NORTH
unveiled_path_status = "free"
unveiled_path_weight = 0
target_x = None
target_y = None
calculated_path: Optional[list[tuple[tuple[int, int], Direction]]]
current_path_start_direction = Direction.NORTH
current_path_start_x = 0
current_path_start_y = 0
current_path_end_x = 0
current_path_end_y = 0
current_path_end_direction = Direction.SOUTH
current_path_status = "free"
current_path_weight = 0
current_orientation = Direction.NORTH

has_commanded_direction = False
communication = None
test_mode = False
planet = Planet()
movement = Movement()


# noinspection PyTypeChecker
def run():
    # DO NOT CHANGE THESE VARIABLES
    #
    # The deploy-script uses the variable "client" to stop the mqtt-client after your program stops or crashes.
    # Your script isn't able to close the client after crashing.
    global client, mission_completed, next_direction, on_node, has_commanded_direction
    global communication, planet, calculated_path, current_path_start_direction, current_path_end_direction
    global current_path_status, current_path_start_x, current_path_start_y, current_orientation, current_path_end_x
    global current_path_end_y

    client_id = '127-' + str(uuid.uuid4())  # Replace YOURGROUPID with your group ID
    client = mqtt.Client(client_id=client_id,  # Unique Client-ID to recognize our program
                         clean_session=True,  # We want a clean session after disconnect or abort/crash
                         protocol=mqtt.MQTTv311)  # Define MQTT protocol version
    # callback_api_version=mqtt.CallbackAPIVersion.VERSION2) muss hier raus, obwohl es als Fehler angezeigt wird bei macOS
    # Setup logging directory and file
    curr_dir = os.path.abspath(os.getcwd())
    if not os.path.exists(curr_dir + '/../logs'):
        os.makedirs(curr_dir + '/../logs')
    log_file = curr_dir + '/../logs/project.log'
    logging.basicConfig(filename=log_file,  # Define log file
                        level=logging.DEBUG,  # Define default mode
                        format='%(asctime)s: %(message)s'  # Define default logging format
                        )
    logger = logging.getLogger('RoboLab')
    # THE EXECUTION OF ALL CODE SHALL BE STARTED FROM WITHIN THIS FUNCTION.
    # ADD YOUR OWN IMPLEMENTATION HEREAFTER.
    communication = Communication(client, logger)
    movement.linefollow()
    if test_mode:
        communication.current_planet = input('Aktueller Planet:')
        communication.send_testplanet()
        time.sleep(0.5)
    communication.send_ready()
    time.sleep(0.5)
    analyze_messages(communication)
    try:
        while not mission_completed:
            if not movement.to_start_node:
                if not movement.obstacle:
                    communication.send_path(current_path_start_x, current_path_start_y, int(current_path_start_direction), current_x, current_y, int(current_path_end_direction), movement.current_path_status)
                else:
                    current_path_end_x = current_path_start_x
                    current_path_end_y = current_path_start_y
                    current_path_end_direction = (int(current_path_start_direction) - 180) % 360
                    communication.send_path(current_path_start_x, current_path_start_y, int(current_path_start_direction), current_path_end_x, current_path_end_y, int(current_path_start_direction), movement.current_path_status)
            time.sleep(0.5)
            analyze_messages(communication)
            print(planet.get_paths().keys())
            # schon bekannte Pfade dürften nicht hinzugefügt werden, das müsste hier geprüft werden
            if (current_x, current_y) not in planet.visited_nodes.keys():
                directions_list = planet.check_paths((current_x, current_y), list(movement.node_scan(current_orientation)))
                planet.add_directions((current_x, current_y), directions_list)
                planet.visited_nodes[(current_x, current_y)] = True
                print(planet.visited_nodes.keys())
            next_direction = planet.next_unexplored_node_and_direction((current_x, current_y))
            if next_direction is None:
                movement.tetris()
                break
            communication.send_pathselect(current_x, current_y, int(next_direction))
            start_time = time.time()
            while True:
                current_time = time.time()
                analyze_messages(communication)
                if (current_time - start_time) > 3:
                    print('3 sek vergangen')
                    break
            ev3.Sound.beep()
            if not has_commanded_direction:
                if target_reachable():  # Zielmodus
                    if (current_x, current_y) == (target_x, target_y):
                        print('1130')
                        movement.tetris()
                        break
                    print('1110')
                    calculated_path = planet.shortest_path((current_x, current_y), (target_x, target_y))
                    print(calculated_path)
                    try:
                        next_direction = calculated_path[0][1]
                    except TypeError:
                        print(calculated_path)
                else:  # Erkundungsmodus
                    next_direction = planet.next_unexplored_node_and_direction((current_x, current_y))
                    # print('1117')
                    if next_direction is None:
                        movement.tetris()
                        break
            # vor dem Turn
            planet.update_certain(next_direction, (current_x, current_y))
            has_commanded_direction = False
            print(f'next_direction: {next_direction}')
            if not movement.to_start_node:
                print(current_path_end_direction)
                current_orientation = (int(current_path_end_direction) + 180) % 360
                print(current_orientation)
            current_path_start_direction = next_direction
            current_path_start_x = current_x
            current_path_start_y = current_y
            # Turn und dann linefollow
            movement.turn(next_direction, current_orientation)
            current_path_status = movement.linefollow()
            movement.to_start_node = False
    finally:
        client.loop_stop()
        client.disconnect()
        print("Verbindung wird geschlossen, Programm wird beendet!")


# noinspection PyTypeChecker
def target_reachable():
    """
        Checks if the target is either the current node, not reachable, or reachable.
        :return: bool - True if reachable or current node, false if not
        """
    global calculated_path, target_queue, mission_completed, planet
    if target_x is not None and target_y is not None:
        calculated_path = planet.shortest_path((current_x, current_y), (target_x, target_y))
        if calculated_path is None:
            print('target ist noch nicht erkundet worden.')
            return False
        else:  # wenn Ziel erreichbar
            return True
    else:
        return False


# noinspection PyTypeChecker
def analyze_messages(comm):
    """
        Checks the incoming messages and if necessary, sends messages back via the communication.py class
        :param comm: Communication() Class instance
        :return: void
        """
    global current_x, current_y, unveiled_start_x
    global unveiled_start_y, unveiled_start_direction, unveiled_end_x, unveiled_end_y, unveiled_end_direction
    global unveiled_path_status, unveiled_path_weight, target_x, target_y, mission_completed, next_direction
    global current_path_start_x, current_path_start_y, current_path_start_direction, current_path_end_x
    global current_path_end_y, current_path_end_direction, current_path_weight, current_path_status
    global planet, has_commanded_direction, current_orientation
    while comm.q.qsize() > 0:
        received_message = comm.q.get()
        if received_message['from'] == 'server' and received_message['type'] == 'planet':
            current_x, current_y, current_orientation = comm.receive_ready(received_message)
            current_orientation = planet.convert_direction(current_orientation)
        elif received_message['from'] == 'server' and received_message['type'] == 'path':
            current_path_start_x, current_path_start_y, current_path_start_direction, current_x, current_y, current_path_end_direction, current_path_status, current_path_weight = comm.receive_path(received_message)
            current_orientation = planet.convert_direction(int(current_path_end_direction - 180) % 360)
            planet.add_path(((current_path_start_x, current_path_start_y), planet.convert_direction(current_path_start_direction)),
                            ((current_x, current_y), planet.convert_direction(current_path_end_direction)), current_path_weight)
            print('path-Nachricht eingelesen.')
        elif received_message['from'] == 'server' and received_message['type'] == 'pathSelect':
            has_commanded_direction = True
            next_direction = comm.receive_pathselect(received_message)
            print('pathSelect-Nachricht eingelesen.')
        elif received_message['from'] == 'server' and received_message['type'] == 'pathUnveiled':
            unveiled_start_x, unveiled_start_y, unveiled_start_direction, unveiled_end_x, unveiled_end_y, unveiled_end_direction, unveiled_path_status, unveiled_path_weight = comm.receive_pathunveiled(received_message)
            print(unveiled_path_status)
            if (unveiled_start_x, unveiled_start_y) not in planet.unexplored_nodes:
                planet.unexplored_nodes.insert(0, (unveiled_start_x, unveiled_start_y))
            if (unveiled_end_x, unveiled_end_y) not in planet.unexplored_nodes:
                planet.unexplored_nodes.insert(0, (unveiled_end_x, unveiled_end_y))
            if unveiled_path_status == "free":
                planet.add_path(((unveiled_start_x, unveiled_start_y), planet.convert_direction(unveiled_start_direction)), ((unveiled_end_x, unveiled_end_y), planet.convert_direction(unveiled_end_direction)), unveiled_path_weight)
                planet.update_direction((unveiled_start_x, unveiled_start_y), [planet.convert_direction(unveiled_start_direction)])
                planet.update_direction((unveiled_end_x, unveiled_end_y), [planet.convert_direction(unveiled_end_direction)])
                if (current_path_start_x, current_path_start_y) in planet.visited_nodes.keys():
                    planet.pop_from_stack((current_path_start_x, current_path_start_y))
                if (current_path_end_x, current_path_end_y) in planet.visited_nodes.keys():
                    planet.pop_from_stack((current_path_end_x, current_path_end_y))
            elif unveiled_path_status == "blocked":
                planet.add_path(((unveiled_start_x, unveiled_start_y), planet.convert_direction(unveiled_start_direction)), ((unveiled_end_x, unveiled_end_y), planet.convert_direction(unveiled_end_direction)), unveiled_path_weight)
                planet.update_direction((unveiled_start_x, unveiled_start_y), [planet.convert_direction(unveiled_start_direction)])
                planet.update_direction((unveiled_end_x, unveiled_end_y), [planet.convert_direction(unveiled_end_direction)])
                if (current_path_start_x, current_path_start_y) in planet.visited_nodes.keys():
                    planet.pop_from_stack((current_path_start_x, current_path_start_y))
                if (current_path_end_x, current_path_end_y) in planet.visited_nodes.keys():
                    planet.pop_from_stack((current_path_end_x, current_path_end_y))
            else:
                print('fehler bei pathUnveiled-Nachricht: der Status entspricht nicht \"free\"|\"blocked\".')
            print('pathUnveiled-Nachricht eingelesen.')
        elif received_message['from'] == 'server' and received_message['type'] == 'target':
            target_x, target_y = comm.receive_target(received_message)
            print('target-Nachricht eingelesen.')
        elif received_message['from'] == 'server' and received_message['type'] == 'done':
            completion_message = comm.receive_complete(received_message)
            print(f'completion-Nachricht eingelesen: {completion_message}')
            mission_completed = True
        elif received_message['from'] == 'debug':
            pass
        else:
            print(f'Fehler in Analyse von Nachrichten: Falscher Nachrichtentyp. Entspricht nicht \"testplanet\", \"ready\", usw:\n\n{received_message}')


# DO NOT EDIT
# noinspection PyUnusedLocal
def signal_handler(sig=None, frame=None, raise_interrupt=True):
    if client and client.is_connected():
        client.disconnect()
    if raise_interrupt:
        raise KeyboardInterrupt()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    try:
        run()
        signal_handler(raise_interrupt=False)
    except Exception as e:
        signal_handler(raise_interrupt=False)
        raise e
