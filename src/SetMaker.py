import sys
import os
from itertools import permutations, product
import logging
import tempfile
import shutil
from src.Utils import extract_fields, modify_fields_in_place

# TODO
# - Check if the input indicator definitions include multiple names


# OLD Expert Types
# OLD #: SHORT  : LONG
# OLD ___________________________________
# OLD -1: FILE  : EXTRACT FROM GIVEN FILE
# OLD 0: NONE   : NONE
# OLD 1: 2LC    : TWO LINES CROSS
# OLD 2: 1LVC   : ONE LEVEL CROSS
# OLD 3: 2LVC   : TWO LEVEL CROSS
# OLD 4: LCMA   : LINE CROSS WITH MA
# OLD 5: SLS    : SINGLE LINE SIGNAL
# OLD 6: HIST   : HISTOGRAM
# OLD 7: ARROWS : ARROWS


# 0: NONE,
# 1: BASELINECROSS, // < indi_parameters >; < indi_filename >; < buffer1 >
# 2: TWOLINESCROSS, // < indi_parameters >; < indi_filename >; < buffer1 >, < buffer2 >
# 3: ONELEVELCROSS, // < indi_parameters >; < indi_filename >; < buffer >; < level >
# 4: TWOLEVELCROSS, // < indi_parameters >; < indi_filename >; < (+ / -)buffer >; < high_level >, < low_level >
# 5: SLOPE, // < indi_parameters >; < indi_filename >; < buffer >
# 6: HISTOGRAM, // < indi_parameters >; < indi_filename >; < buffer1 >, < buffer2 >
# 7: LINEMACROSS, // < indi_parameters >; < indi_filename >; < buffer1 >; < MA_period >, < MA_type >
# 8: ARROWS // < indi_parameters >; < indi_filename >; < long_buffer >, < short_buffer >

# Don't forget to update the version in Configuration.py as well!
indi_class = {'NONE': 0, 'BASELINECROSS': 1, 'TWOLINESCROSS': 2, 'ONELEVELCROSS': 3, 'TWOLEVELCROSS': 4,
              'SLOPE': 5, 'HISTOGRAM': 6, 'LINEMACROSS': 7, 'ARROWS': 8, 'SINGLEBUFFER': 9}

usage_class = {'SIGNAL': 0, 'SIGNALEXIT': 1, 'CONFIRMATION': 2, 'TRADEORNOT': 3, 'STOPLOSS': 4, 'EXIT': 5,
               'DISABLED': 6}


def identify_indi_parameters(input_str, indi_type_line):
    """
    Function to prevent repetitive code. It's called by make_indi_cases()
    It splits the configuration input string, checks for its validity, then returns a dict of GIVEN_NAME and input_str
    The split is done for verification only, otherwise the EA is compatible with the input_str's (<>|<>|<>) format
    :param input_str        : Input string (<given name>|<indi type>|<indi definition>) from test_case_maker YAML file
    :return: Dictionary with given name for the case, input definition string and indi usage
    """
    split_params = input_str.split('|')
    if len(split_params) != 3:
        logging.error("Provided indicator input '{}' does not have three fields separated with '|'. Please check input"
                      " file".format(input_str))
        sys.exit(109)

    indi_given_name = str(split_params[0]).strip()
    indi_type_str = str(split_params[1]).strip()
    if indi_type_str not in indi_class.keys():
        logging.error("Indicator type '{}' in given configuration '{}' isn't one of the supported types. "
                      "Please check your configuration.".format(indi_type_str, input_str))
        sys.exit(110)

    return {"GIVEN_NAME": indi_given_name, indi_type_line: input_str}

