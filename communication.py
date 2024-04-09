#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import json
import ssl
from queue import Queue


# noinspection PyMethodMayBeStatic
class Communication:
    """
    Class to hold the MQTT client communication
    Feel free to add functions and update the constructor to satisfy your requirements and
    thereby solve the task according to the specifications
    """
    # DO NOT EDIT THE METHOD SIGNATURE
    def __init__(self, mqtt_client, logger):
        """
        Initializes communication module, connect to server, subscribe, etc.
        :param mqtt_client: paho.mqtt.client.Client
        :param logger: logging.Logger
        """
        # DO NOT CHANGE THE SETUP HERE
        self.client = mqtt_client
        self.client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        self.client.on_message = self.safe_on_message_handler
        # Add your client setup here
        self.client.username_pw_set(username='127',
                                    password='some password...')
        # Your group credentials, see the python skill-test for your group password
        self.client.connect(host='host of the project', port='corresponding port')
        self.client.subscribe(topic='explorer/127', qos=2)
        self.client.subscribe(topic='comtest/127', qos=2)
        self.logger = logger
        self.client.loop_start()
        self.q = Queue()
        self.current_planet = ""

    # DO NOT EDIT THE METHOD SIGNATURE
    # noinspection PyUnusedLocal
    def on_message(self, client, data, message):
        """
            Handles the callback if any message arrived
            :param client: paho.mqtt.client.Client
            :param data: Object
            :param message: Object
            :return: void
            """
        payload = json.loads(message.payload.decode('utf-8'))
        self.logger.debug(json.dumps(payload, indent=2))

        # YOUR CODE FOLLOWS (remove pass, please!)
        json_dict = json.loads(message.payload.decode('utf-8'))
        if json_dict['from'] == 'debug' and json_dict['from'] != 'adjust':
            print(f'{json_dict} empfangen!')
        if json_dict['from'] != 'client':
            self.q.put(json_dict)

    # DO NOT EDIT THE METHOD SIGNATURE
    #
    # In order to keep the logging working you must provide a topic string and
    # an already encoded JSON-Object as message.

    def send_message(self, topic, message):
        """
            Sends given message to specified channel
            :param topic: String
            :param message: Object
            :return: void
            """
        self.logger.debug('Send to: ' + topic)
        self.logger.debug(json.dumps(message, indent=2))

        # YOUR CODE FOLLOWS (remove pass, please!)
        self.client.publish(topic=topic, payload=message)

    # DO NOT EDIT THE METHOD SIGNATURE OR BODY
    #
    # This helper method encapsulated the original "on_message" method and handles
    # exceptions thrown by threads spawned by "paho-mqtt"
    def safe_on_message_handler(self, client, data, message):
        """
            Handle exceptions thrown by the paho library
            :param client: paho.mqtt.client.Client
            :param data: Object
            :param message: Object
            :return: void
            """
        try:
            self.on_message(client, data, message)
        except:
            import traceback
            traceback.print_exc()
            raise

    def send_testplanet(self, comtest=False):
        """
            Sends a testPlanet message based on a specified current_planet variable
            :param comtest: bool, enables comtest-mode
            :return: void
            """
        if comtest:
            self.send_message(topic='comtest/127', message='{"from": "client","type": "testPlanet","payload": {"planetName": "%s"}}' % self.current_planet)
        else:
            self.send_message(topic='explorer/127', message='{"from": "client","type": "testPlanet","payload": {"planetName": "%s"}}' % self.current_planet)

    def send_ready(self, comtest=False):
        """
            Sends a ready message to indicate that the robot is ready.
            :param comtest: bool, enables comtest-mode
            :return: void
            """
        if comtest:
            self.send_message(topic='comtest/127', message='{"from": "client","type": "ready"}')
        else:
            self.send_message(topic='explorer/127', message='{"from": "client","type": "ready"}')

    def receive_ready(self, message):
        """
            Receives the ready answer from the server with the corresponding planet name.
            :param message: String, the message itself
            :return: start_x, start_y, start_orientation
            """
        self.current_planet = message['payload']['planetName']
        print(self.current_planet)
        start_x = message['payload']['startX']
        start_y = message['payload']['startY']
        start_orientation = message['payload']['startOrientation']
        self.client.subscribe(topic=f'planet/{self.current_planet}/127', qos=2)
        return start_x, start_y, start_orientation

    def send_path(self, start_coordinates_x, start_coordinates_y, start_orientation, current_coordinates_x, current_coordinates_y, current_orientation, path_status, comtest=False):
        """
            Sends a path message to transmit the driven path.
            :param start_coordinates_x: String, x-coordinate of path start
            :param start_coordinates_y: String, y-coordinate of path start
            :param start_orientation: String, orientation of the path start
            :param current_coordinates_x: String, x-coordinate of path end
            :param current_coordinates_y: String, y-coordinate of path end
            :param current_orientation: String, orientation of the path end
            :param path_status: String "free|blocked", status whether the path is free or blocked
            :param comtest: bool, enables comtest-mode
            :return: void
            """
        if comtest:
            self.send_message(topic=f'comtest/{self.current_planet}/127', message='{"from": "client","type":"path","payload": {"startX": %s,"startY": %s,"startDirection": %s, "endX": %s, "endY": %s, "endDirection": %s, "pathStatus": "%s"}}' % (start_coordinates_x, start_coordinates_y, start_orientation, current_coordinates_x, current_coordinates_y, current_orientation, path_status))
        else:
            self.send_message(topic=f'planet/{self.current_planet}/127', message='{"from": "client","type":"path","payload": {"startX": %s,"startY": %s,"startDirection": %s, "endX": %s, "endY": %s, "endDirection": %s, "pathStatus": "%s"}}' % (start_coordinates_x, start_coordinates_y, start_orientation, current_coordinates_x, current_coordinates_y, current_orientation, path_status))

    def receive_path(self, message):
        """
            Receives the answer from the server regarding the sent message, potentially with corrected path end coordinates or direction
            :param message: String, the message itself
            :return: current_x, current_y, current_orientation, end_x, end_y, end_orientation, path_weight
            """
        start_x = message['payload']['startX']
        start_y = message['payload']['startY']
        start_orientation = message['payload']['startDirection']
        end_x = message['payload']['endX']
        end_y = message['payload']['endY']
        end_orientation = message['payload']['endDirection']
        path_status = message['payload']['pathStatus']
        path_weight = message['payload']['pathWeight']
        return start_x, start_y, start_orientation, end_x, end_y, end_orientation, path_status, path_weight

    def send_pathselect(self, current_coordinates_x, current_coordinates_y, start_direction, comtest=False):
        """
            Sends a pathselect message to convey the next direction driven.
            :param current_coordinates_x: String, x-coordinate of next chosen path
            :param current_coordinates_y: String, y-coordinate of next chosen path
            :param start_direction: String, orientation from current node to next chosen path
            :param comtest: bool, enables comtest-mode
            :return: void
            """
        if comtest:
            self.send_message(topic=f'comtest/{self.current_planet}/127', message='{"from": "client","type": "pathSelect","payload": {"startX": %s,"startY": %s,"startDirection": %s}}' % (current_coordinates_x, current_coordinates_y, start_direction))
        else:
            self.send_message(topic=f'planet/{self.current_planet}/127', message='{"from": "client","type": "pathSelect","payload": {"startX": %s,"startY": %s,"startDirection": %s}}' % (current_coordinates_x, current_coordinates_y, start_direction))

    def receive_pathselect(self, message):
        """
            Receives the potential pathSelect-message which tells the robot which direction to take next
            :param message: String, the message itself
            :return current_orientation: integer
            """
        current_orientation = message['payload']['startDirection']
        return current_orientation

    def receive_pathunveiled(self, message):
        """
            Receives the potential pathUnveiled-message which unveils a path
            on the map as either free or blocked - with coordinates and direction
            :param message: String, the message itself
            :return: unveiled_start_x,  unveiled_start_y, unveiled_start_orientation, unveiled_end_x, unveiled_end_y,
            unveiled_end_orientation, unveiled_path_status, unveiled_path_weight
            """
        unveiled_start_x = message['payload']['startX']
        unveiled_start_y = message['payload']['startY']
        unveiled_start_orientation = message['payload']['startDirection']
        unveiled_end_x = message['payload']['endX']
        unveiled_end_y = message['payload']['endY']
        unveiled_end_orientation = message['payload']['endDirection']
        unveiled_path_status = message['payload']['pathStatus']
        unveiled_path_weight = message['payload']['pathWeight']
        return unveiled_start_x, unveiled_start_y, unveiled_start_orientation, unveiled_end_x, unveiled_end_y, unveiled_end_orientation, str(unveiled_path_status), unveiled_path_weight,

    def receive_target(self, message):
        target_coordinates_x = message['payload']['targetX']
        target_coordinates_y = message['payload']['targetY']
        return target_coordinates_x, target_coordinates_y

    def send_target_reached(self, target_reached_response, comtest=False):
        """
            Sends a target-reached-message to indicate that the given target has been reached.
            :param target_reached_response: String, message to embed in the emitted response to the server
            :param comtest: bool, enables comtest-mode
            """
        if comtest:
            self.send_message(topic='comtest/127', message='{"from": "client","type": "targetReached","payload": {"message": "' + target_reached_response + '"}}')
        else:
            self.send_message(topic='explorer/127', message='{"from": "client","type": "targetReached","payload": {"message": "' + target_reached_response + '"}}')

    def send_exploration_completed(self, exploration_completed_response, comtest=False):
        """
            Sends an exploration-completed message to indicate that the planet has been fully explored.
            :param exploration_completed_response: String, message to embed in the emitted response to the server
            :param comtest: bool, enables comtest-mode
            """
        if comtest:
            self.send_message(topic='comtest/127', message='{"from": "client","type": "explorationCompleted","payload": {"message": "' + exploration_completed_response + '"}}')
        else:
            self.send_message(topic='explorer/127', message='{"from": "client","type": "explorationCompleted","payload": {"message": "' + exploration_completed_response + '"}}')

    def receive_complete(self, message):
        """
            Receives the complete-message which confirms the mission is completed.
            :param message: String, the message itself
            :return: void
            """
        completion_message = message['payload']['message']
        return completion_message
