import os
import sys
sys.path.append("..")
import tempfile
import subprocess
from src import GlobalConfig


def run_as_admin(command):
    tmp_set_fn = tempfile.mktemp(prefix='hpFX_adm_cmd', suffix='.bat')
    try:
        tmp_file = open(tmp_set_fn, 'w')
    except IOError:
        print("In run_as_admin(): Cannot create temporary file {}. Terminating.".format(tmp_set_fn))
        sys.exit(409)

    tmp_file.write(command)
    tmp_file.close()

    command = "powershell -command \"Start-Process {} -Verb runas \"".format(tmp_set_fn)
    print("Running: {}".format(command))
    subprocess.call(command, shell=False)

    # This is the weirdest thing. If I remove the temporary file, the command doesn't run.
    # DO NOT UNCOMMENT THIS LINE: os.remove(tmp_set_fn)


def main():
    global_conf = GlobalConfig()
    global_conf.ingest_global_config()
    print("Global Shared Folder = ", global_conf.global_shared_folder)
    print("mt4_results_folder = ", global_conf.mt4_results_folder)

    for terminal in global_conf.terminals:
        terminal.print()
        # Create a list of hard links in {hardlink:real_path} dict format
        data_folder = terminal.data_folder

        # Copy executable name
        old_exe = os.path.join(terminal.path, 'terminal.exe')
        new_exe = os.path.join(terminal.path, terminal.exe)
        print("{} -> {}".format(old_exe, new_exe))
        run_as_admin("copy \"{}\" \"{}\"".format(old_exe, new_exe))

        abs_templates_path = os.path.join(global_conf.global_shared_folder, 'templates')
        abs_indicators_path = os.path.join(global_conf.global_shared_folder, 'MQL4\\Indicators')
        abs_experts_path = os.path.join(global_conf.global_shared_folder, 'MQL4\\Experts')
        abs_scripts_path = os.path.join(global_conf.global_shared_folder, 'MQL4\\Sripts')
        abs_history_path = global_conf.global_history_folder
        abs_tester_history_path = global_conf.global_tester_history_folder
        abs_mt4_results_path = os.path.join(global_conf.global_shared_folder, 'tester', global_conf.mt4_results_folder)
        abs_native_csv_path = os.path.join(global_conf.global_shared_folder, 'tester', 'files')

        hl_templates_path = os.path.join(data_folder, 'templates')
        hl_indicators_path = os.path.join(data_folder, 'MQL4\\Indicators')
        hl_experts_path = os.path.join(data_folder, 'MQL4\\Experts')
        hl_scripts_path = os.path.join(data_folder, 'MQL4\\Scripts')
        hl_history_path = os.path.join(data_folder, 'history')
        hl_tester_history_path = os.path.join(data_folder, 'tester\\history')
        hl_mt4_results_path = os.path.join(data_folder, 'tester', global_conf.mt4_results_folder)
        hl_native_csv_path = os.path.join(data_folder, 'tester', 'files')
        hard_links = {abs_templates_path: hl_templates_path, abs_indicators_path: hl_indicators_path,
                      abs_experts_path: hl_experts_path, abs_scripts_path:hl_scripts_path,abs_history_path:hl_history_path,
                      abs_tester_history_path: hl_tester_history_path, abs_mt4_results_path: hl_mt4_results_path,
                      abs_native_csv_path: hl_native_csv_path}

        for hl in hard_links:
            link_path = hard_links[hl].strip()
            abs_path = hl.strip()
            print('{} -> {}'.format(link_path, abs_path))
            # Create real path directories if they don't exist
            if not os.path.exists(abs_path):
                try:
                    os.makedirs(abs_path)
                except IOError:
                    print("'{}' is missing and can't be created. You may try manually configuring hpFX. Aborting.")
                    sys.exit(411)
                # Backup existing/default directories
            if os.path.exists(link_path):
                backup_path = link_path + '.BAK'
                if not os.path.exists(backup_path):
                    command = "call rmdir \"{}\"".format(backup_path)
                    os.system(command)
                    os.rename(link_path, backup_path)
                # Tried using python's os.link(abs_path, link_path), getting permission problems.
            # mklink /J < Link > < Target >
            command = "call rmdir \"{}\"".format(link_path)
            os.system(command)
            command = "mklink /J \"{}\" \"{}\"".format(link_path, abs_path)
            # print(command)
            os.system(command)


if __name__ == "__main__":
    main()
