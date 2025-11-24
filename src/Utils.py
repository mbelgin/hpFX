import csv
# provided by pyyaml
import yaml
import logging
import sys
import os
import tempfile
import hashlib
import shutil
import string
from itertools import combinations, permutations

"""
    A collection of utilities and tools that can be used by any other functions/classes independently.
"""

# Makes a hardwired assumption for the order of indicator types, ugly but serves the function
keyword_dict = {"SIGNAL": "indi_defs_1=", "SIGNAL_USAGE": "indi_usage_1=",
                "CONFIRMATION1": "indi_defs_2=", "CONFIRMATION1_USAGE": "indi_usage_2=",
                "CONFIRMATION2": "indi_defs_3=", "CONFIRMATION2_USAGE": "indi_usage_3=",
                "TRADEORNOT": "indi_defs_4=", "TRADEORNOT_USAGE": "indi_usage_4=",
                "EXIT": "indi_defs_5=", "EXIT_USAGE": "indi_usage_5=",
                "TP_ATR": "opt_1st_tp_atr_multiplier=",
                "SL_ATR": "opt_1st_sl_atr_multiplier=", "TEST_MODE": "TradingMode=",
                "EXPERT_FILE": "TestExpertParameters: ", "TEST_CATEGORY": "TestCategory: ",
                "FILE_TO_EXPORT": "FILE_TO_EXPORT=", "MT4_ID": "MT4_ID="}


def kill_all_terminals(conf):
    """m m
    Kills all of the active instances of MT4
    :param conf: global configuration
    :return:
    """
    workers = conf.terminals
    print("Terminating all open MT4 back testing instances (if any) to launch new tests.")
    for t in workers:
        print("Killing: ", t.exe)
        command = "WMIC Process Where \"ExecutablePath=\'{}\'\" Call Terminate  2>&1>NUL".format(t.exe)
        command = command.replace('\\', '\\\\')
        #print(command)
        os.system(command)

def read_set_file(fn):
    """
    Reads the given file into a list of lines
    :param fn: Input file
    :return: File content as a list of lines
    """
    with open(fn, 'r') as set_file:
        set_content = set_file.readlines()
    return set_content


def extract_fields(set_fn):
    """
    Extracts given fields from the input expert configuration (set) file.
    :param set_fn: Input expert configuration (set) file to extract values from.
    :return: a dictionary of extracted fields and values.
    """
    extracted_fields = {}

    if not os.path.exists(set_fn):
        logging.error("Can't find the file to extract parameters from: {}".format(set_fn))
        sys.exit(301)

    with open(set_fn, 'r') as set_file:
        for line in set_file:
            for keyword in keyword_dict.keys():
                if line.startswith(keyword_dict[keyword]):
                    extracted_fields[keyword] = line.split('=')[1].strip()

    return extracted_fields


def modify_fields_in_place(values, input_fn):
    """
    Finds given values in given file, and replaces them with their corresponding values in the
    keyword_dict{} dictionary.

    This function is specific to modifying *.set files and should not be used as a generic file search/replace tool.

    :param values: A dictionary of values to search and replace
    :param input_fn: input file to read values from
    :return:
    """

    file_desc, tmp_fn = tempfile.mkstemp(prefix='hpFX_')
    try:
        tmp_file = os.fdopen(file_desc, 'w')
    except IOError:
        logging.error("An error occurred creating a temp file in modify_fields_in_place(). Please send a bug report.")
        sys.exit(141)

    #DEBUG print("==== INPUT FN ===== : ", input_fn)
    with open(input_fn, 'r') as input_file:
        for line in input_file:
            modified_line = line
            for value in values.keys():
                if value == 'GIVEN_NAME':
                    continue
                if line.startswith(keyword_dict[value]):
                    modified_line = keyword_dict[value] + str(values[value]) + "\n"
            tmp_file.write(modified_line)

    input_file.close()
    tmp_file.close()
    shutil.move(tmp_fn, input_fn)


def dict_to_csv(input_dict, file_name, overwrite=False):
    # Returns False if an empty dictionary is provided

    if len(input_dict) == 0:
        # Nothing to do here
        return None

    mode = 'a+'
    if overwrite:
        mode = 'w'

    with open(file_name, mode, newline='') as output_file:
        is_file_blank = os.stat(file_name).st_size == 0
        csv_buffer = csv.DictWriter(output_file, input_dict[0].keys())
        if is_file_blank:
            csv_buffer.writeheader()
        csv_buffer.writerows(input_dict)

    return True


