import logging
import sys
import re
import os
import shutil
import argparse
import hashlib
from src import Terminal
from src import Utils


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-e", "--expertconfig", type=str, help="hpFX expert configuration file (*.set) "
                                                               "relative to the 'global_shared_folder' defined in global "
                                                               "config")
    parser.add_argument("-p", "--pairs", type=str, help="Either a comma separated list of pairs or one of the user "
                                                        "defined lists in testconfig (e.g. ALL, MAJOR, etc.)")
    parser.add_argument("-t", "--timeframe", type=str, help="Timeframe that matches the 'Period:' drop down list, "
                                                            "e.g. Daily, H1, M15, etc")
    parser.add_argument("-m", "--model", type=int,
                        help="Test Model: 0='every tick', 1='control points', 2='open prices'. Make sure this "
                             "selection matches the 'TEST MODEL' in expert properties (*.set file).")
    parser.add_argument("-s", "--spread", type=int,
                        help="Spread in points. E.g. 35 is 3.5 pips. 'Current' not supported.")
    parser.add_argument("-from", "--from", type=str, help="Experiment 'From' Date in 'YYYY.MM.DD' format.")
    parser.add_argument("-to", "--to", type=str, help="Experiment 'To' Date in 'YYYY.MM.DD' format.")
    parser.add_argument("-o", "--optimization", action='store_true', help="Enable optimization (this has nothing to do "
                                                                          "with the runtime performance. It simply "
                                                                          "checks the Optimization option in Strategy "
                                                                          "Tester)")
    parser.add_argument("-d", "--delete", action='store_true', help="Delete existing results folders/files and "
                                                                    "run all tests from scratch.")

    parser.add_argument("-r", "--repair", action='store_true', help="Identifies missing tests compared to the input"
                                                                    " configuration and runs them. It checks for"
                                                                    " missing HTM files and blank lines in the Results CSV.")
    parser.add_argument("-b", "--bugfix", action='store_true', help="Starts hpFX in debugging node. generates "
                                                                    "verbose output and keeps MT4 open after tests.")


    # Different args group that can be listed as 'required' as a workaround for argparse's annoying
    # 'everything is considered optional' assumption.
    required_args = parser.add_argument_group('Required Arguments')
    required_args.add_argument("-c", "--testconfig", type=str, required=True,
                               help="Test specific configuration file in YAML format")
    args = vars(parser.parse_args())

    if args['testconfig'] is None:
        parser.print_help()
        logging.error("Please provide a Test configuration file (-c)")
        sys.exit(31)

    return args


