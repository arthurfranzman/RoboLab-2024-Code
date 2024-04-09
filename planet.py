#!/usr/bin/env python3

# Attention: Do not import the ev3dev.ev3 module in this file
import math
from enum import IntEnum, unique
from typing import List, Tuple, Dict, Union, Optional


# @CREDITS: Lea Häusler
# @SOURCE: https://se-gitlab.inf.tu-dresden.de/C0ntroller/tutorbot/-/raw/master/src/planet.py


@unique
class Direction(IntEnum):
    NORTH = 0
    EAST = 90
    SOUTH = 180
    WEST = 270


class Planet:
    """
    Contains the representation of the map and provides certain functions to manipulate or extend
    it according to the specifications
    """
    def __init__(self):
        """ Initializes the data structure """
        self.target = None
        self.path_dict: Dict[Tuple[int, int], Dict[Direction, Tuple[Tuple[int, int], Direction, int]]] = {}
        self.undiscovered_directions = {}
        self.unexplored_nodes = []
        self.visited_nodes: Dict[Tuple[int, int], bool] = {}

    def add_path(self, start: Tuple[Tuple[int, int], Direction], target: Tuple[Tuple[int, int], Direction],
                 weight: int):
        """
         Adds a bidirectional path defined between the start and end coordinates to the map and assigns the weight to it

        Example:
            add_path(((0, 3), Direction.NORTH), ((0, 3), Direction.WEST), 1)
        :param start: 2-Tuple
        :param target:  2-Tuple
        :param weight: Integer
        :return: void
        """
        for point1, point2 in [(start, target), (target, start)]:
            if point1[0] not in self.path_dict.keys():
                value = {point1[1]: (point2[0], point2[1], weight)}
                self.path_dict[point1[0]] = value
            else:
                self.path_dict[point1[0]][point1[1]] = (point2[0], point2[1], weight)

    def get_paths(self) -> Dict[Tuple[int, int], Dict[Direction, Tuple[Tuple[int, int], Direction, int]]]:
        """
        Returns all paths

        Example:
            {
                (0, 3): {
                    Direction.NORTH: ((0, 3), Direction.WEST, 1),
                    Direction.EAST: ((1, 3), Direction.WEST, 2),
                    Direction.WEST: ((0, 3), Direction.NORTH, 1)
                },
                (1, 3): {
                    Direction.WEST: ((0, 3), Direction.EAST, 2),
                    ...
                },
                ...
            }
        :return: Dict
        """
        return self.path_dict

    def shortest_path(self, start: Tuple[int, int], target: Tuple[int, int]) -> Union[None, List[Tuple[Tuple[int, int], Direction]]]:
        """
        Returns the shortest path between two nodes

        Examples:
            shortest_path((0,0), (2,2)) returns: [((0, 0), Direction.EAST), ((1, 0), Direction.NORTH)]
            shortest_path((0,0), (1,2)) returns: None
        :param start: 2-Tuple
        :param target: 2-Tuple
        :return: List[2-Tuple, Direction]
        """
        if start == target:
            return []
        if start not in self.get_paths().keys() or target not in self.get_paths().keys():  # müsste eventuell wieder vor das if statement vorher
            return None

        unvisited_nodes = set(self.get_paths().keys())
        table: Dict[Tuple[int, int], Tuple[int, Tuple[int, int], Direction]] = {start: (0, (0, 0), Direction.NORTH)}

        last_node = target

        while unvisited_nodes:

            current_node = target
            current_dist = math.inf

            for node in table:
                if node in unvisited_nodes and table.get(node)[0] < current_dist:
                    current_node = node
                    current_dist = table.get(node)[0]

            if current_node == last_node:
                break

            for direction in self.get_paths().get(current_node).keys():
                node = self.get_paths().get(current_node).get(direction)[0]
                weight = self.get_paths().get(current_node).get(direction)[2]
                if (node not in table.keys() or current_dist + weight < table.get(node)[0]) and weight != -1:
                    table[node] = (current_dist + weight, current_node, direction)

            unvisited_nodes.remove(current_node)

        if target not in table:
            return None

        path: List[Tuple[Tuple[int, int], Direction]] = []
        node = target
        while node != start:
            direction = table.get(node)[2]
            node = table.get(node)[1]
            path.insert(0, (node, direction))

        return path

    def shortest_unexplored_path(self, start: Tuple[int, int]) -> Union[None, List[Tuple[Tuple[int, int], Direction]]]:
        """
        Returns the shortest path to the closest unexplored node on the planet.

        Examples:
            shortest_unexplored_path((1,2)) returns: [((0, 0), Direction.EAST), ((1, 0), Direction.NORTH)]
            shortest_explored_path((0,0)) returns: None
        :param start: 2-Tuple
        :return: List[2-Tuple, Direction] or None if all nodes are explored
        """

        if start not in self.get_paths().keys():
            return None

        if all(self.is_explored(node) for node in self.get_paths().keys()):
            print('alle Knoten erforscht')
            return None

        unvisited_nodes = set(self.get_paths().keys())
        table: Dict[Tuple[int, int], Tuple[int, Tuple[int, int], Direction]] = {
            start: (0, start, Direction.NORTH)}
        while unvisited_nodes:
            current_node = None
            current_dist = math.inf

            for node in table:
                if node in unvisited_nodes and table.get(node)[0] < current_dist:
                    current_node = node
                    current_dist = table.get(node)[0]

            if current_node is None:
                print('keine Knoten erreichbar. ')
                break

            if not self.is_explored(current_node):
                path: List[Tuple[Tuple[int, int], Direction]] = []
                while current_node != start:
                    direction = table.get(current_node)[2]
                    prev_node = table.get(current_node)[1]
                    path.insert(0, (prev_node, direction))
                    current_node = prev_node
                return path

            for direction in self.get_paths().get(current_node).keys():
                node, _, weight = self.get_paths().get(current_node).get(direction)
                if (node not in table or current_dist + weight < table.get(node)[0]) and weight != -1:
                    table[node] = (current_dist + weight, current_node, direction)

            unvisited_nodes.remove(current_node)

        return None

    def is_explored(self, node: Tuple[int, int]) -> bool:
        """
            Checks if a node still has unexplored directions by comparing the outgoing paths and the unexplored paths of a node.
            :param node: 2-Tuple
            :return: boolean, if True then the node is full explored.
            """
        try:
            if not self.undiscovered_directions[node]:
                return True
            else:
                return False
        except KeyError:
            pass

    def add_directions(self, node: Tuple[int, int], directions):
        """
            Saves directions under the associated coordinates in a dictionary
            :param node: 2-Tuple, current_coordinates
            :param directions: list of directions to be added to the dictionary
            :return: void
            """
        for direction in directions:
            if node not in self.undiscovered_directions:
                self.undiscovered_directions[node] = [direction]
            else:
                self.undiscovered_directions[node].append(direction)
        try:
            self.undiscovered_directions[node]
        except KeyError:
            self.undiscovered_directions[node] = []
        if self.undiscovered_directions[node]:
            # print('1114')
            self.unexplored_nodes.append(node)

    def update_direction(self, node: Tuple[int, int], direction_list: list[Direction]):
        """
            Removes a direction from a node from the node_directions dictionary.

            Example:
                delete_directions(((0, 3), Direction.NORTH))
            :param node: 2-Tuple
            :param direction_list: list which contains the compared positions
            :return: void
            """
        try:
            self.undiscovered_directions[node[0]] = [direction for direction in self.undiscovered_directions[node[0]] if direction not in direction_list]
        except KeyError:
            pass
            print(f'KeyError in delete_directions: Es gibt den Knoten {node[0]} noch gar nicht in undiscovered_directions!')

    def pop_from_stack(self, node: Tuple[int, int]):
        """
            Pops the last unexplored node from the stack if the node has no unexplored paths left.
            :param node: 2-Tuple, takes in current coordinates
            :return: void
            """
        try:
            if not self.undiscovered_directions[node]:
                print('1135')
                self.unexplored_nodes.pop()
        except KeyError:
            pass
        except IndexError:
            pass

    def next_unexplored_node_and_direction(self, start: Tuple[int, int]):
        """
            Checks for the next unexplored node and then for the next unexplored path of that node, if the current node.
            :param start: 2-Tuple, takes in the current coordinates.
            :return: Enum Type of Class Direction or None if fully explored.
            """
        try:
            print(start)
            print(self.unexplored_nodes)
            path = self.shortest_path(start, self.unexplored_nodes[-1])
            if path is None:
                # print('1122')
                return None
            if not path:
                # print('1123')
                return self.next_unexplored_direction(start)
            else:
                # print('1124')
                return path[0][1]
        except IndexError:
            # print('1121')
            return None

    def next_unexplored_direction(self, node: Tuple[int, int]) -> Optional[Direction]:
        """
            Helper method for the method above. Checks the next unexplored path of the current_node
            :param node: 2-Tuple, current coordinates.
            :return: Direction or None if fully explored
            """
        try:
            if self.undiscovered_directions[node]:
                next_direction = self.undiscovered_directions[node][0]
                # print('1128')
                return next_direction
        except KeyError:
            # print('1129')
            return None

    def update_certain(self, next_direction: Direction, node: Tuple[int, int]):
        """
            Updates the dictionary with the yet unvisited paths of the relating nodes (if the list in the dict is not empty).
            :param next_direction: the actual direction that needs to be deleted out of the paths' dict.
            :param node: 2-Tuple, current coordinates.
            :return: void
            """
        try:
            self.undiscovered_directions[node].pop(self.undiscovered_directions[node].index(next_direction))
            if not self.undiscovered_directions[node]:
                print('1134')
                self.unexplored_nodes.pop(self.unexplored_nodes.index(node))
        except ValueError:
            # print('1133')
            pass

    def check_paths(self, node: Tuple[int, int], paths_list) -> list:
        """
            Checks if the current paths have already been visited.
            :param node: 2-Tuple, current coordinates
            :param paths_list: list of current outgoing paths added.
            :return: list with the outgoing paths to be added to the undiscovered_paths dict.
            """
        try:
            filtered_list = [direction for direction in paths_list if direction not in self.get_paths()[node].keys()]
            return filtered_list
        except KeyError:
            return paths_list

    def convert_direction(self, direction_deg) -> Optional[Direction]:
        """
            Converts Direction integers to Direction Enum values if not already
            :param direction_deg: Integer
            :return Direction: attribute of Class Direction
            """
        if direction_deg == 0:
            return Direction.NORTH
        elif direction_deg == 90:
            return Direction.EAST
        elif direction_deg == 180:
            return Direction.SOUTH
        elif direction_deg == 270:
            return Direction.WEST
        elif direction_deg is Direction:
            return direction_deg
        elif direction_deg is None:
            return None
        else:
            print(f'Fehler bei Umwandlung des integers zu Direction.NORTH|EAST|SOUTH|WEST. '
                  f'Die Zahl muss 0, 90, 180, oder 270 sein, nicht {direction_deg}.')