def csv_to_dict(input_file):
    with open(input_file, mode='r') as in_file:
        dict_csv = list(csv.DictReader(in_file))
        in_file.close()
        return dict_csv


def open_yaml(input_fn):
    try:
        with open(input_fn, 'r') as input_file:
            return yaml.load(input_file, Loader=yaml.FullLoader)
    except IOError:
        logging.error("Could not open file: %s", input_fn)
        sys.exit(10)


def c_combinations(c_list, num_elements):
    return list(combinations(c_list, num_elements))


def c_permutations(c_list, num_elements):
    return list(permutations(c_list, num_elements))


def data_folder_name(path_to_mt4_installation):
    """
    Returns the data_folder name for a given MT4 installation.
    :param path_to_mt4_installation: Absolute path for the MT4 installation.
    :return: Hashed 'unique' data folder name (not the entire path) for a given MT4 installation path.
    """
    return hashlib.md5(path_to_mt4_installation.encode('utf-16-le').upper()).hexdigest().upper()


def update_hpfx_csv_headers(src_set, dest_csv):
    """
    hpFX now supports dumping CSV reports (with version 15-62 and up) with 6 'select' headers,
    however it uses generic headers like "ON TESTER 1" rather than meaningful descriptions. This function
    updates these generic headers with human readable descriptions. It reads the header preferences from
    the input *.set file (src_set), finds the descriptions from the lookup table, and updates the CSV.
    This function must be called as a last step, after the CSV file is fully populated by all symbols in the test batch.

    :param src_set: Absolute path to the *.set file that includes user preferences for the 6 headers
    :param dest_csv: The generated and fully populated hpFX Report CSV filename (absolute path)
    :return: Nothing
    """

    # Lookup table for the CSV headers (tested with version hpFX version '16-18 BETA' only)
    hpfx_report_fields = {
        0: "NONE",
        1: "ANNUALIZED ROI",
        2: "ROI",
        3: "PROFIT",
        4: "PROFIT FACTOR",
        5: "EXPECTED PAYOFF",
        6: "WR SIMPLE",
        7: "WR ESTIMATED",
        8: "WR ALL",
        9: "WR TOTAL",
        10: "TP1 HITS",
        11: "SL1 HITS",
        12: "TP2 HITS",
        13: "SL2 HITS",
        14: "TS HITS",
        15: "BE HITS",
        16: "CHALK UPS",
        17: "GROSS PROFIT",
        18: "GROSS LOSS",
        19: "MAX DRAWDOWN",
        20: "RELATIVE DRAWDOWN",
        21: "ABSOLUTE DRAWDOWN",
        22: "CONSECUTIVE WINS",
        23: "CONSECUTIVE PROFITS",
        24: "CONSECUTIVE LOSSES",
        25: "CONSECUTIVE LOSS"}

    conversion_table = {"ON_TESTER_1=": "ON TESTER 1", "ON_TESTER_2=": "ON TESTER 2", "ON_TESTER_3=": "ON TESTER 3",
                        "ON_TESTER_4=": "ON TESTER 4", "ON_TESTER_5=": "ON TESTER 5", "ON_TESTER_6=": "ON TESTER 6"}
    fields_to_replace = {"ON TESTER 1": None, "ON TESTER 2": None, "ON TESTER 3": None, "ON TESTER 4": None,
                         "ON TESTER 5": None, "ON TESTER 6": None}

    #print("DEBUG: src_set={} dest_csv={}".format(src_set, dest_csv))

    # First, match the selections in the *.set file with human readable descriptions
    # I probably made this function more complicated than it needs to be... Oh, well.
    with open(src_set, 'r') as input_file:
        for line in input_file:
            for field in conversion_table.keys():
                if line.startswith(field):
                    #print("DEBUG: Processing field='{}' on line='{}'".format(field, line))
                    fields_to_replace[conversion_table[field]] = hpfx_report_fields[int(line.split('=')[1].strip('\n'))]

    # Then, find and replace in the CSV result file
    file_desc, tmp_fn = tempfile.mkstemp(prefix='hpFX_')

    try:
        tmp_file = os.fdopen(file_desc, 'w')
    except IOError:
        logging.error("An error occurred creating a temp file in update_hpfx_csv_headers(). "
                      "Please send a bug report.")
        sys.exit(142)

    with open(dest_csv, 'rt') as csv_file:
        csv_file_content = csv_file.read()
    csv_file.close()

    for key, value in fields_to_replace.items():
        csv_file_content = csv_file_content.replace(key, value)

    tmp_file.write(csv_file_content)
    tmp_file.close()

    shutil.move(tmp_fn, dest_csv)


