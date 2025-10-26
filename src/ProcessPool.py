from multiprocessing import Pool, Process, Manager
from src.Utils import kill_all_terminals
import os
import time


class ProcessPool:
    def __init__(self, global_conf):
        self.conf = global_conf

        # Take a copy of job inputs and terminals so global values remain intact
        self.workers = self.conf.terminals.copy()
        self.inputs = self.conf.work_inputs.copy()

        # We kill all of the terminals used by hpFX because it can't start a test on an already open instance.
        kill_all_terminals(global_conf)

    def run_terminal(self, terminal, input_ini):
        # Using a try/except to prevent failed processes to hold the pool forever
        while True:
            try:
                my_terminal = terminal.pop()
            except:
                time.sleep(5)
                continue

            # command = 'call "{}" "{}"'.format(my_terminal.exe, input_ini)
            # Switched to using 'start' because unlike 'call' it offers an option to start in a minimized window
            command = 'start /b /wait /min "" "{}" "{}"'.format(my_terminal.exe, input_ini)
            shortened_input_ini = os.path.relpath(input_ini, self.conf.abs_mt4_results_folder)
            print("[{}] is processing: {}".format(my_terminal.name, shortened_input_ini))
            os.system(command)
            terminal.append(my_terminal)
            return True

    def run(self):
        manager = Manager()
        workers = manager.list(self.workers)
        inputs = self.inputs.copy()
        processes = []
        while len(inputs) > 0:
            p = Process(target=self.run_terminal, args=(workers, inputs.pop()))
            processes.append(p)

        for p in processes:
            p.start()

        for p in processes:
            p.join()