def make_indi_cases(config):
    """
    :param config: The global configuration instance
    :return: A list of tuples and dictionaries that represent all covered combinations,to be used by create_experiment_files()
    """
    # This is strictly for the 'Entry_Permutations==True' case.
    # permutation_cases = []
    # This is strictly for a linear list of 'ENTRY' or 'CONF' or 'ENTRY+CONF' (no permutations).
    # signal_conf_cases = []
    # signal_cases = []
    # Switching to a unified representation:
    trade_representations = []

    print("DEBUG: config=", config)

    # All Confirmation indicator combinations
    if config.Entry_Permutations:
        config.SIGNAL = []
        if config.ENTRY_PERMS is None:
            logging.error(
                "'Entry_Permutations' option requires a list of 'ENTRY_PERMS' indicators (NOT 'ENTRY' or 'CONF'). Please "
                "follow the instructions provided in the test_case_maker configuration file ")
            sys.exit(101)

        e_permutations = permutations(config.ENTRY_PERMS, 2)

        for ep in e_permutations:
            print(ep)
            entry_fields = identify_indi_parameters(ep[0], 'SIGNAL')
            conf_fields = identify_indi_parameters(ep[1], 'SIGNAL')
            conf_fields['CONFIRMATION1'] = conf_fields['SIGNAL']
            conf_fields.pop('SIGNAL')
            entry_fields['SIGNAL_USAGE'] = usage_class['SIGNAL']
            conf_fields['CONFIRMATION1_USAGE'] = usage_class['CONFIRMATION']
            trade_representations.append((entry_fields, conf_fields))

    else:
        # Check for incompatibilities between inputs and selected TestMode
        signal_cases = []
        conf1_cases = []
        conf2_cases = []
        tradeornot_cases = []
        exit_cases = []
        if config.SIGNAL is not None:
            for s in config.SIGNAL:
                entry_fields = identify_indi_parameters(s, 'SIGNAL')
                entry_fields['SIGNAL_USAGE'] = usage_class['SIGNAL']
                signal_cases.append(entry_fields)
        if config.CONF1 is not None:
            for c1 in config.CONF1:
                entry_fields = identify_indi_parameters(c1, 'CONFIRMATION1')
                entry_fields['CONFIRMATION1_USAGE'] = usage_class['CONFIRMATION']
                conf1_cases.append(entry_fields)
        if config.CONF2 is not None:
            for c2 in config.CONFIRMATION2:
                entry_fields = identify_indi_parameters(c2, 'CONFIRMATION2')
                entry_fields['CONFIRMATION2_USAGE'] = usage_class['CONFIRMATION']
                conf2_cases.append(entry_fields)
        if config.VOL is not None:
            for ton in config.VOL:
                entry_fields = identify_indi_parameters(ton, 'TRADEORNOT')
                entry_fields['TRADEORNOT_USAGE'] = usage_class['TRADEORNOT']
                tradeornot_cases.append(entry_fields)
        if config.EXIT is not None:
            for e in config.EXIT:
                entry_fields = identify_indi_parameters(e, 'EXIT')
                entry_fields['EXIT_USAGE'] = usage_class['EXIT']
                exit_cases.append(entry_fields)

        #DEBUG print("\nDEBUG=====================================================================================\n")
        #DEBUG for c in signal_cases:
        #DEBUG     print(c)
        #DEBUG print("\nAFTER LIST =====================================================================================\n")
        #DEBUG print(list(signal_cases)[0])
        #DEBUG print("\nAFTER APPEND =====================================================================================\n")
        #DEBUG trade_representations.append(list(signal_cases)[0])
        #DEBUG print(trade_representations)

        signal_cases_len = len(signal_cases)
        conf1_cases_len = len(conf1_cases)
        conf2_cases_len = len(conf2_cases)
        ton_cases_len = len(tradeornot_cases)
        exit_cases_len = len(exit_cases)

        for c in range(signal_cases_len):
            trade_representations.append([signal_cases[c]])

            if conf1_cases_len != 0 and conf1_cases_len == signal_cases_len:
                trade_representations[c].append(conf1_cases[c])
            if conf2_cases_len != 0 and conf2_cases_len == signal_cases_len:
                trade_representations[c].append(conf2_cases[c])
            if ton_cases_len != 0 and ton_cases_len == signal_cases_len:
                trade_representations[c].append(tradeornot_cases[c])
            if exit_cases_len != 0 and exit_cases_len == signal_cases_len:
                trade_representations[c].append(exit_cases[c])

        # trade_representations = tuple(zip(signal_cases, conf1_cases, conf2_cases, tradeornot_cases, exit_cases))
        for t in trade_representations:
            print(t)


        # trade_representations.append(zip(signal_cases, conf1_cases))
    # ---------------------------
    # BACKUP        # Check for incompatibilities between inputs and selected TestMode
    # BACKUP        if (config.SIGNAL is not None) and (config.CONFIRMATION1 is not None):
    # BACKUP            # Linear SIGNAL+CONFIRMATION1 case
    # BACKUP            if not isinstance(config.SIGNAL, list):
    # BACKUP                config.SIGNAL = list(config.SIGNAL)
    # BACKUP            if not isinstance(config.CONFIRMATION1, list):
    # BACKUP                config.CONFIRMATION1 = list(config.CONFIRMATION1)
    # BACKUP
    # BACKUP            if len(config.SIGNAL) != len(config.CONFIRMATION1):
    # BACKUP                logging.error("For SIGNAL+CONFIRMATION1 cases, the number of SIGNAL (={}) and CONFIRMATION1 (={}) lists must "
    # BACKUP                              "match.".format(len(config.SIGNAL), len(config.CONFIRMATION1)))
    # BACKUP                sys.exit(113)
    # BACKUP            signal_conf_cases = []
    # BACKUP            for e1, e2 in zip(config.SIGNAL, config.CONFIRMATION1):
    # BACKUP                entry_fields = identify_indi_parameters(e1, 'SIGNAL')
    # BACKUP                conf_fields = identify_indi_parameters(e2, 'SIGNAL')
    # BACKUP                # Correction for old C1s becoming the new C2s
    # BACKUP                conf_fields['CONFIRMATION1'] = conf_fields['SIGNAL']
    # BACKUP                conf_fields.pop('SIGNAL')
    # BACKUP                entry_fields['SIGNAL_USAGE'] = usage_class['SIGNAL']
    # BACKUP                conf_fields['CONFIRMATION1_USAGE'] = usage_class['CONFIRMATION']
    # BACKUP                signal_conf_cases.append((entry_fields, conf_fields))
    # BACKUP        elif (config.SIGNAL is not None) and (config.CONFIRMATION1 is None):
    # BACKUP            # SIGNAL-Only case
    # BACKUP            if not isinstance(config.SIGNAL, list):
    # BACKUP                config.SIGNAL = list(config.SIGNAL)
    # BACKUP            signal_cases = []
    # BACKUP            for e in config.SIGNAL:
    # BACKUP                entry_fields = identify_indi_parameters(e, 'SIGNAL')
    # BACKUP                entry_fields['SIGNAL_USAGE'] = usage_class['SIGNAL']
    # BACKUP                signal_cases.append(entry_fields)
    # BACKUP        else:
    # BACKUP            logging.error("No valid indicator combinations found. You must specify at least one SIGNAL indicator. "
    # BACKUP                          "Please check your input file and try again.")
    # BACKUP            sys.exit(115)
    # BACKUP
    # BACKUP    # Volume indicator(s)
    # BACKUP    v_cases = []
    # BACKUP    if config.TRADEORNOT is not None:
    # BACKUP        if not isinstance(config.TRADEORNOT, list):
    # BACKUP            config.TRADEORNOT = list(config.TRADEORNOT)
    # BACKUP        v_cases = []
    # BACKUP        for vol in config.TRADEORNOT:
    # BACKUP            v_fields = identify_indi_parameters(vol, 'TRADEORNOT')
    # BACKUP            # DEBUG print("===  TRADEORNOT TUPLE=", v_fields)
    # BACKUP            v_fields['TRADEORNOT_USAGE'] = usage_class['TRADEORNOT']
    # BACKUP            v_cases.append(v_fields)
    # BACKUP
    # BACKUP    # Exit indicator(s)
    # BACKUP    exit_cases = []
    # BACKUP    if config.EXIT is not None:
    # BACKUP        if not isinstance(config.EXIT, list):
    # BACKUP            config.EXIT = list(config.EXIT)
    # BACKUP        exit_cases = []
    # BACKUP        for e in config.EXIT:
    # BACKUP            e_fields = identify_indi_parameters(e, 'EXIT')
    # BACKUP            # DEBUG print("===  EXIT TUPLE=", e_fields)
    # BACKUP            e_fields['EXIT_USAGE'] = usage_class['EXIT']
    # BACKUP            exit_cases.append(e_fields)
    # ------------------------

    # STUPID CHECK if len(permutation_cases) == 0 and len(signal_cases) == 0:
    # STUPID CHECK     logging.error("ERROR: No Signal or Permutation cases detected, check the configuration file")
    # STUPID CHECK     sys.exit(118)

    # There can be only one 'ENTRY_PERMS', 'ENTRY+CONF' OR 'ENTRY'
    # RETIRED found = 0
    # RETIRED if len(permutation_cases) > 0:
    # RETIRED     found += 1
    # RETIRED if len(signal_conf_cases) > 0:
    # RETIRED     found += 1
    # RETIRED if len(signal_cases):
    # RETIRED     found += 1
    # RETIRED if found > 1:
    # RETIRED     logging.error("There can be only one case for 'ENTRY_PERMS', 'SIGNAL+CONFIRMATION1' OR 'SIGNAL', but found more. This looks like "
    # RETIRED                   "a bug in this software, please contact the developer.")
    # RETIRED     sys.exit(120)
    # RETIRED
    all_cases = []
    all_cases.append(trade_representations)
    # if permutation_cases:
    #    all_cases.append(list(permutation_cases))
    # if signal_conf_cases:
    #    all_cases.append(list(signal_conf_cases))
    # if signal_cases:
    #    all_cases.append(list(signal_cases))
    ##if v_cases:
    ##    all_cases.append(list(v_cases))
    # if exit_cases:
    #    all_cases.append(list(exit_cases))

    all_combos = list(product(*all_cases))

    formatted_all_combos = []
    for combo in all_combos:
        combo_list = []
        for c in combo:
            if not isinstance(c, list):
                combo_list.append(c)
            else:
                combo_list += c
        formatted_all_combos.append(combo_list)

    return formatted_all_combos


