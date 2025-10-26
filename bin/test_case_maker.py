import logging
import argparse
import sys

sys.path.append("..")
from src import SetMaker
from src import GlobalConfig


def main():
    parser = argparse.ArgumentParser()
    # Usage: python parse_strategy_report.py -c launcher_config.yaml
    parser.add_argument("-c", "--config", type=str, help="Configuration file that defines which test cases to create"
                        " in YAML format.")
    args = parser.parse_args()
    test_case_config = args.config

    if test_case_config is None:
        logging.error("Missing configuration file (-c), terminating.")
        sys.exit(81)

    global_conf = GlobalConfig()
    global_conf.ingest_global_config()
    global_conf.ingest_test_maker_config(test_case_config)

    all_cases = SetMaker.make_indi_cases(global_conf)

    print(all_cases)

    SetMaker.create_experiment_files(global_conf, all_cases)


if __name__ == "__main__":
    main()




