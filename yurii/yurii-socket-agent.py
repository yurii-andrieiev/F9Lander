import socket

from pybrain.rl.learners.valuebased.interface import ActionValueInterface
from pybrain.rl.environments import Environment
from scipy import *
import json
import os.path

RESET_CMD = str([0, 0, 0, 1])
DEFAULT_IP = '127.0.0.1'
DEFAULT_PORT = 50007
state_space_filename = "state_space.json"

actions = [[0, 0, 0, 0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [1, 1, 0, 0], [0, 1, 1, 0], [1, 0, 1, 0],
           [1, 1, 1, 0]]


class VerticalLandingEnvironment(Environment):
    # the number of action values the environment accepts
    indim = 1
    # the number of sensor values the environment produces
    outdim = 0

    discreteStates = False
    discreteActions = True
    numActions = len(actions)

    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT):
        self.socket = socket.socket()
        self.socket.connect((ip, port))
        self.reset()

    def reset(self):
        self.socket.send(RESET_CMD)

    def performAction(self, action):
        self.socket.send(str(action))

    def getSensors(self):
        states = eval(self.socket.recv(1024))
        if not states:
            return None
        states = {state['type']: state for state in states}
        return states['actor'], states['decoration'], states['system']


class DefaultController(ActionValueInterface):
    def getMaxAction(self, state):
        agent_state, platform_state, system_state = state
        angle = agent_state["angle"]

        left = 1 if angle < 0 else 0
        right = 1 if angle > 0 else 0
        up = 1 if agent_state["vy"] <= -7.0 else 0

        # system_state["flight_status"] | "none", "landed", "destroyed"
        # "none" means that we don't know, whether we landed or destroyed
        if system_state["flight_status"] == "destroyed" or (agent_state["fuel"] <= 0.0 and agent_state["dist"] >= 70.0):
            new = 1
        else:
            new = 0
        return up, left, right, new

    def getActionValues(self, state):
        return actions


environment = VerticalLandingEnvironment()
controller = DefaultController()

state_space = list()

try:
    while True:
        sensors = environment.getSensors()
        if not sensors:
            break
        action = controller.getMaxAction(sensors)
        environment.performAction(action)

        agent_state, platform_state, system_state = sensors
        state_space.append(agent_state)

        print agent_state, platform_state, system_state
        print "{" + str(agent_state) + "," + str(platform_state) + "," + str(system_state) + "}" + ","

except Exception:
    with open(state_space_filename, "w+") as text_file:
        state_space_as_json = json.dumps(state_space, indent=4, separators=(',', ': '))
        text_file.write(state_space_as_json)
        text_file.read()
    raise

environment.socket.close()
print "Socket closed"