def postprocess_results(conf):
    """
    Process HTM reports to generate RESULTS.csv and individual TRADES.csv files.
    Calculates Sharpe Ratios (Monthly and Annual) when enabled in configuration.

    Args:
        conf: GlobalConfig object containing test configuration and paths

    Writes:
        - RESULTS.csv: Summary metrics for all symbols (includes Sharpe ratios if enabled)
        - {SYMBOL}_TRADES.csv: Individual trade data per symbol in htm_reports folder
    """
    import os
    import logging
    from src import HTMParser

    # Display Sharpe Ratio configuration status
    if conf.calculate_sharpe:
        print("\n=== Sharpe Ratio Calculation Enabled ===")
        print("Risk-free rate: {:.2%}".format(conf.risk_free_rate))
        print("Test period: {} to {}".format(conf.date_from, conf.date_to))
        print("Calculating Monthly and Annual Sharpe Ratios...")
        print("==========================================\n")

    # Track symbols with Sharpe calculation warnings
    sharpe_warnings = []
    trades_processed = 0

    for s in conf.symbols:
        if s in conf.htm_reports.keys():
            html_report = conf.htm_reports[s]
            parsed_results = HTMParser(html_report)

            try:
                summary_output, trades_output = parsed_results.htm_to_csv(
                    calculate_sharpe=conf.calculate_sharpe,
                    risk_free_rate=conf.risk_free_rate,
                    date_from=conf.date_from,
                    date_to=conf.date_to
                )

                # Write summary to RESULTS.csv
                dict_to_csv(summary_output, conf.test_report_csv)

                # Write individual trades to {SYMBOL}_TRADES.csv in htm_reports folder
                if len(trades_output) > 0:
                    symbol_trades_csv = os.path.join(conf.abs_reports_folder, "{}_TRADES.csv".format(s))
                    dict_to_csv(trades_output, symbol_trades_csv, overwrite=True)
                    trades_processed += len(trades_output)
                    print("Processed {} - {} trades extracted".format(s, len(trades_output)))
                else:
                    print("Processed {} - No trades found".format(s))

                # Check if Sharpe calculation had issues
                if conf.calculate_sharpe and summary_output[0].get('Shrp(A-mo)') == 'N/A':
                    sharpe_warnings.append(s)

            except Exception as e:
                logging.error("Error processing HTM report for {}: {}".format(s, e))
                print("ERROR: Failed to process {}".format(s))
                continue

        else:
            logging.warning("Missing the HTM report for {}".format(s))
            print("WARNING: Missing HTM report for {}".format(s))

    # Display completion summary
    print("\nResults written to: {}".format(conf.test_report_csv))

    if trades_processed > 0:
        print("Trades written to:  {}/<SYMBOL>_TRADES.csv".format(conf.abs_reports_folder))
        print("Total trade rows:   {}".format(trades_processed))

    # Display Sharpe calculation warnings
    if conf.calculate_sharpe:
        print("\n--- Sharpe Ratio Calculation Summary ---")
        if len(sharpe_warnings) == 0:
            print("SUCCESS: All symbols calculated successfully")
        else:
            print("WARNING: {} symbol(s) could not calculate Sharpe:".format(len(sharpe_warnings)))
            for symbol in sharpe_warnings:
                print("  - {}".format(symbol))
            print("\nPossible reasons:")
            print("  * Test period < 1 year (Annual Sharpe)")
            print("  * Insufficient closed trades (< 2 periods)")
            print("  * All returns identical (zero std deviation)")
            print("\nCheck logs for detailed error messages.")