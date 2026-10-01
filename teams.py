import importlib.util
import json
import multiprocessing
import os
import random
import sys
import time
import traceback
from collections import deque
from multiprocessing.connection import wait

from config import *


def _is_inside(module, folder):
    locations = [getattr(module, "__file__", None) or ""] + list(getattr(module, "__path__", []))
    for location in filter(None, locations):
        location = os.path.abspath(location)
        if location == folder or location.startswith(folder + os.sep):
            return True
    return False


def load_agent_class(folder_path, module_name):
    """Loads the Agent class from folder_path/agent.py.

    Each team is loaded as a separate module, and the team's own helper modules are
    removed from the import cache afterwards, so two teams can use helper modules
    with the same name.
    """
    folder = os.path.abspath(folder_path)
    agent_file = os.path.join(folder, "agent.py")
    if not os.path.isfile(agent_file):
        raise FileNotFoundError(f"Required 'agent.py' not found in folder: {folder_path}")

    # The parent folder is added so that imports like `from team_folder.helper import X` work too
    search_paths = [folder, os.path.dirname(folder)]
    sys.path[:0] = search_paths
    try:
        spec = importlib.util.spec_from_file_location(module_name, agent_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        del sys.path[:len(search_paths)]
        for name, cached in list(sys.modules.items()):
            if _is_inside(cached, folder):
                del sys.modules[name]

    return module.Agent


class LocalTeam:
    """Runs a team's agents in this process. The GUI uses it, because the human player reads the game window's keyboard.

    A team receives each step's observations as {agent index: (visible_world, position, can_shoot, holding_flag, hp,
    ammo)} and answers with {agent index: (action, direction)}.
    """

    def __init__(self, agent_class):
        self.agent_class = agent_class
        self.error_count = 0
        self.failed = False

    def start(self, color, agent_count, seed):
        self.color = color
        self.shared_knowledge = {}
        self.agents = {index: self.agent_class(color, index) for index in range(agent_count)}

    def send_observations(self, observations):
        self.actions = {}
        for index, (visible_world, position, can_shoot, holding_flag, hp, ammo) in observations.items():
            try:
                action, direction = self.agents[index].update(
                    visible_world, position, can_shoot, holding_flag, self.shared_knowledge, hp, ammo)
            except Exception:
                self.error_count += 1
                print(f"Error in {self.color} agent {index}:")
                traceback.print_exc()
                continue
            self.actions[index] = (action, direction)

    def receive_actions(self):
        return self.actions

    def terminate(self, index, reason):
        try:
            self.agents[index].terminate(reason)
        except Exception:
            traceback.print_exc()

    def close(self):
        pass


class ProcessTeam:
    """Runs a team's agents in a child process, so they can't reach the engine and can be timed.

    A team that doesn't answer a step within STEP_TIME_LIMIT does nothing that step; its agents still get every update
    call, in order, as it catches up. A team that crashes, takes longer than STARTUP_TIME_LIMIT to start, or falls
    LAG_TIME_LIMIT behind is killed and marked as failed. The team's `random` is seeded with the given seed.
    """

    def __init__(self, folder, quiet=False):
        self.folder = folder
        self.quiet = quiet
        self.error_count = 0
        self.failed = False
        self.process = None
        self.pending = deque()  # (step, send time) of the steps the team hasn't answered yet
        self.step = 0

    def start(self, color, agent_count, seed):
        methods = multiprocessing.get_all_start_methods()
        context = multiprocessing.get_context("forkserver" if "forkserver" in methods else "spawn")
        os.environ["PYTHONHASHSEED"] = "0"  # Same iteration order of sets of strings in every game
        self.inbox = context.Queue()
        self.reader, writer = context.Pipe(duplex=False)
        self.process = context.Process(target=_run_team, daemon=True,
                                       args=(self.folder, color, agent_count, seed, self.quiet, self.inbox, writer))
        self.process.start()
        writer.close()
        if self._receive(time.monotonic() + STARTUP_TIME_LIMIT) != "ready" and not self.failed:
            self._fail()

    def send_observations(self, observations):
        if self.failed:
            return
        self.step += 1
        self.pending.append((self.step, time.monotonic()))
        self.inbox.put(("update", self.step, observations))

    def receive_actions(self):
        if self.failed:
            return {}
        step, sent_time = self.pending[-1]
        while not self.failed:
            message = self._receive(sent_time + STEP_TIME_LIMIT)
            if message is None:
                break
            try:
                answered_step, actions, self.error_count = message
                actions = {index: (action, direction) for index, action, direction in actions}
            except (TypeError, ValueError):
                self._fail()
                break
            while self.pending and self.pending[0][0] <= answered_step:
                self.pending.popleft()
            if answered_step == step:
                return actions

        if self.pending and time.monotonic() - self.pending[0][1] > LAG_TIME_LIMIT:
            self._fail()
        return {}

    def terminate(self, index, reason):
        if not self.failed:
            self.inbox.put(("terminate", index, reason))

    def close(self):
        if self.process is None:
            return
        if not self.failed:
            self.inbox.put(("close",))
            self.process.join(LAG_TIME_LIMIT)
        self.process.kill()
        self.process.join()
        self.inbox.cancel_join_thread()
        self.inbox.close()
        self.reader.close()

    def _receive(self, deadline):
        """Returns the next message from the team, or None if none arrives before the deadline or the team crashed."""
        if not wait([self.reader], max(0, deadline - time.monotonic())):
            return None
        try:
            return json.loads(self.reader.recv_bytes())
        except (EOFError, OSError, ValueError):
            self._fail()
            return None

    def _fail(self):
        self.failed = True
        self.process.kill()


def _run_team(folder, color, agent_count, seed, quiet, inbox, writer):
    """Entry point of a team's child process. Answers are sent as JSON, so a team can't make the engine run code."""
    if quiet:
        sys.stdout = sys.stderr = open(os.devnull, "w")
    random.seed(seed)
    team = LocalTeam(load_agent_class(folder, f"{color}_agent"))
    team.start(color, agent_count, seed)
    writer.send_bytes(json.dumps("ready").encode())

    while True:
        kind, *args = inbox.get()
        if kind == "update":
            step, observations = args
            team.send_observations(observations)
            actions = [[index, action, direction] for index, (action, direction) in team.receive_actions().items()
                       if isinstance(action, str) and isinstance(direction, str)]
            writer.send_bytes(json.dumps([step, actions, team.error_count]).encode())
        elif kind == "terminate":
            team.terminate(*args)
        else:
            return