class GlobalConfig:
    def __init__(self):
        # User configuration parameters
        self.testUniqueName = None
        self.testCategory = None
        self.test_config = None
        self.global_config = None
        self.symbols = None
        self.expert_config = None
        self.pairs = None
        self.time_frame = None
        self.test_model = None
        self.spread = None
        self.optimization = None
        self.date_from = None
        self.date_to = None
        self.work_inputs = []

        # Global (system) configuration parameters
        self.global_config = os.path.join("../config", "global_config.yaml")
        # Where to keep all configurations and processed results
        self.global_shared_folder = None
        # Temporary directory to be created under each MT4's data folder to keep output
        self.mt4_results_folder = None
        self.abs_mt4_results_folder = None
        self.category_results_folder = None
        self.num_terminals = None
        self.terminals = []
        self.workers = None
        self.expert = None
        self.global_history_folder = None
        self.global_tester_history_folder = None
        self.broker_server = None
        self.broker_login = None
        self.broker_password = None

        # Internal parameters
        self.is_delete = None
        self.is_repair = None
        self.is_debug = False
        self.htm_reports = {}
        self.test_report_csv = None
        # Absolute path for the test specific folder
        self.abs_test_specific_folder = None
        # Relative path for the test specific folder (terminal.exe only supports relative paths to save reports)
        self.relative_test_specific_folder = None
        self.ini_dir = None
        # set_dir Needed due to the new license structure starting with 20-BETA
        self.set_dir = None
        self.set_dir_abs = None
        self.abs_reports_folder = None
        self.relative_reports_folder = None
        self.abs_expert_path = None

        # test_case_maker specific parameters
        # BASELINECROSS,    // < indi_parameters >; < indi_filename >; < buffer1 >
        # TWOLINESCROSS,    // < indi_parameters >; < indi_filename >; < buffer1 >, < buffer2 >
        # ONELEVELCROSS,    // < indi_parameters >; < indi_filename >; < buffer >; < level >
        # TWOLEVELCROSS,    // < indi_parameters >; < indi_filename >; < (+ / -)buffer >; < high_level >, < low_level >
        # SLOPE,            // < indi_parameters >; < indi_filename >; < buffer >
        # HISTOGRAM,        // < indi_parameters >; < indi_filename >; < buffer1 >, < buffer2 >
        # LINEMACROSS,      // < indi_parameters >; < indi_filename >; < buffer1 >; < MA_period >, < MA_type >
        # ARROWS,           // < indi_parameters >; < indi_filename >; < long_buffer >, < short_buffer >
        # NONE

        # Don't forget to update the version in SetMaker.py as well!
        self.indi_types = {'NONE': 0, 'BASELINECROSS': 1, 'TWOLINESCROSS': 2, 'ONELEVELCROSS': 3, 'TWOLEVELCROSS': 4,
                           'SLOPE': 5, 'HISTOGRAM': 6, 'LINEMACROSS': 7, 'ARROWS': 8, 'SINGLEBUFFER': 9}
        self.test_case_expert_template = None
        self.abs_test_case_expert_template = None
        self.hpFX_config_template = None
        self.experts_path = None
        self.abs_experts_path = None
        self.bat_file = None
        #BL IS RETIRED self.BL = None
        self.ENTRY_PERMS = None
        self.SIGNAL = None
        self.CONF1 = None
        self.CONF2 = None
        self.CONF3 = None
        self.VOL = None
        self.EXIT = None
        self.Entry_Permutations = False

    def ingest_args(self):
        args = parse_arguments()

        # This must be the first step in argument parsing: There's nothing to run if there's no global config.
        self.ingest_global_config()

        # This must be the second step in argument parsing: Ingest the parameters provided in the test_config.yaml.
        # We must do this before parsing the command line parameters that will follow, because they take precedence,
        # thus overwrite settings read from the test_config.yaml file.
        self.test_config = args['testconfig']
        self.ingest_test_config()

        # And finally start overwriting the parameters with what's provided on the command line, if any.

        if args['expertconfig'] is not None:
            self.expert_config = args['expertconfig']

        if args['pairs'] is not None:
            #self.pairs = args['pairs'].split(',')
            self.symbols = args['pairs'].split(',')

        if args['timeframe'] is not None:
            self.time_frame = args['timeframe']

        if args['model'] is not None:
            self.test_model = args['model']

        if args['spread'] is not None:
            self.spread = args['spread']

        if args['from'] is not None:
            self.date_from = args['from']

        if args['to'] is not None:
            self.date_to = args['to']

        if args['optimization']:
            # Defined in string format to be included in the generated ini file
            self.optimization = 'true'

        if args['delete']:
            self.is_delete = True

        if args['repair']:
            self.is_repair = True

        if self.is_repair and self.is_delete:
            logging.error("Delete (-d) and Repair (-r) options are mutually exclusive! You need to pick one.")
            sys.exit(55)

        if args['bugfix']:
            self.is_debug = True

        # Moving
        # Append date range to testUniqueName to avoid accidental overwrites
        date_string = self.date_from.replace('.', '') + "-" + self.date_to.replace('.', '')
        self.testUniqueName = os.path.join(self.testUniqueName, date_string)

        # We need to prepend "tester\" to <mt4_results_folder> because terminal.exe requires a relative path to
        # 'tester' for ini files. It can't read ini files from anywhere else, including the data folder. Even worse,
        #  when ini files are located outside of the tester directory, terminal.exe simply runs the 'default' experts
        #  file, creating garbage results, instead of giving an error.
        # self.mt4_results_folder = os.path.join("tester", tmp_args['mt4_results_folder'])

        # abs_test_specific_folder is the parent dir for htm_reports and ini_files (named after the date range)
        # E.g. C:\Users\mehme\Documents\hpFX_Shared\tester\hpFX_tester\TEST\C1_ASH\20160101-20200101
        #print("category_results_folder: ", self.category_results_folder)

        self.abs_test_specific_folder = os.path.join(self.global_shared_folder, 'tester', self.category_results_folder,
                                                     self.testUniqueName)

        if self.is_delete:
            if os.path.exists(self.abs_test_specific_folder):
                print("Deleting existing results in ", self.abs_test_specific_folder)
                shutil.rmtree(self.abs_test_specific_folder)
                os.rmdir(self.abs_test_specific_folder)

        # relative_test_specific_folder is the  parent dir for htm_reports and ini_files (named after the date range)
        # relative to '<data_folder>\tester'
        # E.g. hpFX_tester\TEST\C1_ASH\20160101-20200101
        self.relative_test_specific_folder = os.path.join(self.category_results_folder, self.testUniqueName)

        #DEBUG print("relative_test_specific_folder: ", self.relative_test_specific_folder)

    def ingest_global_config(self):
        tmp_args = Utils.open_yaml(self.global_config)
        self.global_shared_folder = tmp_args['global_shared_folder']
        # prepend 'tester' --> Can't remember why this would be catastrophic, but it was???
        # I Remembered!! the relative path must be relative to 'tester'!!!
        # DON'T PREPEND TESTER HERE!!
        self.mt4_results_folder = tmp_args['mt4_results_folder']
        self.abs_mt4_results_folder = os.path.join(self.global_shared_folder, 'tester', self.mt4_results_folder)
        #print("abs_mt4_results_folder: ", self.abs_mt4_results_folder)
        self.global_history_folder = os.path.join(tmp_args['global_history_folder'], 'history')
        self.global_tester_history_folder = os.path.join(tmp_args['global_history_folder'], 'tester', 'history')
        self.broker_server = tmp_args['broker_server']
        self.broker_login = tmp_args['broker_login']
        self.broker_password = tmp_args['broker_password']

        self.num_terminals = len(tmp_args['mt4_terminals'])

        app_data_root = os.path.join(os.getenv('APPDATA'), 'MetaQuotes', 'Terminal')
        for t in range(self.num_terminals):
            name = "MT4_Core_{}".format(t+1)
            path = tmp_args['mt4_terminals'][t]
            path = path.rstrip('/').rstrip('\\')
            # exe = os.path.join(path, 'hpFX_terminal.exe')
            exe = os.path.join(path, 'terminal.exe')
            unique_name = Utils.data_folder_name(path)
            data_folder = os.path.join(app_data_root, unique_name)
            if not os.path.exists(data_folder):
                logging.error("Unable to identify data folder {} location for '{}'. Please check the path you provided in "
                              "'global_config.yaml' file. Do not use double quotes in this path.".format(data_folder, path))
                sys.exit(11)
            tmp_terminal = Terminal.Terminal(name, path, exe, data_folder)
            self.terminals.append(tmp_terminal)

        # Create the worker pool of MT4 terminals to be used at runtime
        self.workers = self.terminals.copy()

    def ingest_test_config(self):
        """
        Harvest test-specific arguments from the test config file. Note that some of these may be overwritten by
        arguments are provided on the command line, which take precedence.
        """
        tmp_args = Utils.open_yaml(self.test_config)
        self.expert_config = os.path.join(self.mt4_results_folder, tmp_args['TestExpertParameters'])

        # os.makedirs() can't generate the hard linked shared folder (global_shared_folder) recursively if it gets
        # deleted sometime after the hard links are created. So, checking and creating this parent folder if necessary.
        # BTW, I hope you never need this safety measure because it'll be catastrophic for global_shared_folder to be
        # deleted as it permanently holds all of the created test results and reports!!

        # WHY DID I EVER USE tmp_abs_path_to_shared? It's the same thing as abs_mt4_results_folder???
        # tmp_abs_path_to_shared = os.path.join(self.global_shared_folder, self.mt4_results_folder)
        # if not os.path.exists(tmp_abs_path_to_shared):
        #     os.makedirs(tmp_abs_path_to_shared)

        if not os.path.exists(self.abs_mt4_results_folder):
            os.makedirs(self.abs_mt4_results_folder)

        # Check if a list of symbols is provided. If not, a custom symbols list must be provided (e.g. ALL, MAJOR, etc)
        if isinstance(tmp_args['TestSymbolsList'], list):
            self.symbols = tmp_args['TestSymbolsList']
        else:
            try:
                self.symbols = tmp_args[tmp_args['TestSymbolsList']]
            except:
                logging.error("The symbol list is invalid. Check the test config file.")
                sys.exit(13)

        self.expert = tmp_args['TestExpert']
        self.time_frame = tmp_args['TestPeriod']

        if int(tmp_args['TestModel']) in [0, 1, 2]:
            self.test_model = tmp_args['TestModel']
        else:
            logging.error("Test Model must be one of 0='every tick', 1='control points', 2='open prices'")
            sys.exit(15)

        # Not converting to int because "Current" is one of the options
        self.spread = tmp_args['TestSpread']

        if tmp_args['TestOptimization']:
            self.optimization = 'true'
        else:
            self.optimization = 'false'

        self.date_from = tmp_args['TestFromDate']

        self.date_to = tmp_args['TestToDate']

        self.testUniqueName = tmp_args['TestUniqueName']
        # Generate testUniqueName after the expert file (.set) if not specified in test configuration
        if self.testUniqueName is None:
            self.testUniqueName = os.path.basename(self.expert_config).split('.set')[0]

        self.testCategory = tmp_args['TestCategory']
        self.category_results_folder = os.path.join(self.mt4_results_folder, self.testCategory)

    def ingest_test_maker_config(self, custom_config_fn):
        """
        This configuration is meant to be used for 'test_case_maker.py' only. It ingests the provided input to decide
        which test cases to create and how.
        """
        tmp_args = Utils.open_yaml(custom_config_fn)

        print("DEBUG: custom_config_fn =", custom_config_fn)
        print("DEBUG: tmp_args =", tmp_args)

        # TEST MODE RETIRED self.test_mode = tmp_args['TestMode']

        # OVERWRITES the TestCategory that may have been specified in the template yaml config file
        # This is for convenience as it can be tedious (and error prone) to change the template file each time a
        # different category is being processed (e.g. C, BL, C again, BL again...)
        self.testCategory = tmp_args['TestCategory']
        self.category_results_folder = os.path.join(self.mt4_results_folder, self.testCategory)

        # self.abs_experts_path must be generated before 'self.testCategory' is appended to 'self.mt4_results_folder'!!
        self.experts_path = tmp_args['ExpertsPath']
        if os.path.isabs(self.experts_path):
            logging.error("'ExpertsPath' must be provided as a relative path to 'mt4_results_folder' defined in "
                          "global_config.yaml, rather than an absolute path.")
            sys.exit(91)

        self.test_case_expert_template = tmp_args['ExpertTemplate']
        # self.abs_test_case_expert_template = os.path.join(self.global_shared_folder, self.mt4_results_folder,
        #                                                  self.test_case_expert_template)
        # Design change: no longer requiring a path relative to mt4_results_folder.
        self.abs_test_case_expert_template = os.path.abspath(self.test_case_expert_template)
        self.abs_experts_path = os.path.join(self.global_shared_folder, 'tester', self.mt4_results_folder, self.experts_path)

        if not os.path.exists(self.abs_experts_path):
            os.makedirs(self.abs_experts_path)

        self.hpFX_config_template = tmp_args['hpFXTemplate']

        print("DEBUG ==== FROM Configuration.ingest_test_maker_config() =====")
        print("DEBUG mt4_results_folder: ", self.mt4_results_folder)
        print("DEBUG abs_mt4_results_folder :", self.abs_mt4_results_folder)
        print("DEBUG test_case_expert_template: ", self.test_case_expert_template)
        print("DEBUG abs_test_case_expert_template: ", self.abs_test_case_expert_template)
        print("DEBUG hpFX_config_template: ", self.hpFX_config_template)
        print("DEBUG experts_path: ", self.experts_path)
        print("DEBUG abs_experts_path: ", self.abs_experts_path)
        print("DEBUG tmp_args in ingest_test_maker_config(): ", tmp_args)
        print("DEBUG ========================================================")

        # RETIRED self.BASELINE = tmp_args['BASELINE']
        # PROTECTING_GIT_VERSION self.ENTRY_PERMS = tmp_args['ENTRY_PERMS']
        # PROTECTING_GIT_VERSION self.SIGNAL = tmp_args['SIGNAL']
        # PROTECTING_GIT_VERSION self.CONFIRMATION1 = tmp_args['CONFIRMATION1']
        # PROTECTING_GIT_VERSION self.CONFIRMATION2 = tmp_args['CONFIRMATION2']
        # PROTECTING_GIT_VERSION self.TRADEORNOT = tmp_args['TRADEORNOT']
        # PROTECTING_GIT_VERSION self.EXIT = tmp_args['EXIT']
        # PROTECTING_GIT_VERSION self.Entry_Permutations = tmp_args['Entry_Permutations']

        # Translated input to set file's specific format
        self.ENTRY_PERMS = tmp_args['ENTRY_PERMS']
        self.SIGNAL = tmp_args['ENTRY']
        self.CONF1 = tmp_args['CONF']
        # RETIRED self.CONFIRMATION2 = tmp_args['CONFIRMATION2']
        self.VOL = tmp_args['VOL']
        self.EXIT = tmp_args['EXIT']
        self.Entry_Permutations = tmp_args['Entry_Permutations']


        self.bat_file = tmp_args['TestBatFile']
        if os.path.splitext(self.bat_file)[1] != '.bat':
            logging.error("The extension of the 'TestBatFile' must be '.bat'. Please check the configuration file.")
            sys.exit(18)

        # DEBUG print("---- FROM Configuration.ingest_test_maker_config() ----")
        # DEBUG print("BL: ", self.BL)
        # DEBUG print("ENTRY_PERMS: ", self.ENTRY_PERMS)
        # DEBUG print("ENTRY: ", self.ENTRY)
        # DEBUG print("CONF: ", self.CONF)
        # DEBUG print("VOL: ", self.VOL)
        # DEBUG print("EXIT: ", self.EXIT)
        # DEBUG print("Entry_Permutations: ", self.Entry_Permutations)
        # DEBUG print("-------------------------------------------------------")

    def prepare_test_environment(self):
        """
        Create the file/folder structure under 'abs_test_specific_folder' to keep the configurations and results.
        This function must be called after all the input parameters are ingested from the global, test specific
        and command line arguments.

        This structure assumes hard linked data folders and tests will fail if the MT4 instances are not configured
        in that way.
        """

        # In case only one symbol is defined as a variable rather than list in the YAML file,
        # despite the instructions clearly say not to do so
        if not isinstance(self.symbols, list):
            self.symbols = list(self.symbols)

        # We place all of the ini files in a separate directory to keep things tidy & clean.
        self.ini_dir = os.path.join('tester', self.abs_test_specific_folder, "ini_files")
        self.set_dir = os.path.join(self.relative_test_specific_folder, "set_files")
        self.set_dir_abs = os.path.join(self.abs_test_specific_folder, "set_files")
        print("DEBUG CREATING INI DIR: ", self.ini_dir)
        print("DEBUG CREATING ABS SET DIR: ", self.set_dir_abs)
        try:
            if not os.path.exists(self.ini_dir):
                os.makedirs(self.ini_dir)
        except IOError:
            logging.error("Cannot create the folder for the ini files: ", self.ini_dir)
            sys.exit(16)

        try:
            if not os.path.exists(self.set_dir_abs):
                os.makedirs(self.set_dir_abs)
        except IOError:
            logging.error("Cannot create the folder for the set files: ", self.set_dir_abs)
            sys.exit(26)

        # Similarly, creating a htm directory to keep reports.
        self.abs_reports_folder = os.path.join(self.abs_test_specific_folder, "htm_reports")
        self.relative_reports_folder = os.path.join('tester', self.relative_test_specific_folder, "htm_reports")

        try:
            if not os.path.exists(self.abs_reports_folder):
                os.makedirs(self.abs_reports_folder)
        except IOError:
            logging.error("Cannot create the folder for the htm report files: ", self.abs_reports_folder)
            sys.exit(17)

        # The full path to the expert parameters file (*.set)
        self.abs_expert_path = os.path.join(self.global_shared_folder, 'tester', self.expert_config)

        # Move the expert parameters file and test YAML configuration to results folders as a backup/reference
        # TODO: CONSIDER DOING THIS AFTER CHECKING IF A RUN IS NEEDED
        #print("DEBUG Copying {} -> {} ".format(self.abs_expert_path, self.abs_test_specific_folder))

        try:
            # Moved below due to the need for symbol-specific set files
            # shutil.copy(self.abs_expert_path, self.abs_test_specific_folder)
            shutil.copy(self.test_config, self.abs_test_specific_folder)
        except shutil.SameFileError:
            pass

        # The filename to keep the parsed results
        self.test_report_csv = os.path.join(self.abs_test_specific_folder, "RESULTS.csv")

        # Identify if the request if for a new set of symbols, or repairing a set with missing results.
        # print("DEBUG >>> self.symbols: {}".format(self.symbols))
        if os.path.exists(self.test_report_csv):
            if self.is_repair:
                results_dict = Utils.csv_to_dict(self.test_report_csv)
                #print("DEBUG >>> results_dict: {}".format(results_dict))
                for line in results_dict:
                    # Sometimes a symbol is processed, but the result may be blank
                    if int(line['Total trades']) == 0:
                        continue
                    else:
                        # Remove symbols that are already processed correctly
                        try:
                            self.symbols.remove(line['Symbol'])
                        except ValueError:
                            pass

                    # At this point, symbols missing from the CSV file and symbols with a blank line should
                    # remain in the list to be processed
            elif self.is_delete:
                print("Overwrite (-d) requested, all existing results will be overwritten.")
            else:
                logging.error("Found existing results for this case. You must specify either '-r' to repair missing "
                              "results or '-d' to overwrite existing.")
                sys.exit(61)

            if len(self.symbols) == 0:
                print("Could not find any symbols to process/repair, all of the results look complete and intact.")
                sys.exit(0)

            print("Identified symbols to process/repair: ", self.symbols)
            current_csv = Utils.csv_to_dict(self.test_report_csv)
            retained_csv = []
            for line in current_csv:
                if line['Symbol'] in self.symbols:
                    continue
                else:
                    retained_csv.append(line)
            # If the retained_csv is of size zero, dict_to_csv() doesn't know what to do with it.
            # So we simply remove the existing CVS as there're no results to salvage.
            if len(retained_csv) == 0:
                os.remove(self.test_report_csv)
            else:
                Utils.dict_to_csv(retained_csv, self.test_report_csv, overwrite=True)

        # terminal.exe doesn't know how to handle multiple pairs (wouldn't it be nice!), so we create a file for each
        mt4_id_counter = 1
        for symbol in self.symbols:
            tmp_symbol_ini_fn = os.path.join(self.ini_dir, symbol + ".ini")
            # License changes after 20-BETA requires a separate set file for each test (for different MT4 IDs)
            tmp_symbol_set_fn = os.path.join(self.set_dir, symbol + ".set")
            tmp_symbol_set_fn_abs = os.path.join(self.global_shared_folder, "tester", tmp_symbol_set_fn)

            # print("DEBUG: abs_mt4_results_folder = {}".format(self.abs_mt4_results_folder))
            # print("DEBUG: tmp_symbol_set_fn = {}".format(tmp_symbol_set_fn))
            # print("DEBUG: tmp_symbol_set_fn_abs = {}".format(tmp_symbol_set_fn_abs))

            try:
                # Each symbol gets its own set file starting from 20 BETA version
                shutil.copy(self.abs_expert_path, tmp_symbol_set_fn_abs)
            except shutil.SameFileError:
                pass

            Utils.modify_fields_in_place({"MT4_ID": mt4_id_counter},  tmp_symbol_set_fn_abs)
            mt4_id_counter += 1

            self.work_inputs.append(tmp_symbol_ini_fn)
            # terminal.exe expects a relative path
            tmp_test_report_htm = os.path.join(self.relative_reports_folder, symbol + ".htm")
            # we also need the absolute path for the htm->csv parser
            abs_test_report_htm = os.path.join(self.abs_reports_folder, symbol + ".htm")
            abs_tmp_report_gif = os.path.join(self.abs_reports_folder, symbol + ".gif")
            # We need to delete existing gif files if re-running the case because MT4 doesn't overwrite them.
            # While we are on it, we delete .htm files too, although MT4 overwrites them.
            for f in abs_tmp_report_gif, abs_test_report_htm, tmp_symbol_ini_fn:
                if os.path.exists(f):
                    try:
                        print("Removing existing file: ", f)
                        os.remove(f)
                    except IOError:
                        logging.error("Can't get a lock on {} to delete existing file, please close all applications "
                                      "using this file.".format(f))
                        sys.exit(69)

            self.htm_reports[symbol] = abs_test_report_htm
            with open(tmp_symbol_ini_fn, 'w') as ini_file:
                ini_file.write("; Automatically generated by hpFX -- do not edit\n")
                ini_file.write("; Broker Login Information \n")
                ini_file.write("Server={}\n".format(self.broker_server))
                ini_file.write("Login={}\n".format(self.broker_login))
                ini_file.write("Password={}\n".format(self.broker_password))
                ini_file.write("; System Configuration \n")
                ini_file.write("ExpertsEnable=true\n")
                ini_file.write("ExpertsDllImport=true\n")
                ini_file.write("ExpertsExpImport=true\n")
                ini_file.write("; Test Expert Information \n")
                ini_file.write("TestExpert={}\n".format(self.expert))
                # IMPORTANT: TestExpertParameters must be relative to the '<data_folder>\tester'
                ini_file.write("TestExpertParameters={}\n".format(tmp_symbol_set_fn))
                ini_file.write("TestSymbol={}\n".format(symbol))
                ini_file.write("TestPeriod={}\n".format(self.time_frame))
                ini_file.write("TestModel={}\n".format(self.test_model))
                ini_file.write("TestSpread={}\n".format(self.spread))
                ini_file.write("TestOptimization={}\n".format(self.optimization))
                ini_file.write("TestDateEnable=true\n")
                ini_file.write("TestFromDate={}\n".format(self.date_from))
                ini_file.write("TestToDate={}\n".format(self.date_to))
                # IMPORTANT: TestReport must be relative to the '<data_folder>' UNLIKE TestExpertParameters!!!
                ini_file.write("TestReport={}\n".format(tmp_test_report_htm))
                ini_file.write("TestReplaceReport=true\n")
                shut_down_terminal = 'true'
                if self.is_debug:
                    shut_down_terminal = 'false'
                ini_file.write("TestShutdownTerminal={}\n".format(shut_down_terminal))
                ini_file.write("TestVisualEnable=false\n")


class ExpertIni:
    def __init__(self, input_fn=None, output_fn=None):
        # Input ini file to read for loading in
        self.__input_fn = input_fn
        self.__output_fn = output_fn
        self.__ini_parameters = ['TestExpert', 'TestExpertParameters', 'TestSymbolsList', 'TestPeriod', 'TestModel',
                                 'TestSpread', 'TestOptimization', 'TestDateEnable', 'TestFromDate', 'TestToDate',
                                 'TestReport', 'TestReplaceReport', 'TestShutdownTerminal']
        self.ini_config = {}

    def load(self):
        try:
            with open(self.__input_fn, 'r') as input_file:
                for line in input_file:
                    for key in self.__ini_parameters:
                        if re.match(key, line):
                            self.ini_config[key] = line.split('=', 1)[1].rstrip('\n')
        except IOError:
            logging.error("Could not open file: %s", self.__input_fn)
            sys.exit(1)