def create_experiment_files(config, all_indi_combos):
    """
    :param config: Global configuration instance
    :param all_indi_combos: A list of tuples and dictionaries that represent all covered combinations, as returned
                            by  make_indi_cases()
    :return: Nothing - it generates yaml and set files.
    """

    if not os.path.exists(config.abs_test_case_expert_template):
        logging.error("Template file '{}' cannot be found. Please check 'ExpertTemplate' and corresponding file: "
                      "'{}'".format(config.test_case_expert_template, config.abs_test_case_expert_template))
        sys.exit(131)

    # We need this later when creating the *.bat file.
    if not os.path.exists('./hpFX.py'):
        logging.error("Cannot find 'hpFX.py' under this directory.")
        sys.exit(132)
    hpFX_exe = os.path.abspath('./hpFX.py')

    # Create the *.bat file to be used to launch all of the test cases created here.
    try:
        bat_file = open(config.bat_file, 'w')
    except IOError:
        logging.error("Error in creating the batch file {} in modify_fields_in_place().".format(config.bat_file))
        sys.exit(144)

    print("\n=== ALL INDI COMBOS ===")
    for c in all_indi_combos:
        print(c)

    for indi in all_indi_combos:
        # We need to use a temporary file as we don't know the final filename (yet).
        tmp_set_file = tempfile.mktemp(prefix='hpFX_')
        shutil.copy(config.abs_test_case_expert_template, tmp_set_file)

        filename = ""
        for i in indi:
            # Needing this casting because Dict is also an iterable, messing up loops
            if isinstance(i, dict):
                list_i = [i]
            else:
                list_i = i
            for c in list_i:
                # DEBUG print("Modifying {} in {}".format(c, tmp_set_file))
                modify_fields_in_place(c, tmp_set_file)
                filename += "+" + str(c['GIVEN_NAME'])
                # DEBUG print("-> ", c)

        # We generate the combination test experts by concatenating the indicator for each category using
        # a '+' sign. The first one gets one too, so we need to strip it.
        set_fn = filename.lstrip('+') + ".set"
        yaml_fn = filename.lstrip('+') + ".yaml"

        abs_set_fn = os.path.join(config.abs_experts_path, set_fn)
        abs_yaml_fn = os.path.join(config.abs_experts_path, yaml_fn)

        print("Creating set file  : ", abs_set_fn)
        print("Creating yaml file : ", abs_yaml_fn)

        # Set the experiment type
        # RETIRED experiment_type = {"TEST_MODE": config.test_mode}
        # RETIRED modify_fields_in_place(experiment_type, tmp_set_file)

        shutil.move(tmp_set_file, abs_set_fn)

        # Next, we insert the *.set filename in the *.yaml file "TEST_CATEGORY": "TestCategory: "
        yaml_dict = {"EXPERT_FILE": os.path.join(config.experts_path, set_fn), "TEST_CATEGORY": config.testCategory}
        shutil.copy(config.hpFX_config_template, abs_yaml_fn)
        modify_fields_in_place(yaml_dict, abs_yaml_fn)

        # Finally, create a *.bat file to run all these experiments in batch
        command = "python \"{}\" -c \"{}\" -r\n".format(hpFX_exe, abs_yaml_fn)
        bat_file.write(command)
        print(command)

    print("\n>>> Processed {} cases in total.".format(len(all_indi_combos)))
    print("\n>>> You can run all cases using '{}'".format(config.bat_file))
    bat_file.close()
